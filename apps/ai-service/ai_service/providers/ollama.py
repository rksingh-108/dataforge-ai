"""Ollama provider for fully local models (no external network egress)."""
from __future__ import annotations

import requests

from ai_service.providers.base import (
    LLMProvider,
    LLMResponse,
    Message,
    ProviderError,
    ToolCall,
    ToolSpec,
)


class OllamaProvider(LLMProvider):
    name = "ollama"

    def _endpoint(self) -> str:
        return f"{self.settings.base_url}/api/chat"

    def complete(
        self,
        messages: list[Message],
        *,
        tools: list[ToolSpec] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        payload: dict = {
            "model": self.settings.model,
            "stream": False,
            "options": {
                "temperature": self.settings.temperature if temperature is None else temperature,
                "num_predict": max_tokens or self.settings.max_tokens,
            },
            "messages": [self._encode_message(m) for m in messages],
        }
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]

        try:
            response = requests.post(self._endpoint(), json=payload,
                                     timeout=self.settings.timeout_seconds)
        except requests.RequestException as exc:
            raise ProviderError("LLM provider is unreachable.", provider=self.name) from exc
        if response.status_code >= 400:
            raise ProviderError(f"LLM provider returned HTTP {response.status_code}.",
                                provider=self.name, status=response.status_code)

        body = response.json()
        message = body.get("message", {}) or {}
        tool_calls = [
            ToolCall(id=call.get("id") or f"call_{i}", name=call.get("function", {}).get("name", ""),
                     arguments=_as_dict(call.get("function", {}).get("arguments")))
            for i, call in enumerate(message.get("tool_calls") or [])
        ]
        return LLMResponse(
            content=message.get("content") or "",
            tool_calls=tool_calls,
            input_tokens=int(body.get("prompt_eval_count", 0) or 0),
            output_tokens=int(body.get("eval_count", 0) or 0),
            model=body.get("model", self.settings.model),
            stop_reason=body.get("done_reason", "") or "",
        )

    @staticmethod
    def _encode_message(message: Message) -> dict:
        if message.role == "tool":
            return {"role": "tool", "content": message.content}
        if message.role == "assistant" and message.tool_calls:
            return {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {"function": {"name": c.name, "arguments": c.arguments}} for c in message.tool_calls
                ],
            }
        return {"role": message.role, "content": message.content}


def _as_dict(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    return {"value": raw} if raw else {}
