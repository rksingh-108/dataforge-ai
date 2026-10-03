"""HTTP client for the dedicated AI service.

This is the *only* place in the API that talks to the AI service. It centralizes
authentication (service token), timeouts, correlation ids and error translation
so callers get domain errors instead of raw HTTP failures.

The AI service is never called without a tenant scope header; that scope is
attached from the authenticated request, not from client input.
"""
from __future__ import annotations

import logging
import uuid

import requests
from django.conf import settings

from apps.common.exceptions import UpstreamServiceError

logger = logging.getLogger("apps.ai_bridge")


class AIServiceClient:
    def __init__(self, base_url: str | None = None, token: str | None = None,
                 timeout: int | None = None):
        self.base_url = (base_url or settings.AI_SERVICE_URL).rstrip("/")
        self.token = token if token is not None else settings.INTERNAL_SERVICE_TOKEN
        self.timeout = timeout or settings.INTERNAL_REQUEST_TIMEOUT_SECONDS

    def _headers(self, *, organization_id: uuid.UUID | None, user_id: uuid.UUID | None,
                 request_id: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Request-Id": request_id or str(uuid.uuid4()),
        }
        if organization_id:
            headers["X-DataForge-Org"] = str(organization_id)
        if user_id:
            headers["X-DataForge-User"] = str(user_id)
        return headers

    def post(self, path: str, payload: dict, *, organization_id=None, user_id=None,
             request_id: str | None = None, timeout: int | None = None) -> dict:
        url = f"{self.base_url}{path}"
        try:
            # `timeout` is always supplied: either the caller's override or the
            # configured INTERNAL_REQUEST_TIMEOUT_SECONDS. bandit cannot see
            # through the `or` expression, hence the targeted suppression.
            response = requests.post(  # nosec B113
                url,
                json=payload,
                headers=self._headers(organization_id=organization_id, user_id=user_id,
                                      request_id=request_id),
                timeout=timeout or self.timeout,
            )
        except requests.RequestException as exc:
            logger.error("AI service unreachable at %s: %s", url, exc)
            raise UpstreamServiceError("The AI service is unavailable.") from exc

        if response.status_code >= 400:
            logger.warning("AI service returned %s for %s: %s",
                           response.status_code, path, response.text[:500])
            raise UpstreamServiceError(
                detail={"upstream_status": response.status_code,
                        "upstream_message": _safe_message(response)}
            )
        try:
            return response.json()
        except ValueError as exc:
            raise UpstreamServiceError("The AI service returned malformed JSON.") from exc

    def get(self, path: str, *, timeout: int | None = None) -> dict:
        url = f"{self.base_url}{path}"
        try:
            response = requests.get(url, timeout=timeout or self.timeout)  # nosec B113
        except requests.RequestException as exc:
            raise UpstreamServiceError("The AI service is unavailable.") from exc
        if response.status_code >= 400:
            raise UpstreamServiceError(detail={"upstream_status": response.status_code})
        return response.json()

    # --- Convenience wrappers ----------------------------------------------
    def test_connection(self, config: dict) -> dict:
        return self.post("/v1/datasources/test", {"connection": config}, timeout=30)

    def introspect(self, config: dict) -> dict:
        return self.post("/v1/datasources/introspect", {"connection": config}, timeout=60)

    def run_agent(self, payload: dict, *, organization_id, user_id, request_id=None) -> dict:
        return self.post(
            "/v1/agent/run",
            payload,
            organization_id=organization_id,
            user_id=user_id,
            request_id=request_id,
        )

    def process_document(self, payload: dict) -> dict:
        return self.post("/v1/rag/process", payload, timeout=300)

    def embed_query(self, text: str) -> dict:
        return self.post("/v1/embeddings/query", {"text": text})


def _safe_message(response) -> str:
    """Extract an error message without echoing full upstream payloads."""
    try:
        body = response.json()
        if isinstance(body, dict):
            return str(body.get("error") or body.get("message") or "")[:300]
    except ValueError:
        pass
    return response.text[:300]
