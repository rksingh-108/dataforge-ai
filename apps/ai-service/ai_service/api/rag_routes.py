"""Document processing and embedding endpoints."""
from __future__ import annotations

import base64
import binascii
import logging

from flask import Blueprint, current_app, jsonify, request

from ai_service.api import error_response
from ai_service.providers.base import ProviderError
from ai_service.rag.extract import ExtractionError
from ai_service.rag.pipeline import process_document
from ai_service.security.internal_auth import require_internal_token

bp = Blueprint("rag", __name__, url_prefix="/v1")
logger = logging.getLogger("ai_service.api.rag")


def _embedder():
    return current_app.extensions["embedding_provider"]


@bp.post("/rag/process")
@require_internal_token
def rag_process():
    payload = request.get_json(silent=True) or {}
    encoded = payload.get("content_base64")
    if not encoded:
        return error_response("bad_request", "`content_base64` is required.")
    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return error_response("bad_request", "`content_base64` is not valid base64.")

    try:
        result = process_document(
            data,
            filename=str(payload.get("filename", "")),
            content_type=str(payload.get("content_type", "")),
            embedder=_embedder(),
            chunk_size=current_app.config["RAG_CHUNK_SIZE"],
            overlap=current_app.config["RAG_CHUNK_OVERLAP"],
        )
    except ExtractionError as exc:
        return error_response("extraction_failed", str(exc), 422)
    except ProviderError as exc:
        return error_response("embedding_failed", str(exc), 502)
    except ValueError as exc:
        return error_response("processing_failed", str(exc), 422)

    return jsonify(result)


@bp.post("/embeddings/query")
@require_internal_token
def embed_query():
    payload = request.get_json(silent=True) or {}
    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        return error_response("bad_request", "`text` is required.")
    try:
        vectors = _embedder().embed([text])
    except ProviderError as exc:
        return error_response("embedding_failed", str(exc), 502)
    return jsonify({"embedding": vectors[0], "dimensions": len(vectors[0])})
