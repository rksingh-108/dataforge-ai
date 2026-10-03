"""Document text extraction for PDF, DOCX and TXT."""
from __future__ import annotations

import io

SUPPORTED = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
}


class ExtractionError(ValueError):
    """Raised when a document cannot be turned into text."""


def detect_kind(filename: str, content_type: str) -> str:
    if content_type in SUPPORTED:
        return SUPPORTED[content_type]
    lowered = (filename or "").lower()
    for extension, kind in ((".pdf", "pdf"), (".docx", "docx"), (".txt", "txt")):
        if lowered.endswith(extension):
            return kind
    raise ExtractionError(
        "Unsupported document type. Only PDF, DOCX and TXT files can be processed."
    )


def extract(data: bytes, *, filename: str, content_type: str) -> dict:
    """Extract text and page/section structure. Returns `{kind, pages, page_count}`."""
    kind = detect_kind(filename, content_type)
    if kind == "pdf":
        return _extract_pdf(data)
    if kind == "docx":
        return _extract_docx(data)
    return _extract_txt(data)


def _extract_pdf(data: bytes) -> dict:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        pages = []
        for number, page in enumerate(reader.pages, start=1):
            pages.append({"page": number, "text": page.extract_text() or ""})
    except Exception as exc:
        raise ExtractionError(f"Could not read the PDF: {str(exc)[:200]}") from exc
    return {"kind": "pdf", "pages": pages, "page_count": len(pages)}


def _extract_docx(data: bytes) -> dict:
    import docx

    try:
        document = docx.Document(io.BytesIO(data))
        paragraphs = [p.text for p in document.paragraphs]
    except Exception as exc:
        raise ExtractionError(f"Could not read the DOCX: {str(exc)[:200]}") from exc

    # DOCX has no reliable page boundaries; treat the whole body as one "page"
    # and let chunking provide the granularity.
    return {
        "kind": "docx",
        "pages": [{"page": 1, "text": "\n".join(paragraphs)}],
        "page_count": 1,
    }


def _extract_txt(data: bytes) -> dict:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExtractionError("The text file is not valid UTF-8.") from exc
    return {"kind": "txt", "pages": [{"page": 1, "text": text}], "page_count": 1}
