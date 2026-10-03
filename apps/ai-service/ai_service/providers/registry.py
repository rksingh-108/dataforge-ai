"""Provider registry.

Selection is configuration-driven. `LLM_PROVIDER` / `EMBEDDING_PROVIDER` choose an
adapter by name; no call site ever references a concrete vendor class.
"""
from __future__ import annotations

from ai_service.providers.anthropic import AnthropicProvider
from ai_service.providers.azure_openai import AzureOpenAIProvider
from ai_service.providers.base import EmbeddingProvider, LLMProvider, ProviderError
from ai_service.providers.embeddings import (
    OllamaEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
)
from ai_service.providers.ollama import OllamaProvider
from ai_service.providers.openai_compatible import OpenAICompatibleProvider

LLM_PROVIDERS: dict[str, type[LLMProvider]] = {
    "openai": OpenAICompatibleProvider,
    "openai_compatible": OpenAICompatibleProvider,
    "azure_openai": AzureOpenAIProvider,
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
}

EMBEDDING_PROVIDERS: dict[str, type[EmbeddingProvider]] = {
    "openai": OpenAICompatibleEmbeddingProvider,
    "openai_compatible": OpenAICompatibleEmbeddingProvider,
    "ollama": OllamaEmbeddingProvider,
}


def build_llm_provider(settings) -> LLMProvider:
    provider_cls = LLM_PROVIDERS.get(settings.provider)
    if provider_cls is None:
        raise ProviderError(
            f"Unsupported LLM_PROVIDER '{settings.provider}'. "
            f"Known providers: {', '.join(sorted(LLM_PROVIDERS))}."
        )
    return provider_cls(settings)


def build_embedding_provider(settings) -> EmbeddingProvider:
    provider_cls = EMBEDDING_PROVIDERS.get(settings.provider)
    if provider_cls is None:
        raise ProviderError(
            f"Unsupported EMBEDDING_PROVIDER '{settings.provider}'. "
            f"Known providers: {', '.join(sorted(EMBEDDING_PROVIDERS))}."
        )
    return provider_cls(settings)
