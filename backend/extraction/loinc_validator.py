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
import re
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


def _norm(text: str) -> str:
    """lowercase, punctuation -> spaces, collapse whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


def _contains_words(haystack: str, needle: str) -> bool:
    """True if `needle` appears in `haystack` as whole words (not inside another word)."""
    return bool(needle) and re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", haystack) is not None


def match_test_name(raw_name: str, min_ratio: float = 0.90) -> LoincMatch:
    """
    Match a raw extracted test name against the local LOINC subset.

    Strict by design (a wrong 'verified' badge is worse than no badge):
      1) exact match after normalisation (also tries each side of "T3 - Triiodothyronine");
      2) a LOINC name found inside the text as WHOLE WORDS, only if it covers most of the
         text (>= 75%) and is not a tiny token like 'ph' inside another word;
      3) high-threshold fuzzy match (>= 0.90) for typos only.
    Anything else is returned unverified.
    """
    if not raw_name or not raw_name.strip():
        return LoincMatch(False, None, None, None, 0.0)

    full = _norm(raw_name)
    if not full:
        return LoincMatch(False, None, None, None, 0.0)
    parts = [full] + [_norm(p) for p in re.split(r"\s+-\s+|\s*/\s*(?=[A-Za-z]{4,})|[()]|,", raw_name) if _norm(p)]
    entries = _load_loinc()

    # 1) exact normalised match
    for entry in entries:
        names = {_norm(n) for n in _all_names(entry)}
        if any(part in names for part in parts):
            return LoincMatch(True, entry.common_name, entry.code, entry.category, 1.0)

    # 2) whole-word containment with coverage requirement (prefer the longest name)
    best: tuple[int, LoincEntry] | None = None
    for entry in entries:
        for n in _all_names(entry):
            nn = _norm(n)
            if len(nn) < 4 or not _contains_words(full, nn):
                continue
            if len(nn) / len(full) >= 0.75 and (best is None or len(nn) > best[0]):
                best = (len(nn), entry)
    if best:
        return LoincMatch(True, best[1].common_name, best[1].code, best[1].category, 0.95)

    # 3) strict fuzzy (typos only)
    best_score, best_entry = 0.0, None
    for entry in entries:
        for n in _all_names(entry):
            nn = _norm(n)
            if len(nn) < 5:
                continue
            score = difflib.SequenceMatcher(None, full, nn).ratio()
            if score > best_score:
                best_score, best_entry = score, entry
    if best_entry and best_score >= min_ratio:
        return LoincMatch(True, best_entry.common_name, best_entry.code, best_entry.category, best_score)

    return LoincMatch(False, None, None, None, best_score)
