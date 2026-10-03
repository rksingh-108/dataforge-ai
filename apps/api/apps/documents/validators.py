"""Upload validation.

Defense in depth: we check the declared content type, the extension, the size,
and the *magic bytes* of the file itself. A file that claims to be a PDF but does
not start with ``%PDF`` is rejected. This prevents content-type spoofing and
polyglot uploads.
"""
from __future__ import annotations

import hashlib

from django.conf import settings
from rest_framework import serializers

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

_MAGIC = {
    "pdf": [b"%PDF"],
    "docx": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],  # OOXML is a zip
    "txt": [],  # validated by decoding instead
}

_CONTENT_TYPE_BY_EXT = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
}


def _extension(filename: str) -> str:
    name = filename.lower().rsplit("/", 1)[-1]
    if "." not in name:
        raise serializers.ValidationError("A file extension is required (.pdf, .docx or .txt).")
    return name.rsplit(".", 1)[-1]


def validate_upload(uploaded_file) -> dict:
    """Validate an uploaded file and return normalized metadata.

    Raises ``serializers.ValidationError`` on any problem.
    """
    filename = (uploaded_file.name or "").strip()
    if not filename or ".." in filename or "\\" in filename:
        raise serializers.ValidationError("Invalid file name.")

    extension = _extension(filename)
    if extension not in ALLOWED_EXTENSIONS:
        raise serializers.ValidationError(
            f"Unsupported file type '.{extension}'. Allowed: pdf, docx, txt."
        )

    declared_type = (getattr(uploaded_file, "content_type", "") or "").lower()
    expected_type = _CONTENT_TYPE_BY_EXT[extension]
    # Tolerate the generic types browsers sometimes send for .txt files.
    generic_txt = extension == "txt" and declared_type in {"application/octet-stream", "text/*"}
    if declared_type and declared_type != expected_type and not generic_txt:
        raise serializers.ValidationError(
            f"Declared content type '{declared_type}' does not match '.{extension}'."
        )

    max_bytes = settings.DOCUMENT_MAX_UPLOAD_BYTES
    if uploaded_file.size > max_bytes:
        raise serializers.ValidationError(
            f"File is too large. Maximum is {max_bytes // (1024 * 1024)} MB."
        )

    head = _read_head(uploaded_file)
    expected_magic = _MAGIC.get(extension, [])
    if expected_magic and not any(head.startswith(sig) for sig in expected_magic):
        raise serializers.ValidationError(
            f"The file content does not look like a valid .{extension} file."
        )
    if extension == "txt":
        _validate_text(uploaded_file)

    return {
        "extension": extension,
        "content_type": expected_type,
        "size_bytes": uploaded_file.size,
        "checksum_sha256": _sha256(uploaded_file),
    }


def _read_head(uploaded_file, size: int = 8) -> bytes:
    position = uploaded_file.tell()
    uploaded_file.seek(0)
    head = uploaded_file.read(size)
    uploaded_file.seek(position)
    return head or b""


def _sha256(uploaded_file) -> str:
    digest = hashlib.sha256()
    position = uploaded_file.tell()
    uploaded_file.seek(0)
    for block in uploaded_file.chunks():
        digest.update(block)
    uploaded_file.seek(position)
    return digest.hexdigest()


def _validate_text(uploaded_file) -> None:
    position = uploaded_file.tell()
    uploaded_file.seek(0)
    sample = uploaded_file.read(65536)
    uploaded_file.seek(position)
    if b"\x00" in sample:
        raise serializers.ValidationError("Text files must not contain null bytes.")
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise serializers.ValidationError("Text files must be valid UTF-8.") from exc
