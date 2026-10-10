"""
Per-report FAISS vector store.

Each report gets its own small FAISS index persisted to disk under
VECTOR_STORE_DIR/<report_id>/. This keeps retrieval strictly scoped to a
single report's content (a hard requirement: the chat assistant must only
ever answer from the uploaded report, never mix context across reports).
"""
import json
import os
from dataclasses import dataclass
from functools import lru_cache

import faiss
import numpy as np

from app.config import get_settings
from rag.chunking import Chunk, chunk_text

settings = get_settings()


@lru_cache
def _get_embedder():
    """Lazily load the embedding model on first use (not at import/startup), so the
    web server binds its port quickly and idle memory stays low.

    Uses fastembed (ONNX runtime) instead of sentence-transformers/PyTorch: same
    all-MiniLM-L6-v2 model, but ~5x less memory — required for Render's 512 MB tier."""
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=settings.EMBEDDING_MODEL, threads=1)


def _embed(texts: list[str]) -> np.ndarray:
    """Return L2-normalized float32 embeddings, shape (len(texts), dim)."""
    # Small batches keep peak memory low (Render free tier = 512 MB).
    vectors = np.asarray(list(_get_embedder().embed(texts, batch_size=8)), dtype="float32")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


@dataclass
class RetrievedChunk:
    chunk_id: int
    text: str
    score: float


def _report_dir(report_id: str) -> str:
    path = os.path.join(settings.VECTOR_STORE_DIR, report_id)
    os.makedirs(path, exist_ok=True)
    return path


def build_index(report_id: str, full_text: str) -> str:
    """Chunk the report, embed each chunk, build and persist a FAISS index.
    Returns the directory path where the index + chunk texts are stored."""
    chunks: list[Chunk] = chunk_text(full_text)
    if not chunks:
        raise ValueError("No text available to index for this report.")

    vectors = _embed([c.text for c in chunks])

    index = faiss.IndexFlatIP(vectors.shape[1])  # cosine similarity via normalized inner product
    index.add(vectors)

    directory = _report_dir(report_id)
    faiss.write_index(index, os.path.join(directory, "index.faiss"))
    with open(os.path.join(directory, "chunks.json"), "w", encoding="utf-8") as f:
        json.dump([{"chunk_id": c.chunk_id, "text": c.text} for c in chunks], f, ensure_ascii=False)

    return directory


def index_exists(report_id: str) -> bool:
    directory = os.path.join(settings.VECTOR_STORE_DIR, report_id)
    return os.path.exists(os.path.join(directory, "index.faiss")) and os.path.exists(
        os.path.join(directory, "chunks.json")
    )


def ensure_index(report_id: str, full_text: str) -> str:
    """Return the report's index directory, rebuilding it from the report text stored in
    the database if the files are gone. Free hosting tiers wipe the disk on every restart
    or sleep, but the report text lives in Postgres — so chat keeps working for old reports."""
    if index_exists(report_id):
        return os.path.join(settings.VECTOR_STORE_DIR, report_id)
    return build_index(report_id, full_text)


def retrieve(report_id: str, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    """Retrieve the most relevant chunks for a query, scoped to one report's index."""
    top_k = top_k or settings.RAG_TOP_K
    directory = _report_dir(report_id)
    index_path = os.path.join(directory, "index.faiss")
    chunks_path = os.path.join(directory, "chunks.json")

    if not (os.path.exists(index_path) and os.path.exists(chunks_path)):
        return []

    index = faiss.read_index(index_path)
    with open(chunks_path, encoding="utf-8") as f:
        chunk_lookup = {c["chunk_id"]: c["text"] for c in json.load(f)}

    query_vec = _embed([query])

    scores, indices = index.search(query_vec, min(top_k, index.ntotal))

    results: list[RetrievedChunk] = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        results.append(RetrievedChunk(chunk_id=int(idx), text=chunk_lookup.get(int(idx), ""), score=float(score)))
    return results
