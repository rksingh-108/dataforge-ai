"""Azure OpenAI provider.

Azure uses deployment-scoped URLs and an `api-key` header. `LLM_MODEL` is treated
as the deployment name and `LLM_BASE_URL` as
`https://<resource>.openai.azure.com/openai/deployments/<deployment>`.
"""
from __future__ import annotations

from ai_service.providers.openai_compatible import OpenAICompatibleProvider


class AzureOpenAIProvider(OpenAICompatibleProvider):
    name = "azure_openai"
    api_version = "2024-06-01"

    def _endpoint(self) -> str:
        return f"{self.settings.base_url}/chat/completions?api-version={self.api_version}"

    def _headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json", "api-key": self.settings.api_key}
