"""Data source models.

A `DataSource` is a connection to a customer's business database. The password
is stored **encrypted** (`password_encrypted`) and is never exposed through the
API. Discovered schema is cached in `SchemaTable` / `SchemaColumn` so the UI and
the SQL safety layer can reason about allowed tables without re-connecting.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.crypto import decrypt_secret, encrypt_secret
from apps.common.models import BaseModel, OrganizationScopedModel


class DataSourceEngine(models.TextChoices):
    POSTGRESQL = "postgresql", "PostgreSQL"
    MYSQL = "mysql", "MySQL"


class DataSourceStatus(models.TextChoices):
    UNKNOWN = "unknown", "Unknown"
    CONNECTED = "connected", "Connected"
    ERROR = "error", "Error"


class DataSource(OrganizationScopedModel):
    name = models.CharField(max_length=150)
    description = models.CharField(max_length=500, blank=True)
    engine = models.CharField(max_length=20, choices=DataSourceEngine.choices)
    host = models.CharField(max_length=255)
    port = models.PositiveIntegerField()
    database_name = models.CharField(max_length=128)
    username = models.CharField(max_length=128)
    password_encrypted = models.BinaryField()

    # Read-only is the default and the safe choice. Non-read-only connections are
    # still only ever used for read-only queries by the AI service.
    is_read_only = models.BooleanField(default=True)
    ssl_mode = models.CharField(max_length=20, default="prefer")

    status = models.CharField(
        max_length=16, choices=DataSourceStatus.choices, default=DataSourceStatus.UNKNOWN
    )
    last_error = models.TextField(blank=True)
    last_tested_at = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="datasources_created",
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"], name="unique_datasource_name_per_org"
            ),
        ]
        indexes = [models.Index(fields=["organization", "status"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.engine})"

    # --- Credential handling ------------------------------------------------
    def set_password(self, plaintext: str) -> None:
        self.password_encrypted = encrypt_secret(plaintext)

    def get_password(self) -> str:
        """Decrypt and return the password. Callers must never log or serialize this."""
        return decrypt_secret(self.password_encrypted)

    def connection_config(self) -> dict:
        """Plain connection settings for the AI service. Never serialize to a client."""
        return {
            "engine": self.engine,
            "host": self.host,
            "port": self.port,
            "database": self.database_name,
            "username": self.username,
            "password": self.get_password(),
            "ssl_mode": self.ssl_mode,
        }


class SchemaTable(BaseModel):
    datasource = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, related_name="tables"
    )
    schema_name = models.CharField(max_length=128, default="public")
    table_name = models.CharField(max_length=128)
    row_estimate = models.BigIntegerField(null=True, blank=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["schema_name", "table_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["datasource", "schema_name", "table_name"],
                name="unique_table_per_datasource",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.schema_name}.{self.table_name}"


class SchemaColumn(BaseModel):
    table = models.ForeignKey(SchemaTable, on_delete=models.CASCADE, related_name="columns")
    column_name = models.CharField(max_length=128)
    data_type = models.CharField(max_length=128)
    is_nullable = models.BooleanField(default=True)
    is_primary_key = models.BooleanField(default=False)
    ordinal_position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordinal_position"]
        constraints = [
            models.UniqueConstraint(
                fields=["table", "column_name"], name="unique_column_per_table"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.table.table_name}.{self.column_name}"
