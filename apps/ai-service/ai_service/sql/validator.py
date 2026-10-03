"""SQL validation — the safety gate before anything touches a customer database.

Design: parse with a real SQL parser (sqlglot), then make assertions about the
resulting AST. Regex checks are deliberately avoided because comments, casing and
whitespace make them trivially evadable.

Rules enforced (see security/threat-model/sql-injection.md):
1. Exactly one statement.
2. The statement must be a read-only SELECT (optionally with CTEs / UNION).
3. No DDL/DML/utility nodes anywhere in the tree.
4. No locking clauses (`FOR UPDATE`), no `INTO`, no `COPY`.
5. Every referenced table must be in the datasource allowlist.
6. No access to system catalogs unless explicitly allowlisted.
7. Dangerous functions are rejected.
8. A row cap is enforced by wrapping the query, not by trusting the model to add
   a LIMIT.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp

DIALECT_BY_ENGINE = {"postgresql": "postgres", "mysql": "mysql"}

# Node types that must never appear in an approved query. Built dynamically so a
# sqlglot version that lacks one of these node classes does not break import.
_FORBIDDEN_NODE_NAMES = (
    "Insert", "Update", "Delete", "Drop", "Create", "Alter", "Command",
    "Grant", "Revoke", "Set", "Merge", "TruncateTable", "Copy", "LoadData",
)
_FORBIDDEN_NODES: tuple[type[exp.Expression], ...] = tuple(
    node for node in (getattr(exp, name, None) for name in _FORBIDDEN_NODE_NAMES) if node is not None
)

# Functions that can read/write outside the query's own result set.
_FORBIDDEN_FUNCTIONS = {
    "pg_read_file", "pg_read_binary_file", "pg_ls_dir", "pg_sleep",
    "lo_import", "lo_export", "dblink", "dblink_exec",
    "load_file", "into_outfile", "sys_eval", "sys_exec",
    "benchmark", "sleep",
}

_SYSTEM_SCHEMA_PREFIXES = ("pg_catalog", "information_schema", "mysql", "performance_schema", "sys")


class SQLValidationError(ValueError):
    """Raised when a statement fails validation. The message is safe to show."""

    def __init__(self, message: str, *, code: str = "sql_rejected", detail: dict | None = None):
        super().__init__(message)
        self.code = code
        self.detail = detail or {}


@dataclass
class ValidationResult:
    original_sql: str
    safe_sql: str
    dialect: str
    tables: list[str] = field(default_factory=list)
    applied_limit: int | None = None


def validate_read_only_query(
    sql: str,
    *,
    engine: str,
    allowed_tables: set[str],
    max_rows: int = 500,
    max_joins: int = 6,
    allow_system_tables: bool = False,
) -> ValidationResult:
    """Validate and rewrite a SQL statement so it is safe to execute."""
    if not sql or not sql.strip():
        raise SQLValidationError("The query is empty.", code="sql_empty")

    dialect = DIALECT_BY_ENGINE.get(engine)
    if dialect is None:
        raise SQLValidationError(f"Unsupported engine '{engine}'.", code="sql_engine_unsupported")

    try:
        statements = [s for s in sqlglot.parse(sql, read=dialect) if s is not None]
    except sqlglot.errors.ParseError as exc:
        raise SQLValidationError("The SQL could not be parsed.", code="sql_parse_error",
                                 detail={"reason": str(exc)[:200]}) from exc

    if len(statements) != 1:
        raise SQLValidationError(
            "Only a single statement may be executed.", code="sql_multiple_statements"
        )

    statement = statements[0]

    if not _is_read_only_select(statement):
        raise SQLValidationError(
            "Only read-only SELECT queries are permitted.", code="sql_not_select"
        )

    _assert_no_forbidden_nodes(statement)
    _assert_no_locking(statement)
    _assert_no_forbidden_functions(statement)

    tables = _referenced_tables(statement)
    _assert_tables_allowed(tables, allowed_tables, allow_system_tables=allow_system_tables)

    join_count = len(list(statement.find_all(exp.Join)))
    if join_count > max_joins:
        raise SQLValidationError(
            f"The query joins {join_count} tables; the limit is {max_joins}.",
            code="sql_too_many_joins",
        )

    safe_sql, applied_limit = _enforce_row_cap(statement, dialect=dialect, max_rows=max_rows)
    return ValidationResult(
        original_sql=sql,
        safe_sql=safe_sql,
        dialect=dialect,
        tables=sorted(tables),
        applied_limit=applied_limit,
    )


# --- Rule helpers ------------------------------------------------------------

def _is_read_only_select(statement: exp.Expression) -> bool:
    if isinstance(statement, (exp.Select, exp.Union, exp.Except, exp.Intersect)):
        return True
    # A WITH ... SELECT parses as a Select with a `with` arg in sqlglot.
    return isinstance(statement, exp.Subquery)


def _assert_no_forbidden_nodes(statement: exp.Expression) -> None:
    for node_type in _FORBIDDEN_NODES:
        if statement.find(node_type) is not None:
            raise SQLValidationError(
                f"Statement contains a forbidden operation: {node_type.__name__}.",
                code="sql_forbidden_statement",
            )


def _assert_no_locking(statement: exp.Expression) -> None:
    for _lock in statement.find_all(exp.Lock):
        raise SQLValidationError("Locking clauses are not permitted.", code="sql_locking_clause")
    # sqlglot may expose FOR UPDATE as a comment-level arg; check the raw text too.
    for keyword in ("for update", "for share", "lock in share mode"):
        if keyword in statement.sql().lower():
            raise SQLValidationError("Locking clauses are not permitted.",
                                     code="sql_locking_clause")


def _assert_no_forbidden_functions(statement: exp.Expression) -> None:
    for func in statement.find_all(exp.Func):
        for name in _function_names(func):
            if name in _FORBIDDEN_FUNCTIONS:
                raise SQLValidationError(f"Function '{name}' is not permitted.",
                                         code="sql_forbidden_function")


def _function_names(func: exp.Expression) -> set[str]:
    """All plausible spellings of a function's name.

    `sql_name()` returns a class-level label ("ANONYMOUS" for unparsed functions),
    so unknown functions are matched by their literal name instead.
    """
    names: set[str] = set()
    literal = getattr(func, "name", None)
    if isinstance(literal, str) and literal:
        names.add(literal.lower())
    if not isinstance(func, exp.Anonymous):
        try:
            sql_name = func.sql_name()
            if sql_name and sql_name.lower() != "anonymous":
                names.add(sql_name.lower())
        except (AttributeError, TypeError):
            pass
    return names


def _referenced_tables(statement: exp.Expression) -> set[str]:
    """Tables the statement actually reads.

    CTE aliases appear as table references in the AST but are not real tables, so
    they are excluded before the allowlist check.
    """
    cte_names = {cte.alias_or_name.lower() for cte in statement.find_all(exp.CTE)}
    tables: set[str] = set()
    for table in statement.find_all(exp.Table):
        name = table.name
        if not name:
            continue
        if not table.db and name.lower() in cte_names:
            continue
        schema = table.db or ""
        tables.add(f"{schema}.{name}" if schema else name)
    return tables


def _assert_tables_allowed(tables: set[str], allowed: set[str], *, allow_system_tables: bool) -> None:
    if not allowed:
        raise SQLValidationError(
            "No schema metadata is available for this data source; refresh its schema first.",
            code="sql_no_schema",
        )
    allowed_short = {t.split(".")[-1] for t in allowed}
    for table in tables:
        if table in allowed:
            continue
        if table.split(".")[-1] in allowed_short and "." not in table:
            continue
        schema = table.split(".")[0] if "." in table else ""
        if schema.lower() in _SYSTEM_SCHEMA_PREFIXES and not allow_system_tables:
            raise SQLValidationError(
                f"Access to system table '{table}' is not permitted.",
                code="sql_system_table",
            )
        raise SQLValidationError(
            f"Table '{table}' is not part of this data source's discovered schema.",
            code="sql_unknown_table",
            detail={"table": table},
        )


def _enforce_row_cap(statement: exp.Expression, *, dialect: str, max_rows: int) -> tuple[str, int | None]:
    """Wrap the query so the row cap cannot be bypassed by the model.

    Wrapping (rather than trusting an inner LIMIT) means the cap holds even for
    UNIONs, CTEs and any LIMIT the model may have written itself.
    """
    existing = _existing_limit(statement)
    inner = statement.sql(dialect=dialect)
    if existing is not None and existing <= max_rows and not _is_compound(statement):
        return inner, existing
    return f"SELECT * FROM ({inner}) AS dataforge_bounded LIMIT {max_rows}", max_rows


def _existing_limit(statement: exp.Expression) -> int | None:
    limit = statement.args.get("limit")
    if limit is None:
        return None
    expression = getattr(limit, "expression", None) or getattr(limit, "this", None)
    for candidate in (getattr(expression, "name", None), getattr(expression, "this", None)):
        try:
            return int(candidate)
        except (TypeError, ValueError):
            continue
    return None


def _is_compound(statement: exp.Expression) -> bool:
    return isinstance(statement, (exp.Union, exp.Except, exp.Intersect))
