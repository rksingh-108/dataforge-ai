"""Configuration for the AI service.

Every value is read from the environment. The LLM provider and embedding provider
are selected purely by configuration (``LLM_PROVIDER`` / ``EMBEDDING_PROVIDER``),
so switching vendors never requires a code change.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / ".env")


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(_env(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    model: str
    api_key: str
    base_url: str
    timeout_seconds: int
    max_tokens: int
    temperature: float


@dataclass(frozen=True)
class EmbeddingSettings:
    provider: str
    model: str
    dim: int
    api_key: str
    base_url: str


@dataclass(frozen=True)
class Settings:
    environment: str
    internal_service_token: str
    api_base_url: str
    llm: LLMSettings
    embeddings: EmbeddingSettings
    rag_chunk_size: int
    rag_chunk_overlap: int
    rag_top_k: int
    sql_statement_timeout_ms: int
    sql_max_rows: int
    sql_max_joins: int
    sql_connect_timeout_seconds: int
    agent_max_iterations: int
    allow_private_networks: bool
    log_level: str = "INFO"
    extra: dict = field(default_factory=dict)


def _to_bool(value: str, default: bool = False) -> bool:
    if not value:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        environment=_env("DJANGO_ENV", "development"),
        internal_service_token=_env("INTERNAL_SERVICE_TOKEN"),
        api_base_url=_env("AI_SERVICE__API_BASE_URL", "").rstrip("/")
        or _api_base_url_from_env(),
        llm=LLMSettings(
            provider=_env("LLM_PROVIDER", "openai_compatible").lower(),
            model=_env("LLM_MODEL", "gpt-4o-mini"),
            api_key=_env("LLM_API_KEY"),
            base_url=_env("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            timeout_seconds=_int("LLM_REQUEST_TIMEOUT_SECONDS", 60),
            max_tokens=_int("LLM_MAX_TOKENS", 1024),
            temperature=_float("LLM_TEMPERATURE", 0.0),
        ),
        embeddings=EmbeddingSettings(
            provider=_env("EMBEDDING_PROVIDER", "openai_compatible").lower(),
            model=_env("EMBEDDING_MODEL", "text-embedding-3-small"),
            dim=_int("EMBEDDING_DIM", 1536),
            api_key=_env("EMBEDDING_API_KEY") or _env("LLM_API_KEY"),
            base_url=_env("EMBEDDING_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        ),
        rag_chunk_size=_int("RAG_CHUNK_SIZE", 1000),
        rag_chunk_overlap=_int("RAG_CHUNK_OVERLAP", 150),
        rag_top_k=_int("RAG_TOP_K", 5),
        sql_statement_timeout_ms=_int("SQL_STATEMENT_TIMEOUT_MS", 5000),
        sql_max_rows=_int("SQL_MAX_ROWS", 500),
        sql_max_joins=_int("SQL_MAX_JOINS", 6),
        sql_connect_timeout_seconds=_int("SQL_CONNECT_TIMEOUT_SECONDS", 5),
        agent_max_iterations=_int("AGENT_MAX_ITERATIONS", 6),
        allow_private_networks=_to_bool(_env("DATASOURCE_ALLOW_PRIVATE_NETWORKS", "")),
        log_level=_env("LOG_LEVEL", "INFO"),
    )


def _api_base_url_from_env() -> str:
    """The AI service reaches the platform API at the internal host.

    In Compose this is the `api` service; locally it is localhost. We prefer an
    explicit override but fall back to the standard internal address.
    """
    return _env("INTERNAL_API_BASE_URL", "http://api:8000").rstrip("/")
