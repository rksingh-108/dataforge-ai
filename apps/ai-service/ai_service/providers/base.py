"""Provider abstractions.

The rest of the AI service only ever sees these types, so a new vendor is added
by writing one adapter and registering it — never by editing the agent or tools.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class ProviderError(RuntimeError):
    """Raised when a provider call fails. Carries a safe, non-secret message."""

    def __init__(self, message: str, *, provider: str = "", status: int | None = None):
        super().__init__(message)
        self.provider = provider
        self.status = status


@dataclass
class ToolSpec:
    """A tool exposed to the model, in a provider-neutral shape."""

    name: str
    description: str
    parameters: dict[str, Any]


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    stop_reason: str = ""

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class Message:
    """A conversation message in a provider-neutral shape."""

    role: str  # "system" | "user" | "assistant" | "tool"
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str = ""
    name: str = ""


class LLMProvider(ABC):
    """Chat/generation provider."""

    name: str = "unknown"

    def __init__(self, settings):
        self.settings = settings

    @abstractmethod
    def complete(
        self,
        messages: list[Message],
        *,
        tools: list[ToolSpec] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        """Return the model's next response for a conversation."""

    @property
    def model_name(self) -> str:
        return self.settings.model


class EmbeddingProvider(ABC):
    """Text-to-vector provider."""

    name: str = "unknown"

    def __init__(self, settings):
        self.settings = settings

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts, preserving order."""

    @property
    def dimensions(self) -> int:
        return int(self.settings.dim)

    @property
    def model_name(self) -> str:
        return self.settings.model
