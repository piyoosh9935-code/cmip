"""Minimal sentence-aware chunker. Our synthetic notes are short (a few sentences,
well under CHUNK_SIZE) so most notes end up as a single chunk - this exists so the
pipeline is correct for longer real-world notes too, not because it's load-bearing
for the demo data."""

import re

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    text = text.strip()
    if len(text) <= chunk_size:
        return [text] if text else []

    sentences = _SENTENCE_RE.split(text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(current)
        current = sentence[:chunk_size] if len(sentence) > chunk_size else sentence
    if current:
        chunks.append(current)

    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            tail = chunks[i - 1][-overlap:]
            overlapped.append(f"{tail} {chunks[i]}".strip())
        return overlapped
    return chunks
