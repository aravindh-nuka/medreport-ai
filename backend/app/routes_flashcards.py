"""Auto-generated learning flashcards for a report, cached per (mode, language)
after first generation, with per-card bookmarking."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Report, Flashcard
from app.schemas import FlashcardOut
from explanation.explanation_engine import generate_flashcards

router = APIRouter(prefix="/api/flashcards", tags=["flashcards"])


@router.get("/{report_id}", response_model=list[FlashcardOut])
def get_flashcards(report_id: str, mode: str = "student", language: str = "en", db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found.")

    existing = (
        db.query(Flashcard)
        .filter(Flashcard.report_id == report_id, Flashcard.language == language)
        .all()
    )
    if existing:
        return existing

    param_dicts = [
        {
            "test_name_raw": p.test_name_raw, "value": p.value, "unit": p.unit,
            "reference_range": p.reference_range, "status": p.status, "category": p.loinc_category,
        }
        for p in report.parameters
    ]
    cards = generate_flashcards(report.report_type, param_dicts, mode=mode, language=language)

    for c in cards:
        db.add(Flashcard(
            report_id=report.id, term=c["term"], definition=c["definition"],
            category=c["category"], reference_range=c["reference_range"], language=language,
        ))
    db.commit()

    return db.query(Flashcard).filter(Flashcard.report_id == report_id, Flashcard.language == language).all()


@router.post("/{flashcard_id}/toggle-bookmark", response_model=FlashcardOut)
def toggle_bookmark(flashcard_id: str, db: Session = Depends(get_db)):
    card = db.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
    if not card:
        raise HTTPException(404, "Flashcard not found.")
    card.bookmarked = not card.bookmarked
    db.commit()
    db.refresh(card)
    return card
