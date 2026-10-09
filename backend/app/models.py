"""
ORM models.

Design principle: extracted facts and AI-generated content are stored in
clearly separate columns/tables so the UI can always show the user which
parts came straight from their report (source_of_truth = "extracted")
versus which parts are AI interpretation (source_of_truth = "ai_generated").
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Float, Text, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    original_filename: Mapped[str] = mapped_column(String)
    stored_path: Mapped[str] = mapped_column(String)
    report_type: Mapped[str] = mapped_column(String, default="Unknown")  # CBC, LFT, KFT, etc.

    # --- Extracted header facts (nullable -> "Unknown" if not found, never guessed) ---
    patient_name: Mapped[str | None] = mapped_column(String, nullable=True)
    patient_age: Mapped[str | None] = mapped_column(String, nullable=True)
    patient_sex: Mapped[str | None] = mapped_column(String, nullable=True)
    hospital_name: Mapped[str | None] = mapped_column(String, nullable=True)
    doctor_name: Mapped[str | None] = mapped_column(String, nullable=True)
    sample_date: Mapped[str | None] = mapped_column(String, nullable=True)

    raw_text: Mapped[str] = mapped_column(Text)  # full extracted text, used for RAG indexing
    vector_index_path: Mapped[str | None] = mapped_column(String, nullable=True)

    @property
    def chat_available(self) -> bool:
        """True if the RAG index was built successfully for this report. If False,
        the AI Chat page will not be able to find anything — see the upload route's
        logs for the underlying cause (e.g. embedding model failed to load)."""
        return self.vector_index_path is not None

    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    parameters: Mapped[list["LabParameter"]] = relationship(back_populates="report", cascade="all, delete-orphan")
    chat_messages: Mapped[list["ChatMessage"]] = relationship(back_populates="report", cascade="all, delete-orphan")
    flashcards: Mapped[list["Flashcard"]] = relationship(back_populates="report", cascade="all, delete-orphan")
    # One row per (mode, language) combination — cached so switching mode/language
    # doesn't require a fresh LLM call after the first generation.
    summaries: Mapped[list["ReportSummary"]] = relationship(back_populates="report", cascade="all, delete-orphan")


class LabParameter(Base):
    """One row per extracted lab test value. This is the 'extracted facts' table —
    everything here comes directly from the report text, never inferred."""
    __tablename__ = "lab_parameters"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    report_id: Mapped[str] = mapped_column(String, ForeignKey("reports.id"))

    test_name_raw: Mapped[str] = mapped_column(String)          # as found in the report
    test_name_normalized: Mapped[str | None] = mapped_column(String, nullable=True)  # LOINC-matched canonical name
    loinc_code: Mapped[str | None] = mapped_column(String, nullable=True)
    loinc_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    loinc_category: Mapped[str | None] = mapped_column(String, nullable=True)  # e.g. "CBC", "LFT" — used for flashcard glossary lookup

    value: Mapped[str | None] = mapped_column(String, nullable=True)   # kept as string ("Unknown" if absent)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    reference_range: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="Unknown")     # Normal / Abnormal / Critical / Unknown

    report: Mapped["Report"] = relationship(back_populates="parameters")
    explanation: Mapped["ParameterExplanation"] = relationship(
        back_populates="parameter", uselist=False, cascade="all, delete-orphan"
    )


class ParameterExplanation(Base):
    """AI-generated explanation content for a single lab parameter, cached per mode+language
    so we don't re-call the LLM every time the user reopens a card."""
    __tablename__ = "parameter_explanations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    parameter_id: Mapped[str] = mapped_column(String, ForeignKey("lab_parameters.id"))
    mode: Mapped[str] = mapped_column(String)       # patient | student | doctor
    language: Mapped[str] = mapped_column(String, default="en")

    what_it_measures: Mapped[str] = mapped_column(Text, default="")
    why_it_matters: Mapped[str] = mapped_column(Text, default="")
    high_value_reasons: Mapped[str] = mapped_column(Text, default="")
    low_value_reasons: Mapped[str] = mapped_column(Text, default="")
    lifestyle_suggestions: Mapped[str] = mapped_column(Text, default="")
    when_to_consult_doctor: Mapped[str] = mapped_column(Text, default="")
    clinical_significance: Mapped[str] = mapped_column(Text, default="")
    educational_notes: Mapped[str] = mapped_column(Text, default="")

    source_of_truth: Mapped[str] = mapped_column(String, default="ai_generated")  # "ai_generated" or "template_fallback"

    parameter: Mapped["LabParameter"] = relationship(back_populates="explanation")


class ReportSummary(Base):
    """
    AI-generated 'Report Overview' content, cached per mode + language.
    Structured to match the product's Report Overview page order: title is
    derived from Report.report_type (not stored here), followed by abstract,
    doctor-style narrative, final verdict, and grouped recommendations.
    Key Findings (verified/normal/unknown) are NOT stored here — they are
    computed directly from LabParameter rows, since that's ground truth and
    needs no AI generation or caching.
    """
    __tablename__ = "report_summaries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    report_id: Mapped[str] = mapped_column(String, ForeignKey("reports.id"))
    mode: Mapped[str] = mapped_column(String, default="patient")
    language: Mapped[str] = mapped_column(String, default="en")

    short_summary: Mapped[str] = mapped_column(Text, default="")          # ~300 char abstract
    detailed_explanation: Mapped[str] = mapped_column(Text, default="")   # doctor-style bulleted narrative
    final_verdict: Mapped[str] = mapped_column(Text, default="")

    suggestions: Mapped[str] = mapped_column(Text, default="")
    precautions: Mapped[str] = mapped_column(Text, default="")
    lifestyle_advice: Mapped[str] = mapped_column(Text, default="")
    diet_recommendations: Mapped[str] = mapped_column(Text, default="")
    exercise_suggestions: Mapped[str] = mapped_column(Text, default="")
    followup_advice: Mapped[str] = mapped_column(Text, default="")
    doctor_consultation_advice: Mapped[str] = mapped_column(Text, default="")
    monitoring_advice: Mapped[str] = mapped_column(Text, default="")
    source_of_truth: Mapped[str] = mapped_column(String, default="ai_generated")  # "ai_generated" or "template_fallback"

    report: Mapped["Report"] = relationship(back_populates="summaries")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    report_id: Mapped[str] = mapped_column(String, ForeignKey("reports.id"))
    role: Mapped[str] = mapped_column(String)  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    grounded: Mapped[bool] = mapped_column(Boolean, default=True)  # False if "couldn't find" fallback
    # "ai" if the LLM answered normally, "template_fallback" if every LLM provider
    # failed and this is a raw excerpt surfaced directly from the report instead.
    answer_source: Mapped[str] = mapped_column(String, default="ai")
    retrieved_chunks: Mapped[list | None] = mapped_column(JSON, nullable=True)  # chunk ids used, for transparency
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    report: Mapped["Report"] = relationship(back_populates="chat_messages")


class Flashcard(Base):
    __tablename__ = "flashcards"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    report_id: Mapped[str] = mapped_column(String, ForeignKey("reports.id"))
    term: Mapped[str] = mapped_column(String)
    definition: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String, default="General")  # Test / Disease / Concept / etc.
    reference_range: Mapped[str | None] = mapped_column(String, nullable=True)
    language: Mapped[str] = mapped_column(String, default="en")
    bookmarked: Mapped[bool] = mapped_column(Boolean, default=False)

    report: Mapped["Report"] = relationship(back_populates="flashcards")
