"""RAG ingestion pipeline: extract → chunk → embed.

The embeddings are produced by whichever embedding provider is configured. The
result is returned to the caller (the platform API), which owns persistence.
"""
from __future__ import annotations

import logging

from ai_service.providers.base import EmbeddingProvider
from ai_service.rag.chunking import chunk_text
from ai_service.rag.extract import extract
from ai_service.security.injection import scan_for_injection, summarise_findings

logger = logging.getLogger("ai_service.rag")


def process_document(
    data: bytes,
    *,
    filename: str,
    content_type: str,
    embedder: EmbeddingProvider,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> dict:
    """Extract, chunk and embed a document.

    Returns:
        {kind, page_count, chunk_count, chunks: [{index, content, source_label,
         embedding, metadata}], scan: {...}}
    """
    extracted = extract(data, filename=filename, content_type=content_type)
    pages = extracted["pages"]

    chunks: list[dict] = []
    next_index = 0
    for page in pages:
        label = f"page-{page['page']}"
        for chunk in chunk_text(page.get("text", ""), chunk_size=chunk_size,
                                overlap=overlap, source_label=label):
            chunks.append(
                {
                    "index": next_index,
                    "content": chunk.content,
                    "source_label": chunk.source_label,
                    "metadata": {"page": page["page"]},
                }
            )
            next_index += 1

    if not chunks:
        return {
            "kind": extracted["kind"],
            "page_count": extracted["page_count"],
            "chunk_count": 0,
            "chunks": [],
            "scan": {"flagged": False, "categories": [], "count": 0},
        }

    # Flag suspicious content once for the whole document (informational).
    findings = []
    for chunk in chunks[:50]:
        findings.extend(scan_for_injection(chunk["content"]))

    vectors = embedder.embed([chunk["content"] for chunk in chunks])
    if len(vectors) != len(chunks):
        raise ValueError("Embedding provider returned the wrong number of vectors.")
    for chunk, vector in zip(chunks, vectors, strict=True):
        chunk["embedding"] = vector

    return {
        "kind": extracted["kind"],
        "page_count": extracted["page_count"],
        "chunk_count": len(chunks),
        "chunks": chunks,
        "scan": summarise_findings(findings),
    }
