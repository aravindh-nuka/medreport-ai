"""Upload endpoint: accepts a digital PDF, runs the full extraction pipeline,
persists structured facts, and builds the per-report RAG index."""
import logging
import os
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Report, LabParameter
from app.schemas import ReportOut
from extraction.pdf_extractor import extract_pdf, UnsupportedPDFError
from extraction.structured_parser import extract_patient_info, extract_lab_parameters, guess_report_type
from rag.vector_store import build_index

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reports", tags=["upload"])
settings = get_settings()


@router.post("/upload", response_model=ReportOut)
async def upload_report(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported. Scanned images are not accepted.")

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_MB:
        raise HTTPException(400, f"File too large ({size_mb:.1f}MB). Max allowed is {settings.MAX_UPLOAD_MB}MB.")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    stored_name = f"{uuid.uuid4()}.pdf"
    stored_path = os.path.join(settings.UPLOAD_DIR, stored_name)
    with open(stored_path, "wb") as f:
        f.write(contents)

    try:
        extraction = extract_pdf(stored_path)
    except UnsupportedPDFError as e:
        os.remove(stored_path)
        raise HTTPException(422, str(e)) from e

    patient_info = extract_patient_info(extraction.full_text)
    parameters = extract_lab_parameters(extraction.full_text)
    report_type = guess_report_type(extraction.full_text, parameters)

    report = Report(
        original_filename=file.filename,
        stored_path=stored_path,
        report_type=report_type,
        patient_name=patient_info.patient_name,
        patient_age=patient_info.patient_age,
        patient_sex=patient_info.patient_sex,
        hospital_name=patient_info.hospital_name,
        doctor_name=patient_info.doctor_name,
        sample_date=patient_info.sample_date,
        raw_text=extraction.full_text,
    )
    db.add(report)
    db.flush()  # get report.id before building index / adding children

    for p in parameters:
        db.add(
            LabParameter(
                report_id=report.id,
                test_name_raw=p.test_name_raw,
                test_name_normalized=p.test_name_normalized,
                loinc_code=p.loinc_code,
                loinc_verified=p.loinc_verified,
                loinc_category=p.category,
                value=p.value,
                unit=p.unit,
                reference_range=p.reference_range,
                status=p.status,
            )
        )

    try:
        index_dir = build_index(report.id, extraction.full_text)
        report.vector_index_path = index_dir
        logger.info("Vector index built for report %s at %s", report.id, index_dir)
    except Exception as e:  # noqa: BLE001 — broadened from ValueError: an embedding-model
        # load failure (e.g. first-run download issue) is NOT a ValueError and must not
        # crash the whole upload. Chat will show "couldn't find" for this report until
        # re-uploaded, but the report itself, its extracted data, and all other features
        # (Overview, Individual Test Analysis, Flashcards) remain fully usable.
        report.vector_index_path = None
        logger.error("Vector index build FAILED for report %s — chat will be unavailable "
                     "for this report. Cause: %s", report.id, e, exc_info=True)

    db.commit()
    db.refresh(report)
    return report
