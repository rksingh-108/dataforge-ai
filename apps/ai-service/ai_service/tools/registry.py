"""Tool registry.

Tools are the only way the agent can affect the world. Each tool declares a JSON
schema (exposed to the model) and a handler (called by us). Handlers receive a
`ToolContext` carrying the *already-authorized* organization scope, never raw
request data.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ai_service.providers.base import ToolSpec

logger = logging.getLogger("ai_service.tools")


class ToolError(Exception):
    """A tool failed in a way that is safe to report back to the model."""


@dataclass
class ToolContext:
    """Everything a tool needs, already scoped and authorized."""

    organization_id: str
    datasource_ids: list[str] = field(default_factory=list)
    datasource_names: dict[str, str] = field(default_factory=dict)
    document_ids: list[str] = field(default_factory=list)
    embedder: Any = None
    api_client: Any = None
    settings: Any = None
    allowed_tables: dict[str, set[str]] = field(default_factory=dict)


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    handler: Callable[..., dict]
    required_permission: str = ""

    def spec(self) -> ToolSpec:
        return ToolSpec(name=self.name, description=self.description, parameters=self.parameters)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def specs(self) -> list[ToolSpec]:
        return [tool.spec() for tool in self._tools.values()]

    def names(self) -> list[str]:
        return sorted(self._tools)

    def execute(self, name: str, arguments: dict, context: ToolContext) -> dict:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolError(f"Unknown tool '{name}'.")
        if not isinstance(arguments, dict):
            raise ToolError("Tool arguments must be an object.")
        try:
            return tool.handler(context, **arguments)
        except ToolError:
            raise
        except TypeError as exc:
            raise ToolError(f"Invalid arguments for '{name}': {str(exc)[:200]}") from exc


def build_default_registry() -> ToolRegistry:
    """Registry with the tools the Data Analyst agent is allowed to use."""
    from ai_service.tools.data_tools import list_tables, run_sql
    from ai_service.tools.document_tools import search_documents

    registry = ToolRegistry()
    registry.register(
        Tool(
            name="list_tables",
            description=(
                "List the tables and columns available in a connected business "
                "database. Call this before writing SQL for a data source."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "datasource_id": {
                        "type": "string",
                        "description": "Id of the data source to inspect.",
                    }
                },
                "required": ["datasource_id"],
                "additionalProperties": False,
            },
            handler=list_tables,
        )
    )
    registry.register(
        Tool(
            name="run_sql",
            description=(
                "Run a single read-only SELECT query against an approved business "
                "database and return rows. Only SELECT statements referencing "
                "tables from list_tables are allowed; anything else is rejected."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "datasource_id": {"type": "string"},
                    "sql": {
                        "type": "string",
                        "description": "A single read-only SELECT statement.",
                    },
                    "purpose": {
                        "type": "string",
                        "description": "Short description of what the query answers.",
                    },
                },
                "required": ["datasource_id", "sql"],
                "additionalProperties": False,
            },
            handler=run_sql,
        )
    )
    registry.register(
        Tool(
            name="search_documents",
            description=(
                "Search the organization's uploaded documents for passages "
                "relevant to a question. Returns excerpts with their source."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "description": "Maximum number of passages to return.",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            handler=search_documents,
        )
    )
    return registry
