"""Test doubles for the provider interfaces.

These exist ONLY for the automated test suite. They are not selectable through
`LLM_PROVIDER`/`EMBEDDING_PROVIDER` (the registry does not import this module), so
they cannot be switched on in a deployed environment. If you find yourself
importing this outside `tests/`, stop and reconsider.
"""
from __future__ import annotations

import hashlib

from ai_service.providers.base import EmbeddingProvider, LLMProvider, LLMResponse, ToolCall


class ScriptedProvider(LLMProvider):
    """Returns a pre-programmed sequence of responses, one per call."""

    name = "scripted"

    def __init__(self, responses: list[LLMResponse] | None = None):
        # Deliberately does not call super().__init__: there is no real settings
        # object behind a scripted provider.
        self._responses = list(responses or [])
        self.calls: list[dict] = []

    @property
    def model_name(self) -> str:
        return "test-model"

    def complete(self, messages, *, tools=None, max_tokens=None, temperature=None) -> LLMResponse:
        self.calls.append({"messages": list(messages), "tools": tools})
        if self._responses:
            return self._responses.pop(0)
        return LLMResponse(content="I have no further information.")


class DeterministicEmbeddingProvider(EmbeddingProvider):
    """Produces stable pseudo-embeddings derived from the text hash.

    Identical text always yields an identical vector, and different text yields a
    different vector, which is all the retrieval tests need.
    """

    name = "deterministic"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def _vector(self, text: str) -> list[float]:
        dim = self.dimensions
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        raw = [(digest[i % len(digest)] / 255.0) - 0.5 for i in range(dim)]
        norm = sum(v * v for v in raw) ** 0.5 or 1.0
        return [v / norm for v in raw]


def tool_call(name: str, arguments: dict, call_id: str = "call_1") -> LLMResponse:
    """Convenience builder for a response that requests a tool."""
    return LLMResponse(tool_calls=[ToolCall(id=call_id, name=name, arguments=arguments)])
