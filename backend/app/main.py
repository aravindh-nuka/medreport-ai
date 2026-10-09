"""
MedReport AI — FastAPI application entrypoint.

Run locally (separate frontend/backend, hot-reload on both):
    uvicorn app.main:app --reload --port 8000

Interactive API docs available at /docs (Swagger) and /redoc.
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import get_settings
from app.database import init_db
from app.routes_upload import router as upload_router
from app.routes_report import router as report_router
from app.routes_chat import router as chat_router
from app.routes_flashcards import router as flashcards_router

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "AI Digital Medical Report Interpreter. Extracts structured facts from digital "
        "PDF reports, verifies test names against a local LOINC subset, and provides "
        "grounded AI explanations, RAG-based chat, and flashcards — never fabricating "
        "medical information."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(report_router)
app.include_router(chat_router)
app.include_router(flashcards_router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health", tags=["system"])
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}


# --- Combined single-container deployment (Hugging Face Spaces) ---
# Only activates if a built frontend exists at backend/static/ — the
# Dockerfile copies the frontend's `dist/` build there. In local development
# (frontend and backend run as two separate processes, no static/ directory),
# this block does nothing and the app behaves exactly as before.
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

if STATIC_DIR.is_dir():
    if (STATIC_DIR / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="frontend-assets")
    if (STATIC_DIR / "icons").is_dir():
        app.mount("/icons", StaticFiles(directory=STATIC_DIR / "icons"), name="frontend-icons")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        # Never let this catch-all swallow a genuinely missing /api/* route —
        # that should be a real 404, not the frontend's index.html.
        if full_path.startswith("api/"):
            raise HTTPException(404, "Not found")

        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)

        # Any other path (including React Router client-side routes like
        # /reports/abc123 that don't correspond to a real file) falls back to
        # index.html so the client-side router can take over.
        return FileResponse(STATIC_DIR / "index.html")
