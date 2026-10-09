"""Endpoints for listing reports, fetching report detail, generating the
Report Overview, computing Key Findings, and generating per-parameter
explanations."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Report, LabParameter, ReportSummary, ParameterExplanation
from app.schemas import (
    ReportOut, ReportDetailOut, SummaryRequest, ReportSummaryOut, KeyFindingsOut,
    ExplainParameterRequest, LabParameterOut,
)
from explanation.explanation_engine import explain_parameter, generate_report_overview

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("", response_model=list[ReportOut])
def list_reports(db: Session = Depends(get_db)):
    return db.query(Report).order_by(Report.uploaded_at.desc()).all()


@router.get("/{report_id}", response_model=ReportDetailOut)
def get_report(report_id: str, db: Session = Depends(get_db)):
    report = (
        db.query(Report)
        .options(joinedload(Report.parameters).joinedload(LabParameter.explanation))
        .filter(Report.id == report_id)
        .first()
    )
    if not report:
        raise HTTPException(404, "Report not found.")
    return report


@router.delete("/{report_id}")
def delete_report(report_id: str, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found.")
    db.delete(report)
    db.commit()
    return {"status": "deleted"}


@router.get("/{report_id}/key-findings", response_model=KeyFindingsOut)
def get_key_findings(report_id: str, db: Session = Depends(get_db)):
    """Computed directly from extracted LabParameter rows — no AI call needed.
    Verified findings are always returned before unverified ones."""
    report = db.query(Report).options(joinedload(Report.parameters)).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found.")

    verified_abnormal, verified_normal, unverified = [], [], []
    for p in report.parameters:
        if not p.loinc_verified:
            unverified.append(p)
        elif p.status == "Normal":
            verified_normal.append(p)
        elif p.status in ("Abnormal (Low)", "Abnormal (High)", "Critical"):
            verified_abnormal.append(p)
        else:
            unverified.append(p)  # status Unknown even though name verified

    return KeyFindingsOut(verified_abnormal=verified_abnormal, verified_normal=verified_normal, unverified=unverified)


@router.post("/overview", response_model=ReportSummaryOut)
def get_or_create_overview(payload: SummaryRequest, db: Session = Depends(get_db)):
    """Generates (or returns cached) Report Overview content: short abstract,
    doctor-style narrative, final verdict, and grouped recommendations."""
    report = db.query(Report).options(joinedload(Report.parameters)).filter(Report.id == payload.report_id).first()
    if not report:
        raise HTTPException(404, "Report not found.")

    existing = (
        db.query(ReportSummary)
        .filter(ReportSummary.report_id == report.id, ReportSummary.mode == payload.mode,
                ReportSummary.language == payload.language)
        .first()
    )
    if existing:
        return existing

    param_dicts = [
        {
            "test_name_raw": p.test_name_raw, "value": p.value, "unit": p.unit,
            "reference_range": p.reference_range, "status": p.status, "loinc_verified": p.loinc_verified,
        }
        for p in report.parameters
    ]
    result, source = generate_report_overview(report.report_type, param_dicts, mode=payload.mode, language=payload.language)

    summary = ReportSummary(
        report_id=report.id, mode=payload.mode, language=payload.language,
        short_summary=result["short_summary"], detailed_explanation=result["detailed_explanation"],
        final_verdict=result["final_verdict"], suggestions=result["suggestions"],
        precautions=result["precautions"], lifestyle_advice=result["lifestyle_advice"],
        diet_recommendations=result["diet_recommendations"], exercise_suggestions=result["exercise_suggestions"],
        followup_advice=result["followup_advice"], doctor_consultation_advice=result["doctor_consultation_advice"],
        monitoring_advice=result["monitoring_advice"], source_of_truth=source,
    )

    # Only cache real AI content. A template-fallback result is shown once and
    # NOT persisted, so the next request retries the real LLM chain fresh
    # instead of permanently trapping the user on the basic offline version.
    if source == "ai_generated":
        db.add(summary)
        db.commit()
        db.refresh(summary)

    return summary


# Backward-compatible alias (older frontend builds may call /summary)
@router.post("/summary", response_model=ReportSummaryOut)
def get_or_create_summary_alias(payload: SummaryRequest, db: Session = Depends(get_db)):
    return get_or_create_overview(payload, db)


@router.post("/parameter/explain", response_model=LabParameterOut)
def explain_report_parameter(payload: ExplainParameterRequest, db: Session = Depends(get_db)):
    parameter = db.query(LabParameter).filter(LabParameter.id == payload.parameter_id).first()
    if not parameter:
        raise HTTPException(404, "Lab parameter not found.")

    existing = (
        db.query(ParameterExplanation)
        .filter(ParameterExplanation.parameter_id == parameter.id, ParameterExplanation.mode == payload.mode,
                ParameterExplanation.language == payload.language)
        .first()
    )
    if not existing:
        result, source = explain_parameter(
            test_name=parameter.test_name_normalized or parameter.test_name_raw,
            value=parameter.value, unit=parameter.unit, reference_range=parameter.reference_range,
            status=parameter.status, loinc_verified=parameter.loinc_verified,
            mode=payload.mode, language=payload.language,
        )

        existing = ParameterExplanation(
            parameter_id=parameter.id, mode=payload.mode, language=payload.language,
            what_it_measures=result["what_it_measures"], why_it_matters=result["why_it_matters"],
            high_value_reasons=result["high_value_reasons"], low_value_reasons=result["low_value_reasons"],
            lifestyle_suggestions=result["lifestyle_suggestions"],
            when_to_consult_doctor=result["when_to_consult_doctor"],
            clinical_significance=result["clinical_significance"], educational_notes=result["educational_notes"],
            source_of_truth=source,
        )

        # Same rule as the report overview: only cache genuine AI content, so a
        # template-fallback explanation doesn't permanently replace a real one.
        if source == "ai_generated":
            db.add(existing)
            db.commit()

    parameter.explanation = existing
    return parameter
