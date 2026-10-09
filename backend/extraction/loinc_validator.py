"""
Local LOINC subset validator.

Purpose: every lab test name extracted from a report is checked against a
local LOINC subset (data/loinc_subset.csv) before it is shown to the user
as a "known" test. This is a deliberate anti-hallucination control — if we
can't match a test name to a known LOINC entry, we still show the raw
extracted text but flag `loinc_verified=False` and DO NOT let the LLM
invent a normalized name or clinical meaning for it beyond generic
"Unknown / uncommon parameter" guidance.

The local CSV ships with a starter subset covering the report types named
in the product brief. Extend data/loinc_subset.csv with more rows (or the
full public LOINC release) as needed — no code changes required.
"""
import csv
import difflib
from dataclasses import dataclass
from functools import lru_cache

from app.config import get_settings

settings = get_settings()


@dataclass
class LoincEntry:
    code: str
    common_name: str
    synonyms: list[str]
    category: str


@dataclass
class LoincMatch:
    verified: bool
    normalized_name: str | None
    loinc_code: str | None
    category: str | None
    match_score: float


@lru_cache
def _load_loinc() -> list[LoincEntry]:
    entries: list[LoincEntry] = []
    with open(settings.LOINC_LOCAL_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            synonyms = [s.strip() for s in row["synonyms"].split(";") if s.strip()]
            entries.append(
                LoincEntry(
                    code=row["loinc_code"],
                    common_name=row["common_name"],
                    synonyms=synonyms,
                    category=row["category"],
                )
            )
    return entries


def _all_names(entry: LoincEntry) -> list[str]:
    return [entry.common_name] + entry.synonyms


def match_test_name(raw_name: str, min_ratio: float = 0.82) -> LoincMatch:
    """
    Fuzzy-match a raw extracted test name against the local LOINC subset.
    Uses exact/substring match first, then difflib similarity as a fallback.
    Never fabricates a match below the confidence threshold.
    """
    if not raw_name or not raw_name.strip():
        return LoincMatch(False, None, None, None, 0.0)

    cleaned = raw_name.strip().lower()
    entries = _load_loinc()

    # 1) exact / substring match (fast path, highest confidence)
    for entry in entries:
        for name in _all_names(entry):
            if cleaned == name.lower() or cleaned in name.lower() or name.lower() in cleaned:
                return LoincMatch(True, entry.common_name, entry.code, entry.category, 1.0)

    # 2) fuzzy match fallback
    best_score = 0.0
    best_entry: LoincEntry | None = None
    for entry in entries:
        for name in _all_names(entry):
            score = difflib.SequenceMatcher(None, cleaned, name.lower()).ratio()
            if score > best_score:
                best_score = score
                best_entry = entry

    if best_entry and best_score >= min_ratio:
        return LoincMatch(True, best_entry.common_name, best_entry.code, best_entry.category, best_score)

    # No confident match -> mark unverified rather than guessing
    return LoincMatch(False, None, None, None, best_score)
