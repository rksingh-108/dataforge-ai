"""Adversarial tests for SQL validation.

This is the most security-critical component in the product. Every test here is a
statement a hostile user or a manipulated model might try to slip through.
"""
from __future__ import annotations

import pytest

from ai_service.sql.validator import SQLValidationError, validate_read_only_query

ALLOWED = {"public.orders", "public.customers"}


def validate(sql: str, *, engine: str = "postgresql", allowed: set[str] | None = None,
             max_rows: int = 100, max_joins: int = 6):
    return validate_read_only_query(
        sql,
        engine=engine,
        allowed_tables=ALLOWED if allowed is None else allowed,
        max_rows=max_rows,
        max_joins=max_joins,
    )


# --- Accepted ----------------------------------------------------------------

def test_select_is_accepted_and_capped():
    result = validate("SELECT id, total FROM orders")
    assert result.tables == ["orders"]
    assert result.applied_limit == 100
    assert "LIMIT 100" in result.safe_sql.upper()


def test_join_and_aggregate_is_accepted():
    result = validate(
        "SELECT c.name, SUM(o.total) AS revenue "
        "FROM orders o JOIN customers c ON c.id = o.customer_id GROUP BY c.name"
    )
    assert set(result.tables) == {"orders", "customers"}


def test_cte_is_accepted():
    result = validate(
        "WITH recent AS (SELECT * FROM orders) SELECT COUNT(*) FROM recent"
    )
    # The CTE alias `recent` must not be treated as a real table.
    assert result.tables == ["orders"]


def test_schema_qualified_table_is_accepted():
    validate("SELECT 1 FROM public.orders")


def test_existing_smaller_limit_is_preserved():
    result = validate("SELECT id FROM orders LIMIT 10")
    assert result.applied_limit == 10
    assert "dataforge_bounded" not in result.safe_sql


# --- Rejected: writes and DDL -------------------------------------------------

@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM orders",
        "UPDATE orders SET total = 0",
        "INSERT INTO orders (id) VALUES (1)",
        "DROP TABLE orders",
        "TRUNCATE TABLE orders",
        "ALTER TABLE orders ADD COLUMN x int",
        "CREATE TABLE evil (id int)",
        "GRANT ALL ON orders TO public",
    ],
)
def test_write_and_ddl_are_rejected(sql):
    with pytest.raises(SQLValidationError):
        validate(sql)


def test_data_modifying_cte_is_rejected():
    with pytest.raises(SQLValidationError):
        validate(
            "WITH x AS (DELETE FROM orders RETURNING id) SELECT * FROM x"
        )


def test_multiple_statements_are_rejected():
    with pytest.raises(SQLValidationError) as exc:
        validate("SELECT 1 FROM orders; DROP TABLE customers")
    assert exc.value.code in {"sql_multiple_statements", "sql_forbidden_statement"}


def test_union_of_writes_is_rejected():
    with pytest.raises(SQLValidationError):
        validate("SELECT id FROM orders UNION SELECT id FROM orders; DELETE FROM orders")


# --- Rejected: locking, INTO, dangerous functions ----------------------------

def test_for_update_is_rejected():
    with pytest.raises(SQLValidationError) as exc:
        validate("SELECT * FROM orders FOR UPDATE")
    assert exc.value.code in {"sql_locking_clause", "sql_forbidden_statement"}


def test_pg_read_file_is_rejected():
    with pytest.raises(SQLValidationError) as exc:
        validate("SELECT pg_read_file('/etc/passwd')")
    assert exc.value.code == "sql_forbidden_function"


def test_mysql_load_file_is_rejected():
    with pytest.raises(SQLValidationError) as exc:
        validate("SELECT LOAD_FILE('/etc/passwd')", engine="mysql")
    assert exc.value.code == "sql_forbidden_function"


def test_into_outfile_is_rejected():
    with pytest.raises(SQLValidationError):
        validate("SELECT * FROM orders INTO OUTFILE '/tmp/x'", engine="mysql")


# --- Rejected: table scope ---------------------------------------------------

def test_unknown_table_is_rejected():
    with pytest.raises(SQLValidationError) as exc:
        validate("SELECT * FROM secret_payroll")
    assert exc.value.code == "sql_unknown_table"


def test_other_schema_table_is_rejected():
    with pytest.raises(SQLValidationError) as exc:
        validate("SELECT * FROM other_tenant.orders")
    assert exc.value.code == "sql_unknown_table"


def test_system_catalog_is_rejected():
    with pytest.raises(SQLValidationError) as exc:
        validate("SELECT * FROM pg_catalog.pg_shadow")
    assert exc.value.code == "sql_system_table"


def test_comment_obfuscation_does_not_bypass_table_check():
    with pytest.raises(SQLValidationError):
        validate("SELECT * FROM /* public.orders */ secret_payroll")


def test_no_schema_available_rejects_everything():
    with pytest.raises(SQLValidationError) as exc:
        validate("SELECT 1 FROM orders", allowed=set())
    assert exc.value.code == "sql_no_schema"


def test_too_many_joins_is_rejected():
    sql = "SELECT * FROM orders a JOIN customers b ON TRUE"
    with pytest.raises(SQLValidationError) as exc:
        validate(sql, allowed=ALLOWED, max_joins=0)
    assert exc.value.code == "sql_too_many_joins"


# --- Rejected: malformed -----------------------------------------------------

def test_empty_sql_is_rejected():
    with pytest.raises(SQLValidationError) as exc:
        validate("   ")
    assert exc.value.code == "sql_empty"


def test_unparseable_sql_is_rejected():
    with pytest.raises(SQLValidationError) as exc:
        validate("SELECT FROM WHERE ((")
    assert exc.value.code in {"sql_parse_error", "sql_not_select", "sql_forbidden_statement"}


def test_explain_is_not_treated_as_a_select():
    # EXPLAIN can leak plan/statistics info; it is not a plain SELECT.
    with pytest.raises(SQLValidationError):
        validate("EXPLAIN SELECT * FROM orders")
