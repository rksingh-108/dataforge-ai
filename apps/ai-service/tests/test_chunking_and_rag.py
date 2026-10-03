"""RAG pipeline tests: chunking boundaries, extraction and end-to-end processing."""
from __future__ import annotations

import io

from ai_service.providers.testing import DeterministicEmbeddingProvider
from ai_service.rag.chunking import chunk_text
from ai_service.rag.extract import detect_kind, extract
from ai_service.rag.pipeline import process_document


def test_chunk_text_splits_on_paragraph_boundaries():
    text = ("Paragraph one. " * 20 + "\n\n") * 3
    chunks = chunk_text(text, chunk_size=200, overlap=20)
    assert len(chunks) > 1
    assert all(len(c.content) <= 200 for c in chunks)
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_chunk_text_produces_overlap():
    text = "".join(f"Sentence number {i}. " for i in range(50))
    chunks = chunk_text(text, chunk_size=150, overlap=50)
    assert len(chunks) >= 3
    # Consecutive chunks share characters (overlap), so the union is not disjoint.
    total = sum(len(c.content) for c in chunks)
    assert total > len(text.strip())


def test_chunk_text_empty_returns_no_chunks():
    assert chunk_text("", chunk_size=100, overlap=10) == []
    assert chunk_text("   \n\n  ", chunk_size=100, overlap=10) == []


def test_detect_kind_by_content_type_and_extension():
    assert detect_kind("a.pdf", "application/pdf") == "pdf"
    assert detect_kind("a.docx", "") == "docx"
    assert detect_kind("a.txt", "text/plain") == "txt"


def test_detect_kind_rejects_unsupported():
    import pytest

    from ai_service.rag.extract import ExtractionError

    with pytest.raises(ExtractionError):
        detect_kind("a.exe", "application/octet-stream")


def test_extract_txt():
    result = extract(b"hello\nworld", filename="a.txt", content_type="text/plain")
    assert result["kind"] == "txt"
    assert result["page_count"] == 1
    assert "hello" in result["pages"][0]["text"]


def test_extract_docx_roundtrip():
    import docx

    document = docx.Document()
    document.add_paragraph("Quarterly revenue was strong.")
    buffer = io.BytesIO()
    document.save(buffer)

    result = extract(buffer.getvalue(), filename="a.docx",
                     content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert result["kind"] == "docx"
    assert "Quarterly revenue" in result["pages"][0]["text"]


def test_process_document_produces_embedded_chunks(settings):
    text = ("Our refund policy allows returns within 30 days. " * 20).encode()
    embedder = DeterministicEmbeddingProvider(settings.embeddings)

    result = process_document(text, filename="policy.txt", content_type="text/plain",
                              embedder=embedder, chunk_size=200, overlap=20)

    assert result["chunk_count"] == len(result["chunks"])
    assert result["chunk_count"] > 1
    for chunk in result["chunks"]:
        assert len(chunk["embedding"]) == settings.embeddings.dim
        assert chunk["source_label"] == "page-1"


def test_process_document_reports_empty_documents(settings):
    embedder = DeterministicEmbeddingProvider(settings.embeddings)
    result = process_document(b"   ", filename="blank.txt", content_type="text/plain",
                              embedder=embedder)
    assert result["chunk_count"] == 0
    assert result["chunks"] == []
