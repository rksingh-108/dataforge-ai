# AI Service

The AI service (`apps/ai-service`) is a Flask application that owns agent
orchestration, tools, RAG and the provider adapters. It is deliberately separated
from the Django API: it makes outbound calls to LLM vendors and customer databases,
it is the only component that does, and it holds no platform data of its own.

## Why a separate service

| Reason | Detail |
| ------ | ------ |
| Different trust level | It is an *egress broker*: the only component allowed to reach customer databases and LLM vendors |
| Different runtime profile | Long provider calls and document parsing versus short API requests |
| Independent scaling | LLM latency should not consume API workers |
| Boundary hygiene | AI orchestration cannot leak into domain/business logic because it is a different deployable |

What it does **not** get: platform database credentials, user passwords, or the
ability to decide authorization.

## Module map

```
ai_service/
├── app.py                Flask factory; builds providers once, stores on extensions
├── config.py             Environment-driven Settings (frozen dataclasses)
├── api/                  Routes: health, agent, rag, datasources
├── providers/            LLMProvider / EmbeddingProvider interfaces + adapters
│   ├── base.py           Interfaces, Message, ToolSpec, LLMResponse
│   ├── registry.py       Configuration-driven selection
│   ├── openai_compatible.py · anthropic.py · azure_openai.py · ollama.py
│   └── testing.py        Test doubles — never imported in production
├── agents/               orchestrator.py (bounded loop), prompts.py
├── tools/                registry.py (Tool/ToolContext/dispatch), data_tools, document_tools
├── sql/                  validator.py (AST rules), executor.py (read-only execution)
├── rag/                  extract.py, chunking.py, pipeline.py
├── connections/          postgres.py, mysql.py, base.py (read-only sessions)
├── security/             internal_auth.py, host_guard.py, injection.py
└── clients/api_client.py Calls the platform API's internal endpoints
```

## Provider abstraction

```python
class LLMProvider(ABC):
    @abstractmethod
    def complete(self, messages: list[Message], *, tools=None,
                 max_tokens=None, temperature=None) -> LLMResponse: ...

class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...
```

Selection is entirely configuration:

| Variable | Values |
| -------- | ------ |
| `LLM_PROVIDER` | `openai`, `openai_compatible`, `azure_openai`, `anthropic`, `ollama` |
| `EMBEDDING_PROVIDER` | `openai`, `openai_compatible`, `ollama` |

A test asserts the orchestrator source contains no vendor name, so the abstraction
cannot rot. **Groq is deliberately not supported.**

Adding a provider: implement the interface, register it in `registry.py`, add a
registry test. No call site changes.

## The agent loop

`agents/orchestrator.py`:

1. System prompt (`agents/prompts.py`) plus a user message describing the approved
   data sources.
2. `provider.complete(messages, tools=registry.specs())`.
3. If the response has tool calls: execute each through the registry, append the
   result wrapped as untrusted data, loop.
4. If the response has no tool calls: that is the answer.
5. Bounded by `AGENT_MAX_ITERATIONS`; on exhaustion it asks once more for a final
   answer without tools and marks `budget_exhausted`.

Every step is recorded as a trace entry with a **redacted** argument summary (SQL
preview, lengths) and an output summary (row counts, match counts, flags).

## Tools

See [tools.md](tools.md).

## RAG

```
bytes ─▶ extract (pdf|docx|txt) ─▶ chunk (paragraph-aware, overlapping)
      ─▶ embed (configured provider) ─▶ return chunks
```

The service returns chunks; the **API persists them** into pgvector, because the
API is the only writer to the platform database. Retrieval is also performed by the
API (`/internal/documents/search`), so the AI service never touches the vector store.

## Safety posture

Read [security/threat-model/sql-injection.md](../../security/threat-model/sql-injection.md)
and [prompt-injection.md](../../security/threat-model/prompt-injection.md). The
short version:

- The model is untrusted output; tools validate independently.
- SQL is parsed and checked against a discovered allowlist; the session is read-only.
- Scope comes from the API, not from model output.
- Untrusted content is delimited and scanned.
- Everything is bounded: iterations, timeouts, rows, joins, chunk sizes.

## Configuration

All variables are documented in `.env.example`. The essentials:

| Variable | Purpose |
| -------- | ------- |
| `INTERNAL_SERVICE_TOKEN` | Shared with the API; must match |
| `INTERNAL_API_BASE_URL` | Where to reach the platform API |
| `LLM_*` | Provider, model, key, base URL, limits |
| `EMBEDDING_*` | Embedding provider, model, dimension |
| `RAG_*` | Chunk size, overlap, top-k |
| `SQL_*` | Statement timeout, max rows, max joins |
| `AGENT_MAX_ITERATIONS` | Loop bound |

## Testing

```bash
make test-ai     # 94 tests, no external services, sub-second
```

Provider calls are replaced by `providers/testing.py` doubles in tests only. The
SQL validator, host guard, injection scanner, chunker, tool scoping and agent loop
are all tested for real.
