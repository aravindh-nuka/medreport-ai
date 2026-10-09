"""Report-scoped chat endpoint. Persists conversation history per report.
Answers are generated directly in the selected language by the LLM (see
rag/chat_engine.py) rather than translated afterward."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Report, ChatMessage
from app.schemas import ChatRequest, ChatResponse, ChatMessageOut
from rag.chat_engine import answer_question

router = APIRouter(prefix="/api/chat", tags=["chat"])


_INDEX_UNAVAILABLE_MESSAGE_EN = (
    "This report's search index couldn't be built when it was uploaded, so chat isn't "
    "available for it. This can happen if the embedding model failed to download on first "
    "run. Please try re-uploading the report — if it keeps happening, check the backend "
    "terminal logs for a 'Vector index build FAILED' message with the underlying cause."
)
_INDEX_UNAVAILABLE_MESSAGE_TE = (
    "ఈ రిపోర్ట్ అప్‌లోడ్ అయినప్పుడు సెర్చ్ ఇండెక్స్ తయారు కాలేదు, కాబట్టి దీనికి చాట్ అందుబాటులో లేదు. "
    "దయచేసి రిపోర్ట్‌ని మళ్లీ అప్‌లోడ్ చేయడానికి ప్రయత్నించండి."
)


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == payload.report_id).first()
    if not report:
        raise HTTPException(404, "Report not found.")

    db.add(ChatMessage(report_id=report.id, role="user", content=payload.question, grounded=True))

    if not report.chat_available:
        answer = _INDEX_UNAVAILABLE_MESSAGE_TE if payload.language == "te" else _INDEX_UNAVAILABLE_MESSAGE_EN
        db.add(ChatMessage(report_id=report.id, role="assistant", content=answer, grounded=False))
        db.commit()
        return ChatResponse(answer=answer, grounded=False, retrieved_chunk_count=0, source_of_truth="template_fallback")

    result = answer_question(report.id, payload.question, mode=payload.mode, language=payload.language)

    db.add(ChatMessage(report_id=report.id, role="assistant", content=result.answer, grounded=result.grounded))
    db.commit()

    return ChatResponse(
        answer=result.answer, grounded=result.grounded,
        retrieved_chunk_count=result.retrieved_chunk_count, source_of_truth=result.source,
    )


@router.get("/{report_id}/history", response_model=list[ChatMessageOut])
def chat_history(report_id: str, db: Session = Depends(get_db)):
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.report_id == report_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
