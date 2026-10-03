"""Provider registry tests: selection is configuration-driven and fails fast."""
from __future__ import annotations

import pytest

from ai_service.config import EmbeddingSettings, LLMSettings
from ai_service.providers.anthropic import AnthropicProvider
from ai_service.providers.azure_openai import AzureOpenAIProvider
from ai_service.providers.base import ProviderError
from ai_service.providers.embeddings import (
    OllamaEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
)
from ai_service.providers.ollama import OllamaProvider
from ai_service.providers.openai_compatible import OpenAICompatibleProvider
from ai_service.providers.registry import build_embedding_provider, build_llm_provider


def _llm(provider: str) -> LLMSettings:
    return LLMSettings(provider=provider, model="m", api_key="k",
                       base_url="https://example.invalid/v1", timeout_seconds=1,
                       max_tokens=10, temperature=0.0)


def _embed(provider: str) -> EmbeddingSettings:
    return EmbeddingSettings(provider=provider, model="m", dim=8, api_key="k",
                             base_url="https://example.invalid/v1")


@pytest.mark.parametrize(
    "name,expected",
    [
        ("openai", OpenAICompatibleProvider),
        ("openai_compatible", OpenAICompatibleProvider),
        ("azure_openai", AzureOpenAIProvider),
        ("anthropic", AnthropicProvider),
        ("ollama", OllamaProvider),
    ],
)
def test_llm_provider_is_selected_by_name(name, expected):
    assert isinstance(build_llm_provider(_llm(name)), expected)


@pytest.mark.parametrize(
    "name,expected",
    [
        ("openai", OpenAICompatibleEmbeddingProvider),
        ("openai_compatible", OpenAICompatibleEmbeddingProvider),
        ("ollama", OllamaEmbeddingProvider),
    ],
)
def test_embedding_provider_is_selected_by_name(name, expected):
    assert isinstance(build_embedding_provider(_embed(name)), expected)


def test_unknown_llm_provider_fails_fast():
    with pytest.raises(ProviderError) as exc:
        build_llm_provider(_llm("groq"))
    assert "groq" in str(exc.value)


def test_unknown_embedding_provider_fails_fast():
    with pytest.raises(ProviderError):
        build_embedding_provider(_embed("definitely-not-real"))


def test_no_vendor_is_hardcoded_in_the_agent_module():
    """The orchestration layer must depend only on the provider interface."""
    import inspect

    from ai_service.agents import orchestrator

    source = inspect.getsource(orchestrator)
    for vendor in ("openai", "anthropic", "azure", "ollama", "groq"):
        assert vendor not in source.lower()
