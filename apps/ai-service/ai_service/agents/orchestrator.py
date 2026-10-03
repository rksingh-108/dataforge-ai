"""The Data Analyst agent loop.

Flow:
    question -> [LLM chooses a tool -> tool runs -> result appended] (repeat)
             -> final answer

Safety properties enforced here (not by trusting the model):
- every tool call is dispatched through the registry, which re-checks scope;
- SQL is validated by AST rules inside `run_sql` regardless of the prompt;
- untrusted tool output is wrapped before being handed back to the model;
- the loop is bounded by `agent_max_iterations`.
"""
from __future__ import annotations

import json
import logging

from ai_service.agents.prompts import ANSWER_ONLY_INSTRUCTION, SYSTEM_PROMPT
from ai_service.providers.base import LLMProvider, Message, ProviderError
from ai_service.security.injection import scan_for_injection, summarise_findings, wrap_untrusted
from ai_service.tools.registry import ToolContext, ToolError, ToolRegistry

logger = logging.getLogger("ai_service.agent")

MAX_TOOL_RESULT_CHARS = 12000


class AgentRunError(RuntimeError):
    def __init__(self, message: str, *, code: str = "agent_error"):
        super().__init__(message)
        self.code = code


def run_agent(
    *,
    question: str,
    provider: LLMProvider,
    registry: ToolRegistry,
    context: ToolContext,
    max_iterations: int = 6,
) -> dict:
    """Run the agent and return the answer plus a step-by-step trace."""
    if not question or not question.strip():
        raise AgentRunError("A question is required.", code="empty_question")

    messages: list[Message] = [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content=_build_user_message(question, context)),
    ]

    steps: list[dict] = []
    total_input = total_output = 0
    model_name = ""
    step_index = 0

    for _iteration in range(max_iterations):
        try:
            response = provider.complete(messages, tools=registry.specs())
        except ProviderError as exc:
            raise AgentRunError(str(exc), code="provider_error") from exc

        total_input += response.input_tokens
        total_output += response.output_tokens
        model_name = response.model or model_name

        if not response.tool_calls:
            answer = (response.content or "").strip()
            return {
                "answer": answer or "I could not find enough information to answer that.",
                "steps": steps,
                "provider": provider.name,
                "model": model_name or provider.model_name,
                "total_tokens": total_input + total_output,
            }

        messages.append(
            Message(role="assistant", content=response.content, tool_calls=response.tool_calls)
        )

        for call in response.tool_calls:
            started_step = step_index
            step_index += 1
            step, tool_message = _run_tool(
                call=call, registry=registry, context=context, index=started_step
            )
            steps.append(step)
            messages.append(tool_message)

    # Iteration budget exhausted: ask once more for a final answer without tools.
    messages.append(Message(role="user", content=ANSWER_ONLY_INSTRUCTION))
    try:
        final = provider.complete(messages, tools=None)
    except ProviderError as exc:
        raise AgentRunError(str(exc), code="provider_error") from exc

    total_input += final.input_tokens
    total_output += final.output_tokens
    return {
        "answer": (final.content or "").strip()
        or "I could not complete the analysis within the allowed number of steps.",
        "steps": steps,
        "provider": provider.name,
        "model": final.model or model_name or provider.model_name,
        "total_tokens": total_input + total_output,
        "budget_exhausted": True,
    }


def _run_tool(*, call, registry: ToolRegistry, context: ToolContext, index: int) -> tuple[dict, Message]:
    """Execute one tool call and build both the trace step and the tool message."""
    arguments = call.arguments if isinstance(call.arguments, dict) else {}
    step = {
        "index": index,
        "tool": call.name,
        "title": _title_for(call.name, arguments),
        "status": "succeeded",
        "input_summary": _summarise_arguments(call.name, arguments),
        "output_summary": {},
        "error": "",
    }

    try:
        result = registry.execute(call.name, arguments, context)
    except ToolError as exc:
        step["status"] = "failed"
        step["error"] = str(exc)[:500]
        step["output_summary"] = {"error": str(exc)[:200]}
        return step, Message(
            role="tool", tool_call_id=call.id, name=call.name,
            content=wrap_untrusted(f"Tool error: {exc}", source=call.name),
        )

    step["output_summary"] = _summarise_result(call.name, result)
    findings = _scan_result(result)
    if findings["flagged"]:
        step["output_summary"]["content_flagged"] = findings["categories"]

    serialised = json.dumps(result, default=str)[:MAX_TOOL_RESULT_CHARS]
    return step, Message(
        role="tool",
        tool_call_id=call.id,
        name=call.name,
        content=wrap_untrusted(serialised, source=call.name),
    )


def _build_user_message(question: str, context: ToolContext) -> str:
    lines = [f"Question: {question.strip()}"]
    if context.datasource_ids:
        described = ", ".join(
            f"{did} ({context.datasource_names.get(did, 'data source')})"
            for did in context.datasource_ids
        )
        lines.append(f"Approved data sources: {described}")
    else:
        lines.append("No data sources are approved for this request.")
    if not context.document_ids and context.embedder is not None:
        lines.append("Uploaded documents are available for search.")
    return "\n".join(lines)


def _title_for(tool: str, arguments: dict) -> str:
    if tool == "run_sql":
        purpose = str(arguments.get("purpose", "")).strip()
        return f"Run SQL query{': ' + purpose[:120] if purpose else ''}"
    if tool == "list_tables":
        return f"Inspect schema of {arguments.get('datasource_id', 'data source')}"
    if tool == "search_documents":
        return f"Search documents for '{str(arguments.get('query', ''))[:80]}'"
    return f"Call tool {tool}"


def _summarise_arguments(tool: str, arguments: dict) -> dict:
    """A trace-safe view of the arguments — never raw credentials or full SQL blobs."""
    if tool == "run_sql":
        sql = str(arguments.get("sql", ""))
        return {
            "datasource_id": str(arguments.get("datasource_id", "")),
            "sql_preview": sql[:300] + ("…" if len(sql) > 300 else ""),
            "sql_length": len(sql),
        }
    if tool == "search_documents":
        return {"query": str(arguments.get("query", ""))[:200],
                "top_k": arguments.get("top_k")}
    return {k: (str(v)[:200] if not isinstance(v, (int, float, bool)) else v)
            for k, v in arguments.items()}


def _summarise_result(tool: str, result: dict) -> dict:
    if tool == "run_sql":
        return {
            "ok": result.get("ok", False),
            "row_count": result.get("row_count", 0),
            "truncated": result.get("truncated", False),
            "tables": result.get("tables", []),
            "rejected": result.get("rejected", False),
            "reason": result.get("reason", "")[:200],
            "duration_ms": result.get("duration_ms", 0),
        }
    if tool == "list_tables":
        return {"table_count": result.get("table_count", 0)}
    if tool == "search_documents":
        return {"match_count": result.get("match_count", 0)}
    return {"keys": sorted(result.keys())[:20]}


def _scan_result(result: dict) -> dict:
    findings = []
    for value in result.get("passages", []) or []:
        findings.extend(scan_for_injection(str(value.get("content", ""))))
    return summarise_findings(findings)
