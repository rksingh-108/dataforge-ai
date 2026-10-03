# Onboarding — AI / LLM Developer

## Your area

**You own:** `apps/ai-service` — the agent, tools, RAG pipeline, SQL validation and
the LLM/embedding provider adapters.

**You do not own:** the platform database, authorization, or the product UI. The AI
service has **no** database credentials and never writes platform data.

## Set up

```bash
python -m venv .venv-ai && source .venv-ai/bin/activate
pip install -r apps/ai-service/requirements/dev.txt
cd apps/ai-service
INTERNAL_SERVICE_TOKEN=$(grep INTERNAL_SERVICE_TOKEN ../.env | cut -d= -f2) \
INTERNAL_API_BASE_URL=http://localhost:8000 \
python -m flask --app wsgi run --port 8001
```

Tests need no external services:

```bash
make test-ai     # 94 tests, milliseconds
```

Without a real `LLM_API_KEY`, agent runs fail with `provider_error`. That is a real
failure, not a placeholder — the service does not fabricate answers.

## Architecture

```
api/          Flask routes (health, agent, rag, datasources)
providers/    LLMProvider + EmbeddingProvider interfaces and adapters
              base.py (interfaces) · registry.py (config-driven selection)
              openai_compatible · anthropic · azure_openai · ollama
              testing.py (test doubles — never imported in production)
agents/       orchestrator.py (the bounded tool-calling loop) · prompts.py
tools/        registry.py (Tool, ToolContext, dispatch) · data_tools · document_tools
sql/          validator.py (AST rules) · executor.py (read-only execution)
rag/          extract.py · chunking.py · pipeline.py
connections/  postgres.py · mysql.py · base.py (read-only sessions)
security/     internal_auth.py · host_guard.py · injection.py
clients/      api_client.py (calls back into the platform API)
```

## The rules that keep this safe

These are not suggestions. Each has a test suite.

1. **No provider is hard-coded.** Add a vendor by writing one adapter and
   registering it in `providers/registry.py`. `LLM_PROVIDER` selects it. Never
   import a vendor class anywhere else — there is a test asserting the orchestrator
   contains no vendor name.
2. **Never trust the model.** Tool arguments are validated independently. SQL is
   parsed and checked against the datasource allowlist. The database session is
   read-only regardless.
3. **Scope comes from the API, not the model.** `ToolContext.datasource_ids` is
   built by the API from the caller's membership; tools assert against it.
4. **Untrusted content is labelled.** Wrap document text and tool output with
   `wrap_untrusted(...)` before it goes back to the model.
5. **No credentials in prompts.** The model never sees a connection password.
6. **Bound everything:** iterations, timeouts, row caps, join counts, chunk sizes.
7. **No fake AI.** If the provider fails, return an error. Never synthesise an answer.

## Adding a tool

```python
# tools/registry.py — build_default_registry()
registry.register(Tool(
    name="my_tool",
    description="What it does, phrased for the model.",
    parameters={"type": "object", "properties": {...}, "required": [...],
                "additionalProperties": False},
    handler=my_tool_handler,
))
```

Then:
- write the handler in `tools/`, raising `ToolError` for safe, user-visible failures,
- add a test in `tests/test_tools.py` including an out-of-scope argument case,
- document it in [docs/ai/tools.md](../ai/tools.md).

A tool that reaches the network must go through `security/host_guard.py`.

## Testing

- `tests/test_sql_validator.py` — 29 adversarial cases. **Add one whenever you
  change validation.** If you can think of an evasion, write it as a test first.
- `tests/test_agent_orchestrator.py` — uses `ScriptedProvider`; assert on the loop's
  behaviour, not on model output.
- `tests/test_api_routes.py` — auth enforcement and request validation.
- `tests/conftest.py` — builds the app with explicit `Settings`, so tests never
  depend on the environment.

## Good first tasks

- Add an SQL validator case for a bypass you can think of.
- Add a provider adapter for another OpenAI-compatible gateway and a registry test.
- Improve a tool description so the model calls it more reliably.
- Add a test for a route that lacks one.

## Ask about

- Anything touching SQL validation or host guarding → security owner.
- Anything that would give the AI service a new outbound network capability → AI +
  security owners, before you write it.
