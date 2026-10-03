#!/usr/bin/env python3
"""Enforce the service boundaries documented in docs/architecture/service-boundaries.md
*and* the tenant-scope rules documented in docs/architecture/authorization-model.md.

Rules checked:
1. `apps/api` must not import the AI service in-process (no `flask`, no
   `ai_service` imports) — they communicate over HTTP only.
2. `apps/ai-service` must not import Django — it must never reach the platform
   database directly.
3. The frontend must not ship a database driver dependency.
4. `apps/api` must not read the client-controlled `X-Organization-Id` header for
   authorization; organization scope must come from the URL route plus a verified
   membership (see `apps/common/permissions.py`).
5. A tenant-scoped selector call must not receive an organization id taken from a
   client-controlled source (`kwargs`, `query_params`, `request.data`). Use the
   verified `require_organization(request)` instead.

Exits non-zero with a human-readable report when a rule is violated.
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FORBIDDEN_IN_API = {"flask", "ai_service"}

# A client can set this header freely; it must never decide tenant scope.
FORBIDDEN_API_STRINGS = {"X-Organization-Id"}

# Attribute names that read a value from the client (URL kwargs, query string, body).
CLIENT_CONTROLLED_SOURCES = {"kwargs", "query_params", "data"}

# Keyword names on a selector/service call that carry the tenant scope.
SCOPE_KEYWORDS = {"organization_id", "organization", "org_id"}
FORBIDDEN_IN_AI_SERVICE = {"django", "rest_framework", "channels"}
FORBIDDEN_WEB_DEPS = {
    "pg", "postgres", "mysql", "mysql2", "sqlite3", "better-sqlite3", "typeorm",
    "prisma", "@prisma/client", "sequelize", "knex",
}


def iter_python_files(directory: Path) -> list[Path]:
    return [
        path
        for path in directory.rglob("*.py")
        if "migrations" not in path.parts and "__pycache__" not in path.parts
    ]


def imported_roots(path: Path) -> set[str]:
    """Top-level module names imported by a Python file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError) as exc:
        print(f"  ! could not parse {path.relative_to(ROOT)}: {exc}")
        return set()

    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def check_forbidden(root_dir: Path, forbidden: set[str], label: str) -> list[str]:
    problems: list[str] = []
    if not root_dir.exists():
        return problems
    for path in iter_python_files(root_dir):
        hits = imported_roots(path) & forbidden
        for hit in sorted(hits):
            problems.append(
                f"{label}: {path.relative_to(ROOT)} imports '{hit}' "
                f"(forbidden by service-boundaries.md)"
            )
    return problems


def _reads_client_controlled_source(node: ast.AST) -> bool:
    """True if an expression derives its value from the request's client input."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Attribute) and sub.attr in CLIENT_CONTROLLED_SOURCES:
            return True
    return False


def _header_names_read(tree: ast.AST) -> set[str]:
    """Header names actually read from the request via ``.headers`` / ``.META``.

    Only real reads are collected; a header named in a docstring or a comment is
    documentation, not a scope decision.
    """
    names: set[str] = set()

    def _string_args(node: ast.AST) -> list[str]:
        candidates: list[ast.AST] = []
        if isinstance(node, ast.Call):
            candidates = list(node.args)
        elif isinstance(node, ast.Subscript):
            candidates = [node.slice]
        return [
            c.value
            for c in candidates
            if isinstance(c, ast.Constant) and isinstance(c.value, str)
        ]

    for node in ast.walk(tree):
        receiver = None
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            receiver = node.func.value
        elif isinstance(node, ast.Subscript):
            receiver = node.value
        if isinstance(receiver, ast.Attribute) and receiver.attr in {"headers", "META"}:
            names.update(_string_args(node))
    return names


def check_forbidden_strings(root_dir: Path, label: str) -> list[str]:
    """Rule 4: forbid reads of a client-controlled tenant-scope header."""
    problems: list[str] = []
    for path in iter_python_files(root_dir):
        if "tests" in path.parts:
            continue  # negative tests legitimately reference the header
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        read = _header_names_read(tree) & FORBIDDEN_API_STRINGS
        for name in sorted(read):
            problems.append(
                f"{label}: {path.relative_to(ROOT)} reads the client-controlled "
                f"'{name}' header. Organization scope must come from the URL + a "
                f"verified membership, never a client header (authorization-model.md)."
            )
    return problems


def check_client_controlled_scope(root_dir: Path, label: str) -> list[str]:
    """Rule 5: tenant selectors must not receive a client-controlled org id."""
    problems: list[str] = []
    for path in iter_python_files(root_dir):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for keyword in node.keywords:
                if keyword.arg in SCOPE_KEYWORDS and _reads_client_controlled_source(keyword.value):
                    problems.append(
                        f"{label}: {path.relative_to(ROOT)}:{keyword.value.lineno} passes a "
                        f"client-controlled '{keyword.arg}' into a call. Use "
                        f"require_organization(request) so the scope is verified."
                    )
    return problems


def check_web_dependencies() -> list[str]:
    manifest = ROOT / "apps" / "web" / "package.json"
    if not manifest.exists():
        return []
    data = json.loads(manifest.read_text(encoding="utf-8"))
    declared = set(data.get("dependencies", {})) | set(data.get("devDependencies", {}))
    hits = declared & FORBIDDEN_WEB_DEPS
    return [
        f"web: package.json depends on '{dep}' (the frontend must not access databases)"
        for dep in sorted(hits)
    ]


def main() -> int:
    problems: list[str] = []
    problems += check_forbidden(ROOT / "apps" / "api", FORBIDDEN_IN_API, "api")
    problems += check_forbidden(ROOT / "apps" / "ai-service", FORBIDDEN_IN_AI_SERVICE, "ai-service")
    problems += check_web_dependencies()
    problems += check_forbidden_strings(ROOT / "apps" / "api", "api")
    problems += check_client_controlled_scope(ROOT / "apps" / "api", "api")

    if problems:
        print("Service boundary violations found:\n")
        for problem in problems:
            print(f"  x {problem}")
        print("\nSee docs/architecture/service-boundaries.md for the rules.")
        return 1

    print("Service boundaries OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
