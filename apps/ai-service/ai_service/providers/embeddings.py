"""Embedding providers.

Kept separate from chat providers because the two are frequently sourced from
different vendors (e.g. Azure for chat, OpenAI for embeddings).
"""
from __future__ import annotations

import math

import requests

from ai_service.providers.base import EmbeddingProvider, ProviderError


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    name = "openai_compatible"

    def _endpoint(self) -> str:
        return f"{self.settings.base_url}/embeddings"

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = requests.post(
                self._endpoint(),
                json={"model": self.settings.model, "input": texts},
                headers={
                    "Content-Type": "application/json",
                    **({"Authorization": f"Bearer {self.settings.api_key}"}
                       if self.settings.api_key else {}),
                },
                timeout=120,
            )
        except requests.RequestException as exc:
            raise ProviderError("Embedding provider is unreachable.", provider=self.name) from exc

        if response.status_code >= 400:
            raise ProviderError(
                f"Embedding provider returned HTTP {response.status_code}.",
                provider=self.name,
                status=response.status_code,
            )

        data = response.json().get("data", [])
        vectors = [_normalise(item.get("embedding", [])) for item in data]
        if len(vectors) != len(texts):
            raise ProviderError("Embedding provider returned the wrong number of vectors.",
                                provider=self.name)
        for vector in vectors:
            if len(vector) != self.dimensions:
                raise ProviderError(
                    f"Embedding dimension mismatch: got {len(vector)}, expected {self.dimensions}.",
                    provider=self.name,
                )
        return vectors


class OllamaEmbeddingProvider(EmbeddingProvider):
    name = "ollama"

    def _endpoint(self) -> str:
        return f"{self.settings.base_url}/api/embeddings"

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            try:
                response = requests.post(
                    self._endpoint(),
                    json={"model": self.settings.model, "prompt": text},
                    timeout=120,
                )
            except requests.RequestException as exc:
                raise ProviderError("Embedding provider is unreachable.",
                                    provider=self.name) from exc
            if response.status_code >= 400:
                raise ProviderError(
                    f"Embedding provider returned HTTP {response.status_code}.", provider=self.name
                )
            vectors.append(_normalise(response.json().get("embedding", [])))
        return vectors


def _normalise(vector: list[float]) -> list[float]:
    """L2-normalise so cosine distance is well behaved and magnitudes are stable."""
    values = [float(v) for v in vector]
    norm = math.sqrt(sum(v * v for v in values))
    if norm == 0:
        return values
    return [v / norm for v in values]
