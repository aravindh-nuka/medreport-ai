# Combined Dockerfile for deploying MedReport AI as a SINGLE Hugging Face Space
# — one container, one URL, frontend served directly by the FastAPI backend.
#
# This is NOT used for local development (see the README for that — separate
# `npm run dev` + `uvicorn` processes, which gives hot-reload on both sides).
# This file exists only for the single-platform deployment path.
#
# Hugging Face Spaces requirement: must expose port 7860 — see app_port in
# the Space's README.md frontmatter (see README_HF_SPACE.md in this repo).

# ---- Stage 1: build the frontend ----
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
# Deliberately NOT setting VITE_API_BASE_URL here — same-origin deployment
# (frontend and backend share one domain/port in this setup), so the
# frontend's default relative "/api" path is exactly correct as-is.
RUN npm run build

# ---- Stage 2: backend + serve the built frontend ----
FROM python:3.11-slim
WORKDIR /app

# System dependencies some Python packages (PyMuPDF, etc.) need to build/run
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m spacy download en_core_web_sm

COPY backend/ .

# Copy the frontend build output from stage 1 into a location the backend
# serves as static files (see app/main.py's static-file mounting logic,
# which only activates if this directory exists — local dev without Docker
# is unaffected).
COPY --from=frontend-build /frontend/dist ./static

# Hugging Face Spaces requires writable storage under /data for persistence
# across restarts on paid tiers, but on the free tier (ephemeral disk) this
# just needs to exist so the app doesn't error on startup.
RUN mkdir -p storage/uploads storage/vector_store

EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
