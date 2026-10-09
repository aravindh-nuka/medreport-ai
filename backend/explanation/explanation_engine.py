"""
Adaptive Explanation Engine.

Generates AI explanations strictly grounded in extracted report data (never
invents test values). Every prompt includes only facts already extracted
and stored in the database.

Output format: plain, flowing prose with explicit length targets (NOT
bullet points, NOT JSON). Earlier versions asked the LLM to return strict
JSON, but many free models wrap it in extra text or produce slightly
invalid JSON — the parser would then fail and silently show a "basic
explanation" even though the AI call itself succeeded. A simple marker
format (###FIELD_NAME### followed by plain text) is far more forgiving to
parse correctly, which is what actually fixes that failure mode.

Language handling: when language="te", we do NOT translate English output
word-for-word after the fact. Instead we instruct the LLM to compose the
explanation directly in natural, EVERYDAY SPOKEN Telugu — explicitly
rejecting bookish/literary/government-document register, since that's
what reads as unnatural to most patients. Medical test names are kept in
English unless a Telugu term is in everyday clinical use. Telugu requests
are also routed to a different (Gemini-first) provider order — see
app/llm_client.py — since Google's models produce noticeably more natural
Telugu than the Llama-family models available on Groq/Cerebras.

Failure handling: if EVERY configured LLM provider fails (see
app/llm_client.py's provider chain), we do NOT show the user a raw error.
Instead we build a real explanation deterministically from the extracted
facts using fixed templates — no network call, so it always works. This
output is clearly marked with source="template_fallback" (vs "ai_generated")
so the UI can label it honestly rather than presenting it as an AI
explanation.

Flashcards are NOT LLM-generated at all (by design) — they're built
directly from extracted test names + a hand-authored category glossary.
This is more reliable than an LLM call for what is fundamentally a simple
lookup task, and means flashcards are always instant and always available.

Three audiences:
  patient  -> simple, reassuring, jargon-free
  student  -> educational: physiology + clinical relevance
  doctor   -> concise clinical terminology
"""
import logging
import re

from app.llm_client import generate, LLMUnavailableError

logger = logging.getLogger(__name__)

AI_SOURCE = "ai_generated"
TEMPLATE_FALLBACK_SOURCE = "template_fallback"

_MODE_STYLE = {
    "patient": "Explain simply for a patient/caregiver with no medical background. Avoid jargon. Be reassuring but honest.",
    "student": "Explain for a medical/nursing student: include relevant physiology, clinical significance, and disease relevance.",
    "doctor": "Explain for a clinician: concise, precise clinical terminology, no filler.",
}

_LANGUAGE_INSTRUCTION = {
    "en": "Write the entire response in clear, natural English.",
    "te": (
        "Write the ENTIRE response in natural, EVERYDAY SPOKEN Telugu — exactly the way a "
        "Telugu-speaking doctor or a well-informed friend would casually explain this out loud, "
        "like a WhatsApp voice message, NOT how it would be written in a textbook, newspaper, or "
        "government document. This is critical: avoid heavy Sanskritized ('bookish'/'pure') "
        "vocabulary and formal written-register verb endings. Use the simple, common, everyday "
        "words and sentence patterns an ordinary person uses in daily conversation. If you are "
        "choosing between a formal/literary word and a common spoken word for the same meaning, "
        "ALWAYS pick the common spoken word. Keep medical test names (e.g. Hemoglobin, Creatinine, "
        "HbA1c, SGPT, Cholesterol) in English/Roman script exactly as they are commonly said in "
        "practice — do not translate them into formal Telugu equivalents."
    ),
}

_NO_BULLETS_INSTRUCTION = (
    "Write in plain flowing prose sentences only. Do NOT use bullet points, dashes, numbered "
    "lists, or markdown formatting anywhere in your response."
)


# ---------------------------------------------------------------------------
# Robust marker-based parsing (replaces fragile JSON parsing)
# ---------------------------------------------------------------------------
def _parse_marked_sections(raw: str, keys: list[str]) -> dict | None:
    """
    Extracts fields from a response formatted as:
        ###KEY_NAME###
        content...
        ###NEXT_KEY###
        content...

    Tolerant of extra whitespace, minor preamble text, and a couple of
    missing sections (some free models drop one or two fields even when
    instructed not to). Returns None only if parsing yields too little to
    be usable, in which case the caller falls back to the deterministic
    template.
    """
    pattern = re.compile(r"#{2,3}\s*([A-Za-z_]+)\s*#{2,3}\s*(.*?)(?=#{2,3}\s*[A-Za-z_]+\s*#{2,3}|\Z)", re.DOTALL)
    matches = pattern.findall(raw)
    if not matches:
        return None

    found = {name.strip().lower(): content.strip() for name, content in matches}
    result = {k: found.get(k, "").strip() for k in keys}

    non_empty = sum(1 for v in result.values() if v)
    # require at least all-but-2 fields to be present; otherwise treat as a parse failure
    if non_empty < max(1, len(keys) - 2):
        return None
    return result


# ---------------------------------------------------------------------------
# Report Overview
# ---------------------------------------------------------------------------
_OVERVIEW_KEYS = [
    "short_summary", "detailed_explanation", "final_verdict",
    "suggestions", "precautions", "lifestyle_advice", "diet_recommendations",
    "exercise_suggestions", "followup_advice", "doctor_consultation_advice", "monitoring_advice",
]

_OVERVIEW_FORMAT_INSTRUCTIONS = f"""Format your response using EXACTLY these markers, each on its own line,
followed by that section's content. {_NO_BULLETS_INSTRUCTION} Do not write anything before the first
marker or after the last section.

CRITICAL: The marker tokens themselves (like ###SHORT_SUMMARY###) must be copied EXACTLY as shown below,
in English capital letters with ### on both sides — even if you are writing the content in Telugu or any
other language. NEVER translate, modify, or omit the markers themselves. Only the content that comes
AFTER each marker should be written in the requested language. For example, if writing in Telugu, your
output must look exactly like this pattern (marker in English, content in Telugu):
###SHORT_SUMMARY###
ఈ రిపోర్ట్ ప్రకారం... (Telugu content continues here)
###DETAILED_EXPLANATION###
మొత్తంగా ఈ రిపోర్ట్... (Telugu content continues here)

###SHORT_SUMMARY###
(3 to 4 sentences: a brief overview naming the report type and the specific results that matter most,
quoting actual values from the data. Flowing prose, no generic filler.)

###DETAILED_EXPLANATION###
(7 to 8 sentences as ONE continuous flowing narrative, written as if a doctor is sitting with the
patient and walking them through EVERYTHING in the report, in the patient's own everyday language —
not a high-level teaser, actual comprehensive coverage. Touch on every significant finding (grouping
related ones together where natural so it still fits in 7-8 sentences), explain what each one means
in plain terms, how they relate to each other, what's concerning versus reassuring, and what's
completely normal. This should feel like the patient walks away understanding their whole report,
not just a summary of it. Always name the real test names and values from the report and follow
the order: what the problem is, what it means for the person, what to do about it. Never write generic
statements that could apply to any report. Do not use bullet points — flowing spoken-style prose only.)

###FINAL_VERDICT###
(3 to 4 sentences written exactly like a doctor speaking directly to the patient at the end of a
consultation: state plainly what this report shows overall, then tell the patient what to do next —
whether that's "nothing needed, keep up routine checkups," "see a doctor about X specifically," or
"repeat this test in N weeks," strictly based on the data given. This is the moment where the patient
gets a clear bottom line and a clear next action, not just an abstract conclusion. If the report
doesn't support a definite conclusion, say so plainly rather than inventing one.)

###SUGGESTIONS###
(2-3 sentences, flowing prose.)

###PRECAUTIONS###
(2-3 sentences, flowing prose.)

###LIFESTYLE_ADVICE###
(2-3 sentences, flowing prose.)

###DIET_RECOMMENDATIONS###
(2-3 sentences, flowing prose.)

###EXERCISE_SUGGESTIONS###
(2-3 sentences, flowing prose.)

###FOLLOWUP_ADVICE###
(2-3 sentences, flowing prose.)

###DOCTOR_CONSULTATION_ADVICE###
(2-3 sentences on when and why to consult a doctor about this report.)

###MONITORING_ADVICE###
(2-3 sentences on what should be monitored going forward and how often, if applicable.)"""


# ---------------------------------------------------------------------------
# Deterministic no-LLM fallback strings (used only if every provider fails)
# ---------------------------------------------------------------------------
_OVERVIEW_STRINGS = {
    "en": {
        "short_summary": "This {report_type} report contains {total} test result(s): {abnormal_count} outside the normal range, {normal_count} within normal limits, and {unknown_count} that could not be fully verified. Please review the details below, and share this report with a doctor for a complete interpretation.",
        "detailed_line": "Overall, {total} parameter(s) were extracted from this report. {abnormal_text} {normal_text} {unknown_text} A doctor should review this report alongside your full medical history for a complete picture.",
        "abnormal_text": "{count} result(s) — {names} — fall outside the normal reference range and may need attention.",
        "normal_text": "{count} result(s) — {names} — are within normal limits.",
        "unknown_text": "{count} item(s) — {names} — could not be confidently matched to a standard test and are marked Unknown rather than guessed.",
        "verdict_abnormal": "This report shows {abnormal_count} result(s) outside the normal range. Because interpreting abnormal lab values requires clinical context, a doctor should review these specific findings alongside your symptoms and history. Please do not draw conclusions from this summary alone. Bring this full report to your next medical visit.",
        "verdict_normal": "All extracted results in this report fall within normal reference ranges. This is a reassuring sign for the parameters tested, though it does not rule out every possible health concern. Continue routine checkups as recommended by your doctor.",
        "verdict_unknown": "No definite overall conclusion can be made from this report, since most values could not be verified against a standard reference. Please share the original report with your doctor or lab for a proper interpretation.",
        "suggestions": "Share this full report with a qualified doctor, especially any results marked as outside the normal range.",
        "precautions": "Do not self-diagnose or start any treatment based solely on this summary. Values outside range can have many causes.",
        "lifestyle_advice": "Maintain a balanced diet, regular physical activity, adequate sleep, and avoid tobacco/excess alcohol pending medical advice.",
        "diet_recommendations": "General diet guidance depends on the specific abnormal values; a doctor or dietitian can advise once the full picture is reviewed.",
        "exercise_suggestions": "Moderate regular activity is generally beneficial, but confirm with a doctor if any results are abnormal.",
        "followup_advice": "Schedule a follow-up with your doctor to interpret these results in the context of your full medical history.",
        "doctor_consultation_advice": "Consult a doctor promptly if any result is marked abnormal or critical, or if you have symptoms.",
        "monitoring_advice": "Ask your doctor whether any of these tests should be repeated periodically to track trends over time.",
    },
    "te": {
        "short_summary": "ఈ {report_type} రిపోర్ట్‌లో {total} టెస్ట్ ఫలితాలు ఉన్నాయి: {abnormal_count} నార్మల్ రేంజ్ బయట, {normal_count} నార్మల్ రేంజ్‌లో, మరియు {unknown_count} పూర్తిగా వెరిఫై చేయలేకపోయాము. దయచేసి కింద ఉన్న వివరాలు చూడండి, పూర్తి వివరణ కోసం ఈ రిపోర్ట్‌ని డాక్టర్‌కి చూపించండి.",
        "detailed_line": "మొత్తంగా, ఈ రిపోర్ట్ నుండి {total} పారామీటర్‌లు తీయబడ్డాయి. {abnormal_text} {normal_text} {unknown_text} మీ పూర్తి వైద్య చరిత్రతో పాటు ఈ రిపోర్ట్‌ని డాక్టర్ సమీక్షించాలి.",
        "abnormal_text": "{count} ఫలితాలు — {names} — నార్మల్ రేంజ్ బయట ఉన్నాయి, వీటిపై శ్రద్ధ అవసరం కావచ్చు.",
        "normal_text": "{count} ఫలితాలు — {names} — నార్మల్ రేంజ్‌లోనే ఉన్నాయి.",
        "unknown_text": "{count} అంశాలు — {names} — స్టాండర్డ్ టెస్ట్‌తో పూర్తిగా సరిపోల్చలేకపోయాము, కాబట్టి ఊహించకుండా Unknown అని చూపిస్తున్నాం.",
        "verdict_abnormal": "ఈ రిపోర్ట్‌లో {abnormal_count} ఫలితాలు నార్మల్ రేంజ్ బయట ఉన్నాయి. అసాధారణ వాల్యూలను అర్థం చేసుకోవడానికి క్లినికల్ సందర్భం అవసరం కాబట్టి, మీ లక్షణాలు మరియు చరిత్రతో పాటు వీటిని డాక్టర్ సమీక్షించాలి. దయచేసి కేవలం ఈ సారాంశం ఆధారంగా నిర్ధారణలకు రావద్దు. మీ తదుపరి డాక్టర్ విజిట్‌కి ఈ పూర్తి రిపోర్ట్ తీసుకెళ్లండి.",
        "verdict_normal": "ఈ రిపోర్ట్‌లో తీసిన అన్ని ఫలితాలు నార్మల్ రిఫరెన్స్ రేంజ్‌లోనే ఉన్నాయి. టెస్ట్ చేసిన పారామీటర్‌లకు ఇది మంచి సంకేతం, అయితే ప్రతి ఆరోగ్య సమస్యను ఇది తోసిపుచ్చదు. మీ డాక్టర్ సిఫారసు చేసిన విధంగా రెగ్యులర్ చెకప్‌లు కొనసాగించండి.",
        "verdict_unknown": "చాలా వాల్యూలను స్టాండర్డ్ రిఫరెన్స్‌తో వెరిఫై చేయలేకపోయినందున, ఈ రిపోర్ట్ నుండి ఖచ్చితమైన నిర్ధారణకు రాలేకపోయాము. సరైన వివరణ కోసం దయచేసి ఒరిజినల్ రిపోర్ట్‌ని మీ డాక్టర్ లేదా ల్యాబ్‌కి చూపించండి.",
        "suggestions": "ఈ పూర్తి రిపోర్ట్‌ని అర్హత కలిగిన డాక్టర్‌కి చూపించండి, ముఖ్యంగా నార్మల్ రేంజ్ బయట ఉన్న ఫలితాలు.",
        "precautions": "కేవలం ఈ సారాంశం ఆధారంగా స్వీయ నిర్ధారణ చేయవద్దు లేదా చికిత్స మొదలుపెట్టవద్దు. రేంజ్ బయట వాల్యూలకు చాలా కారణాలు ఉండవచ్చు.",
        "lifestyle_advice": "సమతుల్య ఆహారం, క్రమం తప్పకుండా వ్యాయామం, తగినంత నిద్ర పాటించండి, మరియు డాక్టర్ సలహా వచ్చే వరకు పొగాకు/మద్యం మానుకోండి.",
        "diet_recommendations": "నిర్దిష్ట ఆహార సలహా అసాధారణ వాల్యూలపై ఆధారపడి ఉంటుంది; పూర్తి చిత్రం సమీక్షించిన తర్వాత డాక్టర్ లేదా డైటీషియన్ సలహా ఇవ్వగలరు.",
        "exercise_suggestions": "సాధారణంగా మితమైన క్రమమైన వ్యాయామం మంచిది, కానీ ఫలితాలు అసాధారణంగా ఉంటే డాక్టర్‌తో నిర్ధారించుకోండి.",
        "followup_advice": "మీ పూర్తి వైద్య చరిత్ర సందర్భంలో ఈ ఫలితాలను అర్థం చేసుకోవడానికి డాక్టర్‌తో ఫాలో-అప్ షెడ్యూల్ చేయండి.",
        "doctor_consultation_advice": "ఏదైనా ఫలితం అసాధారణంగా లేదా క్రిటికల్‌గా ఉంటే, లేదా మీకు లక్షణాలు ఉంటే వెంటనే డాక్టర్‌ని సంప్రదించండి.",
        "monitoring_advice": "ఈ టెస్ట్‌లలో ఏవైనా కాలానుగుణంగా పునరావృతం చేయాలా అని మీ డాక్టర్‌ని అడగండి.",
    },
}


def _template_report_overview(report_type: str, parameters: list[dict], language: str) -> dict:
    """Deterministic, no-LLM fallback built entirely from extracted facts. Flowing
    prose (no bullets), matching the same format as real AI output."""
    s = _OVERVIEW_STRINGS.get(language, _OVERVIEW_STRINGS["en"])

    abnormal = [p["test_name_raw"] for p in parameters if "Abnormal" in p.get("status", "") or p.get("status") == "Critical"]
    normal = [p["test_name_raw"] for p in parameters if p.get("status") == "Normal"]
    unknown = [p["test_name_raw"] for p in parameters if not p.get("loinc_verified") or p.get("status") == "Unknown"]

    abnormal_text = s["abnormal_text"].format(count=len(abnormal), names=", ".join(abnormal)) if abnormal else ""
    normal_text = s["normal_text"].format(count=len(normal), names=", ".join(normal)) if normal else ""
    unknown_text = s["unknown_text"].format(count=len(unknown), names=", ".join(unknown)) if unknown else ""

    if abnormal:
        verdict = s["verdict_abnormal"].format(abnormal_count=len(abnormal))
    elif parameters:
        verdict = s["verdict_normal"]
    else:
        verdict = s["verdict_unknown"]

    return {
        "short_summary": s["short_summary"].format(
            report_type=report_type, total=len(parameters),
            abnormal_count=len(abnormal), normal_count=len(normal), unknown_count=len(unknown),
        ),
        "detailed_explanation": s["detailed_line"].format(
            total=len(parameters), abnormal_text=abnormal_text, normal_text=normal_text, unknown_text=unknown_text,
        ),
        "final_verdict": verdict,
        "suggestions": s["suggestions"],
        "precautions": s["precautions"],
        "lifestyle_advice": s["lifestyle_advice"],
        "diet_recommendations": s["diet_recommendations"],
        "exercise_suggestions": s["exercise_suggestions"],
        "followup_advice": s["followup_advice"],
        "doctor_consultation_advice": s["doctor_consultation_advice"],
        "monitoring_advice": s["monitoring_advice"],
    }


def generate_report_overview(
    report_type: str,
    parameters: list[dict],
    mode: str = "patient",
    language: str = "en",
) -> tuple[dict, str]:
    """Returns (content_dict, source) where source is 'ai_generated' or 'template_fallback'."""
    params_text = "\n".join(
        f"- {p['test_name_raw']}: {p.get('value', 'Unknown')} {p.get('unit') or ''} "
        f"(range: {p.get('reference_range') or 'Unknown'}, status: {p.get('status', 'Unknown')}, "
        f"verified: {p.get('loinc_verified', False)})"
        for p in parameters
    ) or "No structured lab parameters were extracted from this report."

    user_prompt = f"""Report type: {report_type}

Extracted lab parameters (ground truth — do not invent additional values, do not contradict these):
{params_text}

{_OVERVIEW_FORMAT_INSTRUCTIONS}"""

    system_prompt = (
        f"You are a medical report interpretation assistant writing a 'Report Overview'. "
        f"{_MODE_STYLE.get(mode, _MODE_STYLE['patient'])} {_LANGUAGE_INSTRUCTION.get(language, _LANGUAGE_INSTRUCTION['en'])} "
        "Base every claim only on the extracted parameters given above — never invent a parameter, "
        "value, or diagnosis not listed. This is educational information, not a medical diagnosis; "
        "the final_verdict section may read like a clinical conclusion but must be strictly derived "
        "from the data provided, and doctor_consultation_advice should reinforce seeing a real doctor "
        "for anything abnormal or critical."
    )

    try:
        raw = generate(system_prompt, user_prompt, language=language)
        parsed = _parse_marked_sections(raw, _OVERVIEW_KEYS)
        if parsed:
            return parsed, AI_SOURCE
        logger.warning(
            "generate_report_overview: LLM call succeeded but marker parsing FAILED "
            "(language=%s, mode=%s). This means real AI content was discarded — falling "
            "back to template. Raw response (first 500 chars): %r",
            language, mode, raw[:500],
        )
    except LLMUnavailableError:
        pass

    return _template_report_overview(report_type, parameters, language), TEMPLATE_FALLBACK_SOURCE


# ---------------------------------------------------------------------------
# Individual parameter explanation
# ---------------------------------------------------------------------------
_PARAM_KEYS = [
    "what_it_measures", "why_it_matters", "high_value_reasons", "low_value_reasons",
    "lifestyle_suggestions", "when_to_consult_doctor", "clinical_significance", "educational_notes",
]

_PARAM_FORMAT_INSTRUCTIONS = f"""Format your response using EXACTLY these markers, each on its own line,
followed by that section's content (2-3 sentences of flowing prose each). {_NO_BULLETS_INSTRUCTION}
Do not write anything before the first marker or after the last section.

CRITICAL: The marker tokens themselves (like ###WHAT_IT_MEASURES###) must be copied EXACTLY as shown,
in English capital letters with ### on both sides — even if you are writing the content in Telugu or
any other language. NEVER translate, modify, or omit the markers. Only the content AFTER each marker
should be in the requested language.

###WHAT_IT_MEASURES###
###WHY_IT_MATTERS###
###HIGH_VALUE_REASONS###
###LOW_VALUE_REASONS###
###LIFESTYLE_SUGGESTIONS###
###WHEN_TO_CONSULT_DOCTOR###
###CLINICAL_SIGNIFICANCE###
###EDUCATIONAL_NOTES###"""

_PARAM_STRINGS = {
    "en": {
        "what_it_measures": "{test_name} is a laboratory value from your report. Your recorded result is {value} {unit} (reference range: {range}).",
        "why_it_matters": "Reference ranges help identify whether a result falls within the range typically seen in healthy individuals. Your result is currently classified as: {status}.",
        "high_reasons": "Values above the reference range can have multiple possible causes and require clinical context to interpret correctly — a doctor can determine the specific reason in your case.",
        "low_reasons": "Values below the reference range can have multiple possible causes and require clinical context to interpret correctly — a doctor can determine the specific reason in your case.",
        "lifestyle": "General wellness habits (balanced diet, regular activity, adequate sleep, avoiding tobacco/excess alcohol) support most lab values, but specific guidance depends on your full picture.",
        "consult": "Discuss this result with a qualified doctor, especially if it is marked outside the normal range, to understand what it means for you specifically.",
        "clinical": "This result should be interpreted alongside your other test values and clinical history by a qualified doctor.",
        "educational": "Ask your doctor or refer to a clinical reference for details on what {test_name} measures and its physiological role.",
        "unverified_note": " This test name could not be confidently matched to a standard reference, so treat its exact identification with caution and confirm with your lab or doctor.",
    },
    "te": {
        "what_it_measures": "{test_name} అనేది మీ రిపోర్ట్‌లోని ఒక ల్యాబ్ వాల్యూ. మీ రికార్డ్ చేసిన ఫలితం {value} {unit} (రిఫరెన్స్ రేంజ్: {range}).",
        "why_it_matters": "రిఫరెన్స్ రేంజ్‌లు ఒక ఫలితం సాధారణంగా ఆరోగ్యవంతమైన వ్యక్తుల్లో కనిపించే రేంజ్‌లో ఉందా అని గుర్తించడంలో సహాయపడతాయి. మీ ఫలితం ప్రస్తుతం ఇలా వర్గీకరించబడింది: {status}.",
        "high_reasons": "రిఫరెన్స్ రేంజ్ కంటే ఎక్కువ వాల్యూలకు అనేక సాధ్యమైన కారణాలు ఉండవచ్చు, వీటిని సరిగ్గా అర్థం చేసుకోవడానికి క్లినికల్ సందర్భం అవసరం — మీ విషయంలో ఖచ్చితమైన కారణం డాక్టర్ నిర్ధారించగలరు.",
        "low_reasons": "రిఫరెన్స్ రేంజ్ కంటే తక్కువ వాల్యూలకు అనేక సాధ్యమైన కారణాలు ఉండవచ్చు, వీటిని సరిగ్గా అర్థం చేసుకోవడానికి క్లినికల్ సందర్భం అవసరం — మీ విషయంలో ఖచ్చితమైన కారణం డాక్టర్ నిర్ధారించగలరు.",
        "lifestyle": "సాధారణ ఆరోగ్య అలవాట్లు (సమతుల్య ఆహారం, క్రమమైన వ్యాయామం, తగినంత నిద్ర, పొగాకు/మద్యం మానుకోవడం) చాలా ల్యాబ్ వాల్యూలకు మద్దతు ఇస్తాయి, కానీ నిర్దిష్ట సలహా మీ పూర్తి పరిస్థితిపై ఆధారపడి ఉంటుంది.",
        "consult": "ఈ ఫలితం గురించి అర్హత కలిగిన డాక్టర్‌తో చర్చించండి, ముఖ్యంగా ఇది నార్మల్ రేంజ్ బయట ఉంటే, మీ విషయంలో దీని అర్థం ఏమిటో తెలుసుకోవడానికి.",
        "clinical": "ఈ ఫలితాన్ని మీ ఇతర టెస్ట్ వాల్యూలు మరియు వైద్య చరిత్రతో కలిపి అర్హత కలిగిన డాక్టర్ అర్థం చేసుకోవాలి.",
        "educational": "{test_name} ఏమి కొలుస్తుందో మరియు దాని శారీరక పాత్ర గురించి వివరాల కోసం మీ డాక్టర్‌ని అడగండి లేదా క్లినికల్ రిఫరెన్స్ చూడండి.",
        "unverified_note": " ఈ టెస్ట్ పేరును స్టాండర్డ్ రిఫరెన్స్‌తో పూర్తిగా సరిపోల్చలేకపోయాము, కాబట్టి దీని ఖచ్చితమైన గుర్తింపును జాగ్రత్తగా పరిగణించి మీ ల్యాబ్ లేదా డాక్టర్‌తో నిర్ధారించుకోండి.",
    },
}


def _template_parameter_explanation(
    test_name: str, value: str | None, unit: str | None, reference_range: str | None,
    status: str, loinc_verified: bool, language: str,
) -> dict:
    """Deterministic, no-LLM fallback built entirely from extracted facts."""
    s = _PARAM_STRINGS.get(language, _PARAM_STRINGS["en"])
    fmt = dict(test_name=test_name, value=value or "Unknown", unit=unit or "", range=reference_range or "Unknown", status=status)

    what_it_measures = s["what_it_measures"].format(**fmt)
    if not loinc_verified:
        what_it_measures += s["unverified_note"]

    return {
        "what_it_measures": what_it_measures,
        "why_it_matters": s["why_it_matters"].format(**fmt),
        "high_value_reasons": s["high_reasons"],
        "low_value_reasons": s["low_reasons"],
        "lifestyle_suggestions": s["lifestyle"],
        "when_to_consult_doctor": s["consult"],
        "clinical_significance": s["clinical"],
        "educational_notes": s["educational"].format(**fmt),
    }


def explain_parameter(
    test_name: str,
    value: str | None,
    unit: str | None,
    reference_range: str | None,
    status: str,
    loinc_verified: bool,
    mode: str = "patient",
    language: str = "en",
) -> tuple[dict, str]:
    """Returns (content_dict, source) where source is 'ai_generated' or 'template_fallback'."""
    verification_note = (
        "This test name is verified against a standard lab test reference."
        if loinc_verified
        else "This test name could not be verified against the standard lab reference — "
             "treat identification of the exact test with caution and advise the user to "
             "confirm with their lab/doctor."
    )

    user_prompt = f"""Lab parameter facts (extracted directly from the user's report — treat as ground truth, do not contradict):
- Test name: {test_name}
- Value: {value if value else "Unknown"}
- Unit: {unit if unit else "Unknown"}
- Reference range: {reference_range if reference_range else "Unknown"}
- Status: {status}
- {verification_note}

{_PARAM_FORMAT_INSTRUCTIONS}"""

    system_prompt = (
        f"You are a medical explanation assistant. {_MODE_STYLE.get(mode, _MODE_STYLE['patient'])} "
        f"{_LANGUAGE_INSTRUCTION.get(language, _LANGUAGE_INSTRUCTION['en'])} "
        "Base your explanation only on the facts given. If the value or range is 'Unknown', say so "
        "honestly rather than inventing a number. Never state a diagnosis; only interpretive, "
        "educational, and general-lifestyle information."
    )

    try:
        raw = generate(system_prompt, user_prompt, language=language)
        parsed = _parse_marked_sections(raw, _PARAM_KEYS)
        if parsed:
            return parsed, AI_SOURCE
        logger.warning(
            "explain_parameter(%r): LLM call succeeded but marker parsing FAILED "
            "(language=%s, mode=%s). Raw response (first 500 chars): %r",
            test_name, language, mode, raw[:500],
        )
    except LLMUnavailableError:
        pass

    return (
        _template_parameter_explanation(test_name, value, unit, reference_range, status, loinc_verified, language),
        TEMPLATE_FALLBACK_SOURCE,
    )


# ---------------------------------------------------------------------------
# Flashcards — deliberately NOT LLM-generated (see module docstring).
# Built entirely from extracted test names + a hand-authored category
# glossary, so generation is instant, always available, and needs no
# provider at all.
# ---------------------------------------------------------------------------
_CATEGORY_GLOSSARY = {
    "en": {
        "CBC": "blood cell counts and overall blood health",
        "LFT": "liver function",
        "KFT": "kidney function",
        "Lipid": "cholesterol levels and cardiovascular risk",
        "Thyroid": "thyroid hormone levels",
        "Diabetes": "blood sugar control",
        "Urine": "urinary and kidney health",
        "Cardiac": "heart health",
        "Coagulation": "how well your blood clots",
        "Inflammatory": "inflammation in the body",
        "Iron Studies": "iron levels and anemia risk",
        "Vitamins": "vitamin levels",
        "Hormones": "hormone balance",
        "Tumor Markers": "certain cancer-related markers",
        "ABG": "blood oxygen and acid-base balance",
        "Vitals": "basic body function",
        "Electrolytes": "electrolyte and fluid balance",
        "Immunology": "immune system activity",
        "Infectious": "infection screening",
        "Stool": "digestive health",
    },
    "te": {
        "CBC": "రక్త కణాల లెక్క మరియు మొత్తం రక్త ఆరోగ్యం",
        "LFT": "కాలేయం పనితీరు",
        "KFT": "మూత్రపిండాల పనితీరు",
        "Lipid": "కొలెస్ట్రాల్ స్థాయిలు మరియు గుండె జబ్బు రిస్క్",
        "Thyroid": "థైరాయిడ్ హార్మోన్ స్థాయిలు",
        "Diabetes": "బ్లడ్ షుగర్ నియంత్రణ",
        "Urine": "మూత్రం మరియు మూత్రపిండాల ఆరోగ్యం",
        "Cardiac": "గుండె ఆరోగ్యం",
        "Coagulation": "మీ రక్తం ఎంత బాగా గడ్డకడుతుంది అనేది",
        "Inflammatory": "శరీరంలో ఇన్ఫ్లమేషన్",
        "Iron Studies": "ఐరన్ స్థాయిలు మరియు రక్తహీనత రిస్క్",
        "Vitamins": "విటమిన్ స్థాయిలు",
        "Hormones": "హార్మోన్ బ్యాలెన్స్",
        "Tumor Markers": "కొన్ని క్యాన్సర్-సంబంధిత మార్కర్లు",
        "ABG": "రక్తంలో ఆక్సిజన్ మరియు యాసిడ్-బేస్ బ్యాలెన్స్",
        "Vitals": "శరీరం యొక్క ప్రాథమిక పనితీరు",
        "Electrolytes": "ఎలక్ట్రోలైట్ మరియు ఫ్లూయిడ్ బ్యాలెన్స్",
        "Immunology": "రోగనిరోధక వ్యవస్థ యాక్టివిటీ",
        "Infectious": "ఇన్ఫెక్షన్ స్క్రీనింగ్",
        "Stool": "జీర్ణ ఆరోగ్యం",
    },
}
_DEFAULT_CATEGORY_DESC = {"en": "your general health", "te": "మీ సాధారణ ఆరోగ్యం"}

_FLASHCARD_DEFINITION_TEMPLATE = {
    "en": "{test_name} is a lab test related to {desc}. Your report recorded a value of {value} {unit} (reference range: {range}, status: {status}).",
    "te": "{test_name} అనేది {desc}కు సంబంధించిన ల్యాబ్ టెస్ట్. మీ రిపోర్ట్‌లో దీని వాల్యూ {value} {unit} (రిఫరెన్స్ రేంజ్: {range}, స్టేటస్: {status}) గా నమోదైంది.",
}
_FLASHCARD_RANGE_TERM_TEMPLATE = {
    "en": "The normal reference range for {test_name} is {range}. Values outside this range may need a doctor's review.",
    "te": "{test_name} యొక్క నార్మల్ రిఫరెన్స్ రేంజ్ {range}. ఈ రేంజ్ బయట ఉన్న వాల్యూలకు డాక్టర్ సమీక్ష అవసరం కావచ్చు.",
}


def generate_flashcards(
    report_type: str,
    parameters: list[dict],
    mode: str = "student",
    language: str = "en",
    max_cards: int = 12,
) -> list[dict]:
    """Builds flashcards directly from extracted test data — no LLM call.
    One card per unique test (term + definition using its actual recorded
    value), plus a reference-range card for tests that have one."""
    glossary = _CATEGORY_GLOSSARY.get(language, _CATEGORY_GLOSSARY["en"])
    default_desc = _DEFAULT_CATEGORY_DESC.get(language, _DEFAULT_CATEGORY_DESC["en"])
    def_template = _FLASHCARD_DEFINITION_TEMPLATE.get(language, _FLASHCARD_DEFINITION_TEMPLATE["en"])
    range_template = _FLASHCARD_RANGE_TERM_TEMPLATE.get(language, _FLASHCARD_RANGE_TERM_TEMPLATE["en"])

    cards: list[dict] = []
    seen: set[str] = set()
    for p in parameters:
        name = p.get("test_name_raw", "")
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())

        desc = glossary.get(p.get("category") or "", default_desc)
        definition = def_template.format(
            test_name=name, desc=desc,
            value=p.get("value") or "Unknown", unit=p.get("unit") or "",
            range=p.get("reference_range") or "Unknown", status=p.get("status") or "Unknown",
        )
        cards.append({"term": name, "definition": definition, "category": "Test", "reference_range": p.get("reference_range")})

        if p.get("reference_range") and len(cards) < max_cards:
            cards.append({
                "term": f"{name} — Reference Range",
                "definition": range_template.format(test_name=name, range=p["reference_range"]),
                "category": "Reference Range",
                "reference_range": p["reference_range"],
            })

        if len(cards) >= max_cards:
            break

    return cards[:max_cards]
