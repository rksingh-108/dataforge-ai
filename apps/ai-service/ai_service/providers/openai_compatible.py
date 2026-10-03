"""OpenAI-compatible chat provider.

Works with OpenAI, most hosted gateways, and local servers that implement the
`/chat/completions` contract (vLLM, LM Studio, Ollama's OpenAI shim, ...).
"""
from __future__ import annotations

import json

import requests

from ai_service.providers.base import (
    LLMProvider,
    LLMResponse,
    Message,
    ProviderError,
    ToolCall,
    ToolSpec,
)


class OpenAICompatibleProvider(LLMProvider):
    name = "openai_compatible"

    def _endpoint(self) -> str:
        return f"{self.settings.base_url}/chat/completions"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"
        return headers

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
            "messages": [self._encode_message(m) for m in messages],
            "max_tokens": max_tokens or self.settings.max_tokens,
            "temperature": self.settings.temperature if temperature is None else temperature,
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
            payload["tool_choice"] = "auto"

        try:
            response = requests.post(
                self._endpoint(),
                json=payload,
                headers=self._headers(),
                timeout=self.settings.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise ProviderError("LLM provider is unreachable.", provider=self.name) from exc

        if response.status_code >= 400:
            raise ProviderError(
                f"LLM provider returned HTTP {response.status_code}.",
                provider=self.name,
                status=response.status_code,
            )

        return self._decode(response.json())

    @staticmethod
    def _encode_message(message: Message) -> dict:
        if message.role == "tool":
            return {"role": "tool", "tool_call_id": message.tool_call_id, "content": message.content}
        if message.role == "assistant" and message.tool_calls:
            return {
                "role": "assistant",
                "content": message.content or None,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
                    }
                    for call in message.tool_calls
                ],
            }
        return {"role": message.role, "content": message.content}

    def _decode(self, body: dict) -> LLMResponse:
        try:
            choice = body["choices"][0]
        except (KeyError, IndexError) as exc:
            raise ProviderError("LLM provider returned an unexpected payload.",
                                provider=self.name) from exc

        message = choice.get("message", {})
        tool_calls = []
        for call in message.get("tool_calls") or []:
            function = call.get("function", {})
            tool_calls.append(
                ToolCall(
                    id=call.get("id", ""),
                    name=function.get("name", ""),
                    arguments=_parse_arguments(function.get("arguments")),
                )
            )
        usage = body.get("usage", {}) or {}
        return LLMResponse(
            content=message.get("content") or "",
            tool_calls=tool_calls,
            input_tokens=int(usage.get("prompt_tokens", 0) or 0),
            output_tokens=int(usage.get("completion_tokens", 0) or 0),
            model=body.get("model", self.settings.model),
            stop_reason=choice.get("finish_reason", "") or "",
        )


def _parse_arguments(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except (ValueError, TypeError):
        return {"_raw": str(raw)[:2000]}
