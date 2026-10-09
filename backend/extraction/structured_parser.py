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

import spacy
from spacy.matcher import Matcher

from app.config import get_settings
from extraction.loinc_validator import match_test_name

settings = get_settings()


@lru_cache
def _get_nlp():
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
_HEADER_PATTERNS: dict[str, list[str]] = {
    "patient_name": [r"(?:patient\s*name|name\s*of\s*patient|patient)\s*[:\-]\s*([A-Za-z .]{2,60})"],
    "patient_age": [r"age\s*[:\-]\s*(\d{1,3}\s*(?:y|yrs|years)?)"],
    "patient_sex": [r"(?:sex|gender)\s*[:\-]\s*(male|female|other|m|f)\b"],
    "hospital_name": [r"(?:hospital|lab(?:oratory)?|diagnostic\s*center|clinic)\s*[:\-]\s*([A-Za-z0-9 .,&'-]{3,80})"],
    "doctor_name": [r"(?:ref(?:erred)?\.?\s*(?:by|dr\.?)|doctor|consultant|physician)\s*[:\-]\s*(?:dr\.?\s*)?([A-Za-z .]{2,60})"],
    "sample_date": [r"(?:sample\s*date|collected\s*on|report\s*date|date)\s*[:\-]\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"],
}


def extract_patient_info(text: str) -> PatientInfo:
    info = PatientInfo()
    lowered = text
    for field_name, patterns in _HEADER_PATTERNS.items():
        for pattern in patterns:
            m = re.search(pattern, lowered, re.IGNORECASE)
            if m:
                value = m.group(1).strip().rstrip(",.")
                if value:
                    setattr(info, field_name, value)
                break
    return info


# ---------------------------------------------------------------------------
# Lab parameter line extraction (regex tuned for common report table layouts)
# ---------------------------------------------------------------------------
# Matches lines like:
#   "Hemoglobin        13.5   g/dL   13.0 - 17.0"
#   "SGPT (ALT)  45 U/L  Normal: 7-56"
#   "Creatinine: 1.1 mg/dL (0.6-1.3)"
_PARAM_LINE = re.compile(
    r"""^(?P<name>[A-Za-z][A-Za-z0-9 /()%.\-]{1,60}?)          # test name
        [\s:]{1,4}
        (?P<value>-?\d+\.?\d*)                                 # numeric value
        \s*
        (?P<unit>%|g/dL|mg/dL|U/L|IU/L|mmol/L|mEq/L|ng/mL|pg/mL|mIU/L|uIU/mL|/cumm|million/cumm|fL|cells/cumm|mm/hr)?
        [\s,]*
        (?:\(?\s*(?:normal|ref(?:erence)?|range)?\s*[:\-]?\s*
           (?P<range>\d+\.?\d*\s*-\s*\d+\.?\d*)\s*\)?)?
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _status_from_range(value: str | None, ref_range: str | None) -> str:
    if not value or not ref_range:
        return "Unknown"
    try:
        v = float(value)
        low_s, high_s = [x.strip() for x in ref_range.split("-")]
        low, high = float(low_s), float(high_s)
        if v < low:
            return "Abnormal (Low)"
        if v > high:
            return "Abnormal (High)"
        return "Normal"
    except (ValueError, IndexError):
        return "Unknown"


def extract_lab_parameters(text: str) -> list[ExtractedParameter]:
    results: list[ExtractedParameter] = []
    seen_names: set[str] = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if len(line) < 4:
            continue
        m = _PARAM_LINE.match(line)
        if not m:
            continue

        name = m.group("name").strip(" :-")
        # skip obvious non-test lines (header labels caught by the pattern)
        if name.lower() in {"age", "date", "sex", "gender", "id", "name"}:
            continue

        value = m.group("value")
        unit = m.group("unit")
        ref_range = m.group("range")
        status = _status_from_range(value, ref_range)

        loinc = match_test_name(name)

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


def guess_report_type(text: str, parameters: list[ExtractedParameter]) -> str:
    """Lightweight rule-based report-type classification from detected LOINC categories
    and keyword hits. Falls back to 'General / Unclassified' rather than guessing."""
    categories = [p.test_name_normalized for p in parameters if p.loinc_verified]
    text_lower = text.lower()

    keyword_map = {
        "MRI Report": ["mri", "magnetic resonance"],
        "CT Report": ["ct scan", "computed tomography"],
        "ECG Report": ["ecg", "electrocardiogram"],
        "X-Ray Report": ["x-ray", "radiograph"],
        "Discharge Summary": ["discharge summary", "discharged on"],
        "Prescription": ["rx", "prescription", "take 1 tablet"],
        "Urine Report": ["urine", "urinalysis"],
    }
    for label, keywords in keyword_map.items():
        if any(k in text_lower for k in keywords):
            return label

    if any(c and "hemoglobin" in c.lower() for c in categories):
        return "CBC (Complete Blood Count)"
    if any(c and c.lower() in {"alt", "ast", "total bilirubin", "albumin"} for c in categories):
        return "LFT (Liver Function Test)"
    if any(c and c.lower() in {"creatinine", "blood urea nitrogen", "egfr"} for c in categories):
        return "KFT (Kidney Function Test)"
    if any(c and "cholesterol" in (c or "").lower() for c in categories):
        return "Lipid Profile"
    if any(c and "tsh" in (c or "").lower() for c in categories):
        return "Thyroid Profile"
    if any(c and ("glucose" in (c or "").lower() or "hba1c" in (c or "").lower()) for c in categories):
        return "Diabetes / Blood Sugar Report"

    return "General / Unclassified"
