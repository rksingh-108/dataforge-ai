"""Anthropic Messages API provider."""
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

API_VERSION = "2023-06-01"


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def _endpoint(self) -> str:
        return f"{self.settings.base_url}/messages"

    def complete(
        self,
        messages: list[Message],
        *,
        tools: list[ToolSpec] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        system, conversation = self._split_system(messages)
        payload: dict = {
            "model": self.settings.model,
            "max_tokens": max_tokens or self.settings.max_tokens,
            "temperature": self.settings.temperature if temperature is None else temperature,
            "messages": conversation,
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = [
                {"name": t.name, "description": t.description, "input_schema": t.parameters}
                for t in tools
            ]

        try:
            response = requests.post(
                self._endpoint(),
                json=payload,
                headers={
                    "x-api-key": self.settings.api_key,
                    "anthropic-version": API_VERSION,
                    "content-type": "application/json",
                },
                timeout=self.settings.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise ProviderError("LLM provider is unreachable.", provider=self.name) from exc

        if response.status_code >= 400:
            raise ProviderError(f"LLM provider returned HTTP {response.status_code}.",
                                provider=self.name, status=response.status_code)

        return self._decode(response.json())

    @staticmethod
    def _split_system(messages: list[Message]) -> tuple[str, list[dict]]:
        system_parts, conversation = [], []
        for message in messages:
            if message.role == "system":
                system_parts.append(message.content)
            elif message.role == "tool":
                conversation.append(
                    {
                        "role": "user",
                        "content": [
                            {"type": "tool_result", "tool_use_id": message.tool_call_id,
                             "content": message.content}
                        ],
                    }
                )
            elif message.role == "assistant" and message.tool_calls:
                conversation.append(
                    {
                        "role": "assistant",
                        "content": [
                            {"type": "tool_use", "id": call.id, "name": call.name,
                             "input": call.arguments}
                            for call in message.tool_calls
                        ],
                    }
                )
            else:
                conversation.append({"role": message.role, "content": message.content})
        return "\n\n".join(system_parts), conversation

    def _decode(self, body: dict) -> LLMResponse:
        content_parts, tool_calls = [], []
        for block in body.get("content", []):
            if block.get("type") == "text":
                content_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.get("id", ""), name=block.get("name", ""),
                             arguments=block.get("input", {}) or {})
                )
        usage = body.get("usage", {}) or {}
        return LLMResponse(
            content="\n".join(content_parts).strip(),
            tool_calls=tool_calls,
            input_tokens=int(usage.get("input_tokens", 0) or 0),
            output_tokens=int(usage.get("output_tokens", 0) or 0),
            model=body.get("model", self.settings.model),
            stop_reason=body.get("stop_reason", "") or "",
        )
