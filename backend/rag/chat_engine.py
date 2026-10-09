"""
Report-grounded chat engine.

Hard rule enforced here: the LLM is only ever given the retrieved report
chunks as context and is explicitly instructed to refuse to answer if the
information isn't present. We also apply a lightweight relevance-score
gate: if the top retrieved chunk's similarity score is too low, we skip
the LLM call entirely and return the fixed "couldn't find" response —
this avoids the model being tempted to answer from general knowledge
when nothing relevant was actually retrieved.

Broad questions ("what is the overall report", "summarize this") are
handled differently from targeted ones ("why is my hemoglobin low"). Top-k
chunk similarity search is built for finding the ONE best-matching passage
for a specific question — it structurally cannot answer a question about
the whole document well, since no single chunk is "about everything," so
even a genuinely answerable broad question would score low and incorrectly
trigger "couldn't find." Broad questions are detected by keyword pattern
and routed to pull from most/all of the report's chunks instead, bypassing
the single-best-match relevance gate (which doesn't make sense to apply
when the question is inherently about the whole document, not one part of it).

Language: when the user selects Telugu, the assistant answers directly in
natural, everyday spoken Telugu (not literary/formal Telugu), rather than
generating English and translating afterward — this keeps medical nuance
intact and reads far more naturally.

Failure handling: if EVERY configured LLM provider fails, we do NOT show
the user a raw error as if it were an answer. Since we can't safely
paraphrase or interpret without an LLM, the honest fallback is to show the
raw retrieved excerpt(s) from the report directly, clearly labeled as an
unprocessed excerpt rather than an AI answer (source="template_fallback").
"""
import logging
import re
from dataclasses import dataclass

from app.llm_client import generate, LLMUnavailableError
from rag.vector_store import retrieve

logger = logging.getLogger(__name__)

NOT_FOUND_MESSAGE_EN = "I couldn't find that information in this report."
NOT_FOUND_MESSAGE_TE = "ఈ రిపోర్ట్‌లో ఆ సమాచారం నాకు కనిపించలేదు."

AI_SOURCE = "ai_generated"
TEMPLATE_FALLBACK_SOURCE = "template_fallback"

# Lowered from 0.28 — with short, table-like lab-data chunks (e.g. "Hemoglobin 13.5
# g/dL 13.0-17.0") compared against natural-language questions ("why is my hemoglobin
# low"), cosine similarity from all-MiniLM-L6-v2 often lands lower than typical
# sentence-to-sentence similarity. A too-strict threshold here causes chat to answer
# "couldn't find" for genuinely relevant content — worse for trust than occasionally
# passing a borderline match through to the LLM, which independently double-checks
# relevance via its own "respond with not-found if excerpts don't answer" instruction.
MIN_RELEVANCE_SCORE = 0.18

# Questions matching these patterns are about the WHOLE report, not one specific
# fact — top-k chunk similarity search structurally can't answer these well (see
# module docstring), so they're detected and routed differently below.
_BROAD_QUESTION_PATTERNS = [
    r"\boverall\b", r"\bsummar", r"whole report", r"entire report",
    r"about this report", r"about the report", r"what.{0,15}report (say|show|indicate|mean)",
    r"what is this report", r"what does this report", r"explain (the|this) report",
    r"tell me about (the|this) report", r"walk me through", r"in general",
    r"మొత్తం", r"సారాంశం", r"గురించి చెప్ప", r"రిపోర్ట్ ఏంటి", r"రిపోర్ట్ లో ఏముంది",
]
_BROAD_QUESTION_RE = re.compile("|".join(_BROAD_QUESTION_PATTERNS), re.IGNORECASE)

# Cap on how many chunks to pass as context for a broad question — enough to
# cover a typical report in full without blowing up the prompt for very long ones.
BROAD_QUESTION_MAX_CHUNKS = 24

_MODE_STYLE = {
    "patient": "Use simple, warm, non-technical language a worried patient or family member can understand.",
    "student": "Use an educational tone: explain relevant physiology, clinical significance, and disease relevance.",
    "doctor": "Use precise clinical/professional terminology, concise and to the point, as if writing for a physician.",
}

_LANGUAGE_INSTRUCTION = {
    "en": "Answer in clear, natural English.",
    "te": (
        "Answer entirely in natural, EVERYDAY SPOKEN Telugu — exactly how a Telugu-speaking doctor "
        "or friend would casually explain this out loud, NOT how it would be written in a textbook "
        "or government document. Avoid heavy Sanskritized ('bookish') vocabulary and formal written "
        "verb endings — use the simple, common words an ordinary person uses in daily conversation. "
        "Keep medical test names (e.g. Hemoglobin, Creatinine, HbA1c) in English/Roman script, as "
        "they are commonly said in practice."
    ),
}

_SYSTEM_TEMPLATE = """You are a medical report assistant. You must answer the user's question
using ONLY the report excerpts provided below. Do not use outside medical knowledge to fill in
missing facts, and do not guess values, names, or dates that are not present in the excerpts.

If the excerpts do not contain information that answers the question, respond EXACTLY with:
"{not_found}"

Style instruction: {style}
Language instruction: {language_instruction}

Report excerpts:
---
{context}
---
"""

_EXCERPT_FALLBACK_PREFIX = {
    "en": "AI is temporarily unavailable, so here is the most relevant excerpt from your report instead:\n\n",
    "te": "AI తాత్కాలికంగా అందుబాటులో లేదు, కాబట్టి బదులుగా మీ రిపోర్ట్ నుండి అత్యంత సంబంధిత భాగం ఇక్కడ ఉంది:\n\n",
}


@dataclass
class ChatResult:
    answer: str
    grounded: bool
    retrieved_chunk_count: int
    source: str = AI_SOURCE


def _is_broad_question(question: str) -> bool:
    return bool(_BROAD_QUESTION_RE.search(question))


def answer_question(report_id: str, question: str, mode: str = "patient", language: str = "en") -> ChatResult:
    not_found = NOT_FOUND_MESSAGE_TE if language == "te" else NOT_FOUND_MESSAGE_EN
    broad = _is_broad_question(question)

    # Broad questions pull from most/all of the report instead of searching for
    # one best-matching chunk, and skip the single-best-match relevance gate —
    # see module docstring for why the normal narrow-match logic doesn't apply here.
    retrieved = retrieve(report_id, question, top_k=BROAD_QUESTION_MAX_CHUNKS if broad else None)

    if not retrieved:
        logger.warning("Chat retrieval returned ZERO chunks for report %s — the vector "
                       "index likely failed to build for this report (check upload logs).", report_id)
        return ChatResult(answer=not_found, grounded=False, retrieved_chunk_count=0, source=AI_SOURCE)

    if not broad:
        top_score = retrieved[0].score
        if top_score < MIN_RELEVANCE_SCORE:
            logger.info("Chat top similarity score %.3f is below threshold %.3f for report %s, "
                        "question: %r", top_score, MIN_RELEVANCE_SCORE, report_id, question)
            return ChatResult(answer=not_found, grounded=False, retrieved_chunk_count=len(retrieved), source=AI_SOURCE)
    else:
        logger.info("Broad question detected for report %s, using %d chunks as context, "
                    "question: %r", report_id, len(retrieved), question)

    context = "\n\n".join(f"[Excerpt {c.chunk_id}] {c.text}" for c in retrieved)
    system_prompt = _SYSTEM_TEMPLATE.format(
        not_found=not_found,
        style=_MODE_STYLE.get(mode, _MODE_STYLE["patient"]),
        language_instruction=_LANGUAGE_INSTRUCTION.get(language, _LANGUAGE_INSTRUCTION["en"]),
        context=context,
    )

    try:
        answer = generate(system_prompt, question, language=language)
        if answer:
            grounded = not_found.lower() not in answer.lower()
            return ChatResult(answer=answer, grounded=grounded, retrieved_chunk_count=len(retrieved), source=AI_SOURCE)
    except LLMUnavailableError:
        pass

    # Every provider failed (or returned empty) — fall back to showing the raw
    # top excerpt directly rather than an error message pretending to be an answer.
    prefix = _EXCERPT_FALLBACK_PREFIX.get(language, _EXCERPT_FALLBACK_PREFIX["en"])
    excerpt_answer = prefix + retrieved[0].text
    return ChatResult(answer=excerpt_answer, grounded=True, retrieved_chunk_count=len(retrieved), source=TEMPLATE_FALLBACK_SOURCE)
