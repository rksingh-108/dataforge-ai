"""Text chunking.

A paragraph-aware splitter: we try to break on blank lines, then sentence
boundaries, and only fall back to a hard character cut. Each chunk carries a
source label (page or section) so answers can cite their origin.
"""
from __future__ import annotations

from dataclasses import dataclass

_SENTENCE_ENDINGS = (". ", "! ", "? ", ".\n", "!\n", "?\n")


@dataclass
class Chunk:
    index: int
    content: str
    source_label: str


def chunk_text(text: str, *, chunk_size: int = 1000, overlap: int = 150,
               source_label: str = "") -> list[Chunk]:
    """Split `text` into overlapping chunks of at most `chunk_size` characters."""
    normalised = _normalise(text)
    if not normalised:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")
    overlap = max(0, min(overlap, chunk_size // 2))

    chunks: list[Chunk] = []
    start = 0
    length = len(normalised)
    index = 0
    while start < length:
        end = min(start + chunk_size, length)
        if end < length:
            end = _find_break(normalised, start, end)
        piece = normalised[start:end].strip()
        if piece:
            chunks.append(Chunk(index=index, content=piece, source_label=source_label))
            index += 1
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return chunks


def _normalise(text: str) -> str:
    lines = [line.rstrip() for line in (text or "").replace("\r\n", "\n").split("\n")]
    return "\n".join(lines).strip()


def _find_break(text: str, start: int, end: int) -> int:
    """Look backwards from `end` for a natural boundary."""
    window_start = max(start + 1, end - 200)
    window = text[window_start:end]

    paragraph = window.rfind("\n\n")
    if paragraph != -1:
        return window_start + paragraph + 2

    best = -1
    for marker in _SENTENCE_ENDINGS:
        position = window.rfind(marker)
        if position > best:
            best = position + len(marker)
    if best > 0:
        return window_start + best

    space = window.rfind(" ")
    if space > 0:
        return window_start + space + 1
    return end
