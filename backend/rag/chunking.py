"""Splits report text into overlapping chunks for embedding + retrieval."""
from dataclasses import dataclass

from app.config import get_settings

settings = get_settings()


@dataclass
class Chunk:
    chunk_id: int
    text: str


def chunk_text(text: str, size: int | None = None, overlap: int | None = None) -> list[Chunk]:
    size = size or settings.CHUNK_SIZE_CHARS
    overlap = overlap or settings.CHUNK_OVERLAP_CHARS

    text = text.strip()
    if not text:
        return []

    chunks: list[Chunk] = []
    start = 0
    idx = 0
    while start < len(text):
        end = min(start + size, len(text))
        piece = text[start:end].strip()
        if piece:
            chunks.append(Chunk(chunk_id=idx, text=piece))
            idx += 1
        if end == len(text):
            break
        start = end - overlap
    return chunks
