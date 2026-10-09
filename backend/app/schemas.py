"""Pydantic schemas for API request/response bodies."""
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel

Mode = Literal["patient", "student", "doctor"]
Lang = Literal["en", "te"]


class ParameterExplanationOut(BaseModel):
    what_it_measures: str
    why_it_matters: str
    high_value_reasons: str
    low_value_reasons: str
    lifestyle_suggestions: str
    when_to_consult_doctor: str
    clinical_significance: str
    educational_notes: str
    source_of_truth: str = "ai_generated"

    class Config:
        from_attributes = True


class LabParameterOut(BaseModel):
    id: str
    test_name_raw: str
    test_name_normalized: Optional[str]
    loinc_code: Optional[str]
    loinc_verified: bool
    loinc_category: Optional[str] = None
    value: Optional[str]
    unit: Optional[str]
    reference_range: Optional[str]
    status: str
    explanation: Optional[ParameterExplanationOut] = None

    class Config:
        from_attributes = True


class ReportSummaryOut(BaseModel):
    short_summary: str
    detailed_explanation: str
    final_verdict: str
    suggestions: str
    precautions: str
    lifestyle_advice: str
    diet_recommendations: str
    exercise_suggestions: str
    followup_advice: str
    doctor_consultation_advice: str
    monitoring_advice: str
    source_of_truth: str = "ai_generated"

    class Config:
        from_attributes = True


class KeyFindingsOut(BaseModel):
    """Computed directly from extracted LabParameter rows — no AI involved.
    Verified findings always precede unknown ones, per product requirement."""
    verified_abnormal: list[LabParameterOut] = []
    verified_normal: list[LabParameterOut] = []
    unverified: list[LabParameterOut] = []


class ReportOut(BaseModel):
    id: str
    original_filename: str
    report_type: str
    patient_name: Optional[str]
    patient_age: Optional[str]
    patient_sex: Optional[str]
    hospital_name: Optional[str]
    doctor_name: Optional[str]
    sample_date: Optional[str]
    uploaded_at: datetime
    chat_available: bool = True

    class Config:
        from_attributes = True


class ReportDetailOut(ReportOut):
    parameters: list[LabParameterOut] = []


class ChatRequest(BaseModel):
    report_id: str
    question: str
    mode: Mode = "patient"
    language: Lang = "en"


class ChatMessageOut(BaseModel):
    role: str
    content: str
    grounded: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    answer: str
    grounded: bool
    retrieved_chunk_count: int
    source_of_truth: str = "ai_generated"  # "ai_generated" or "template_fallback"


class FlashcardOut(BaseModel):
    id: str
    term: str
    definition: str
    category: str
    reference_range: Optional[str] = None
    bookmarked: bool = False

    class Config:
        from_attributes = True


class SummaryRequest(BaseModel):
    report_id: str
    mode: Mode = "patient"
    language: Lang = "en"


class ExplainParameterRequest(BaseModel):
    parameter_id: str
    mode: Mode = "patient"
    language: Lang = "en"
