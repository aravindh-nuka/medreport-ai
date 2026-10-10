"""
Structured extraction pipeline.

Combines regex (for well-formatted numeric lab lines, which dominate
digital reports) with spaCy rule-based matching (for header fields like
patient name / doctor / hospital, which vary more in phrasing).

Golden rule: if a field cannot be found with reasonable confidence, it is
returned as None ("Unknown" at the API layer) — never guessed or inferred.
"""
import re
from dataclasses import dataclass, field
from functools import lru_cache

from app.config import get_settings
from extraction.loinc_validator import match_test_name

settings = get_settings()


@lru_cache
def _get_nlp():
    # Imported lazily: spaCy is not needed to start the server, and importing it
    # eagerly costs ~100+ MB of RAM (matters on Render's 512 MB free tier).
    import spacy

    return spacy.load(settings.SPACY_MODEL)


@dataclass
class PatientInfo:
    patient_name: str | None = None
    patient_age: str | None = None
    patient_sex: str | None = None
    hospital_name: str | None = None
    doctor_name: str | None = None
    sample_date: str | None = None


@dataclass
class ExtractedParameter:
    test_name_raw: str
    value: str | None
    unit: str | None
    reference_range: str | None
    status: str = "Unknown"
    test_name_normalized: str | None = None
    loinc_code: str | None = None
    loinc_verified: bool = False
    category: str | None = None


# ---------------------------------------------------------------------------
# Header field extraction (regex, label-anchored — deliberately conservative)
# ---------------------------------------------------------------------------
# Every pattern is anchored to the START of a line (so "For Diabetic Patient:"
# can never be read as a patient label) and uses [ \t] instead of \s so a match
# can never run across a line break. Captures stop at the next label.
_NEXT_LABEL = (
    r"(?=\s+(?:Lab\s*Id|Client|Age|Sex|Gender|UHID|Reg|Registration|Ref|Sample|Collected|"
    r"Location|Passport|Status|Approved|Printed|Process|Phone|Mobile|Date)\b|\s{2,}|\s*$)"
)
_NAME_CHARS = r"[A-Za-z][A-Za-z .'\-]{1,58}?"
_HEADER_PATTERNS: dict[str, list[str]] = {
    "patient_name": [
        r"^[ \t]*(?:patient[ \t]*name|name[ \t]*of[ \t]*patient|name|patient)[ \t]*[:\-][ \t]*("
        + _NAME_CHARS + r")" + _NEXT_LABEL,
    ],
    "patient_age": [
        r"^[ \t]*age[ \t]*[:\-][ \t]*(\d{1,3}[ \t]*(?:y|yrs|years)?)\b",
        r"\bSex[ \t]*/[ \t]*Age[ \t]*[:\-][ \t]*[A-Za-z]+[ \t]*/[ \t]*(\d{1,3}[ \t]*(?:Y|yrs|years)?)\b",
    ],
    "patient_sex": [
        r"^[ \t]*(?:sex|gender)[ \t]*[:\-][ \t]*(male|female|other|m|f)\b",
        r"\bSex[ \t]*/[ \t]*Age[ \t]*[:\-][ \t]*(male|female|other)\b",
    ],
    "hospital_name": [
        r"^[ \t]*(?:hospital|diagnostic[ \t]*cent(?:er|re)|clinic|laboratory)[ \t]*(?:name)?[ \t]*[:\-][ \t]*"
        r"([A-Za-z0-9][A-Za-z0-9 .,&'\-]{2,78}?)" + _NEXT_LABEL,
    ],
    "doctor_name": [
        r"^[ \t]*(?:ref(?:erred)?\.?[ \t]*(?:by|dr\.?)|doctor|consultant|physician)[ \t]*[:\-][ \t]*"
        r"(?:dr\.?[ \t]*)?(" + _NAME_CHARS + r")" + _NEXT_LABEL,
    ],
    "sample_date": [
        r"(?:^[ \t]*(?:sample[ \t]*date|report[ \t]*date|date)|\bcollected[ \t]*on)[ \t]*[:\-][ \t]*"
        r"(\d{1,2}[/-](?:\d{1,2}|[A-Za-z]{3})[/-]\d{2,4})",
    ],
}

# Words that mean the "value" we captured is really the next label, not a person/place.
_BAD_HEADER_VALUES = {
    "sample type", "sample", "lab id", "client name", "location", "status", "collected at",
    "registration", "ref", "age", "sex", "unknown", "poor control",
}


def extract_patient_info(text: str) -> PatientInfo:
    info = PatientInfo()
    for field_name, patterns in _HEADER_PATTERNS.items():
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if not m:
                continue
            value = m.group(1).strip().rstrip(",.:-").strip()
            if not value or value.lower() in _BAD_HEADER_VALUES:
                continue
            setattr(info, field_name, value)
            break
    return info


# ---------------------------------------------------------------------------
# Lab parameter line extraction (regex tuned for common report table layouts)
# ---------------------------------------------------------------------------
# Matches lines like:
#   "Hemoglobin        13.5   g/dL   13.0 - 17.0"
#   "Fasting Blood Sugar H 141.0 mg/dL 74 - 106"      (lab flag before the value)
#   "WBC Count H10570 /cmm 4000 - 10000"              (flag glued to the value)
#   "Cholesterol 189.0 mg/dL Desirable : <200"
#   "CHOL/HDL Ratio 3.1 Up to 5.0"
_UNIT = (
    r"%|[A-Za-z0-9µμ^.]*/[A-Za-z0-9µμ^.]+|fL|fl|pg|mg|g|IU|U|sec|seconds|ratio|cells"
)
_RANGE = (
    r"(?:\d+\.?\d*\s*[-–]\s*\d+\.?\d*"            # 13.0 - 17.0
    r"|(?:up\s*to|upto|<=|>=|<|>|≤|≥)\s*\d+\.?\d*)"  # < 200, Up to 5.0
)
_PARAM_LINE = re.compile(
    rf"""^(?P<name>[A-Za-z][A-Za-z0-9 /()%.,\-]{{1,60}}?)
         (?:[\s:]+(?P<flag>HH|LL|H|L)(?=\s|\d))?     # optional lab flag
         [\s:]*
         (?P<value>\d+\.?\d*)
         (?:\s*(?P<unit>{_UNIT})(?=\s|$))?
         (?:[\s,]*\(?\s*(?P<rlabel>[A-Za-z][A-Za-z ]{{0,24}})?\s*:?\s*
            (?P<range>{_RANGE})\s*\)?)?
    """,
    re.IGNORECASE | re.VERBOSE,
)

# A range label like "Low: <40" or "Optimal: <100" tells us which band a value falls
# in, NOT the normal range — only these labels introduce a true reference range.
_NORMAL_LABELS = {"", "normal", "desirable", "optimal", "reference", "ref", "range", "normal range", "ref range"}

# Lines that are page furniture, patient header, or prose — never a test result.
_JUNK_NAME = re.compile(
    r"\b(registration|printed|page|sample|approved|collected|passport|lab id|client|process|location|"
    r"ref\.? ?id|status|reference|interval|authenticat|referred|scan|qr|phone|mobile|"
    r"note|explanation|interference|borderline|desirable|optimal|control|diabetic|insufficiency|"
    r"deficiency|stage|grade|risk|criteria|guideline|pre-diabetes|non-diabetes|diabetes:)\b",
    re.IGNORECASE,
)
# Whole-name matches that are labels or risk bands rather than tests.
_JUNK_EXACT = {
    "age", "date", "sex", "gender", "id", "name", "high", "low", "normal", "very high", "result",
    "test", "report", "adult", "child", "male", "female", "page", "time", "unit", "method",
    "pre-diabetes", "non-diabetes", "diabetes", "optimal", "borderline", "borderline high",
}
_CITATION = re.compile(r"\b(et al|\d{4};\d+|j med|n engl|am j|diabetes care|\bpmid\b)", re.IGNORECASE)
_METHOD_SUFFIX = re.compile(r"\s+(microscopic|calculated|derived|automated|manual)$", re.IGNORECASE)


def _to_float(x: str) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _status_from_range(value: str | None, ref_range: str | None) -> str:
    v = _to_float(value) if value else None
    if v is None or not ref_range:
        return "Unknown"
    r = ref_range.strip().lower().replace("–", "-")
    m = re.fullmatch(r"(\d+\.?\d*)\s*-\s*(\d+\.?\d*)", r)
    if m:
        low, high = float(m.group(1)), float(m.group(2))
        return "Abnormal (Low)" if v < low else "Abnormal (High)" if v > high else "Normal"
    m = re.fullmatch(r"(up\s*to|upto|<=|<|≤)\s*(\d+\.?\d*)", r)
    if m:
        lim = float(m.group(2))
        strict = m.group(1) == "<"
        return "Abnormal (High)" if (v >= lim if strict else v > lim) else "Normal"
    m = re.fullmatch(r"(>=|>|≥)\s*(\d+\.?\d*)", r)
    if m:
        lim = float(m.group(2))
        strict = m.group(1) == ">"
        return "Abnormal (Low)" if (v <= lim if strict else v < lim) else "Normal"
    return "Unknown"


def _flag_status(flag: str | None) -> str:
    if not flag:
        return "Unknown"
    return "Abnormal (High)" if flag.upper().startswith("H") else "Abnormal (Low)"


def _clean_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip(" :-,")
    prev = None
    while prev != name:           # strip stacked suffixes
        prev = name
        name = _METHOD_SUFFIX.sub("", name).strip(" :-,")
    return name


def _looks_like_test_name(name: str) -> bool:
    if not (2 <= len(name) <= 55) or len(name.split()) > 7:
        return False
    if name.lower() in _JUNK_EXACT or _JUNK_NAME.search(name) or _CITATION.search(name):
        return False
    return True


def extract_lab_parameters(text: str) -> list[ExtractedParameter]:
    results: list[ExtractedParameter] = []
    seen_names: set[str] = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if len(line) < 4 or line.startswith(("•", "*")) or line.endswith(("-", ",")):
            continue
        m = _PARAM_LINE.match(line)
        if not m:
            continue

        name = _clean_name(m.group("name"))
        value = m.group("value")
        unit = m.group("unit")
        ref_range = m.group("range")
        label = (m.group("rlabel") or "").strip().lower()
        flag = m.group("flag")

        # Prose / headers / citations / reference-table bands are never test rows.
        if not _looks_like_test_name(name):
            continue
        # A label such as "Low:" / "High:" marks a risk band, not the normal range.
        if ref_range and label not in _NORMAL_LABELS:
            ref_range = None
        # A real result row carries a unit or a reference range.
        if not unit and not ref_range:
            continue

        loinc = match_test_name(name)
        # Unrecognised names are kept only when the row is fully formed
        # (unit AND range); otherwise it is dropped rather than guessed.
        if not loinc.verified and not (unit and ref_range):
            continue

        status = _status_from_range(value, ref_range)
        if status == "Unknown":
            status = _flag_status(flag)

        key = name.lower()
        if key in seen_names:
            continue
        seen_names.add(key)

        results.append(
            ExtractedParameter(
                test_name_raw=name,
                value=value if value else "Unknown",
                unit=unit if unit else None,
                reference_range=ref_range if ref_range else None,
                status=status,
                test_name_normalized=loinc.normalized_name,
                loinc_code=loinc.loinc_code,
                loinc_verified=loinc.verified,
                category=loinc.category,
            )
        )

    return results


# Map LOINC categories to broad panels used for report-type labelling.
_PANEL_OF_CATEGORY = {
    "CBC": "CBC (Complete Blood Count)", "Hematology": "CBC (Complete Blood Count)",
    "LFT": "LFT (Liver Function Test)", "KFT": "KFT (Kidney Function Test)",
    "Lipid": "Lipid Profile", "Thyroid": "Thyroid Profile",
    "Diabetes": "Diabetes / Blood Sugar Report", "Urine": "Urine Report",
}


def guess_report_type(text: str, parameters: list[ExtractedParameter]) -> str:
    """Rule-based report-type label. Imaging/document types need an exact word hit;
    lab reports are labelled by the panels actually found in verified results.
    Reports spanning 3+ panels are 'Multi-panel Health Check-up' (never first-keyword wins)."""
    text_lower = text.lower()
    keyword_map = {
        "MRI Report": [r"\bmri\b", r"magnetic resonance"],
        "CT Report": [r"\bct scan\b", r"computed tomography"],
        "ECG Report": [r"\becg\b", r"electrocardiogram"],
        "X-Ray Report": [r"\bx-?ray\b", r"radiograph"],
        "Discharge Summary": [r"discharge summary"],
        "Prescription": [r"\bprescription\b", r"take 1 tablet"],
    }
    for label, pats in keyword_map.items():
        if any(re.search(p, text_lower) for p in pats):
            if not [p for p in parameters if p.loinc_verified] or label in ("Discharge Summary", "Prescription"):
                return label

    verified = [p for p in parameters if p.loinc_verified]
    counts: dict[str, int] = {}
    for p in verified:
        panel = _PANEL_OF_CATEGORY.get(p.category or "")
        if p.test_name_normalized and p.test_name_normalized.lower() in {"hba1c", "hemoglobin a1c"}:
            panel = "Diabetes / Blood Sugar Report"
        if p.category == "Chemistry" and p.test_name_normalized and "glucose" in p.test_name_normalized.lower():
            panel = "Diabetes / Blood Sugar Report"
        if panel:
            counts[panel] = counts.get(panel, 0) + 1
    # other verified categories (Chemistry, Iron, Vitamins...) still count as a panel each
    other = {p.category for p in verified if p.category and p.category not in _PANEL_OF_CATEGORY}
    panels = len(counts) + len(other)

    if panels >= 3:
        return "Multi-panel Health Check-up"
    if len(counts) >= 1 and panels == 1:
        return next(iter(counts))
    if panels == 2 and counts:
        return " + ".join(sorted(counts, key=counts.get, reverse=True)[:2]) if len(counts) == 2 else \
            max(counts, key=counts.get) + " (with other tests)"
    if "urine" in text_lower and not verified:
        return "Urine Report"
    return "General / Unclassified"
