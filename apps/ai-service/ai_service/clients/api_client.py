"""Client for the platform API's internal endpoints.

The AI service holds no platform data itself. Everything it needs for a run —
connection settings, discovered schema, document retrieval — is fetched here,
scoped to the org the API already authorized.
"""
from __future__ import annotations

import logging

import requests
from flask import current_app, g

logger = logging.getLogger("ai_service.api_client")


class PlatformAPIError(RuntimeError):
    """Raised when the platform API cannot serve an internal request."""


class PlatformAPIClient:
    def __init__(self, base_url: str | None = None, token: str | None = None,
                 organization_id: str | None = None, request_id: str | None = None,
                 timeout: int | None = None):
        config = current_app.config if current_app else {}
        self.base_url = (base_url or config.get("API_BASE_URL", "")).rstrip("/")
        self.token = token or config.get("INTERNAL_SERVICE_TOKEN", "")
        self.organization_id = organization_id or getattr(g, "organization_id", None)
        self.request_id = request_id or getattr(g, "request_id", "-")
        self.timeout = timeout or config.get("API_REQUEST_TIMEOUT_SECONDS", 60)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "X-DataForge-Org": str(self.organization_id or ""),
            "X-Request-Id": self.request_id or "-",
            "Accept": "application/json",
        }

    def _get(self, path: str) -> dict:
        url = f"{self.base_url}{path}"
        try:
            response = requests.get(url, headers=self._headers(), timeout=self.timeout)
        except requests.RequestException as exc:
            raise PlatformAPIError("The platform API is unreachable.") from exc
        return self._unwrap(response)

    def _post(self, path: str, payload: dict) -> dict:
        url = f"{self.base_url}{path}"
        try:
            response = requests.post(url, json=payload, headers=self._headers(),
                                     timeout=self.timeout)
        except requests.RequestException as exc:
            raise PlatformAPIError("The platform API is unreachable.") from exc
        return self._unwrap(response)

    @staticmethod
    def _unwrap(response) -> dict:
        if response.status_code >= 400:
            raise PlatformAPIError(f"Platform API returned HTTP {response.status_code}.")
        try:
            return response.json()
        except ValueError as exc:
            raise PlatformAPIError("Platform API returned malformed JSON.") from exc

    # --- Endpoints ---------------------------------------------------------
    def get_connection(self, datasource_id: str) -> dict:
        return self._get(f"/internal/datasources/{datasource_id}/connection")["connection"]

    def get_schema(self, datasource_id: str) -> dict:
        return self._get(f"/internal/datasources/{datasource_id}/schema")

    def search_documents(self, embedding: list[float], *, top_k: int = 5,
                         document_ids: list[str] | None = None) -> list[dict]:
        payload = {"embedding": embedding, "top_k": top_k}
        if document_ids:
            payload["document_ids"] = document_ids
        return self._post("/internal/documents/search", payload)["results"]
