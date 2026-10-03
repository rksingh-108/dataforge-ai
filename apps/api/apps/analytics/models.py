"""Execution tracking and the append-only audit log.

`Execution` records one AI run: what was asked, which tools ran, what came back.
`AuditLog` records security-relevant actions and can never be updated or deleted
through the ORM (see `AppendOnlyModel`).
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import AppendOnlyModel, BaseModel, OrganizationScopedModel


class ExecutionKind(models.TextChoices):
    ANALYST_QUERY = "analyst_query", "Analyst query"
    DOCUMENT_PROCESSING = "document_processing", "Document processing"


class ExecutionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"


class Execution(OrganizationScopedModel):
    """One AI execution, scoped to an organization."""

    kind = models.CharField(max_length=32, choices=ExecutionKind.choices)
    status = models.CharField(
        max_length=16, choices=ExecutionStatus.choices, default=ExecutionStatus.PENDING
    )
    question = models.TextField(blank=True)
    answer = models.TextField(blank=True)
    error = models.TextField(blank=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="executions"
    )
    datasource = models.ForeignKey(
        "datasources.DataSource", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="executions",
    )
    document = models.ForeignKey(
        "documents.Document", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="executions",
    )

    provider = models.CharField(max_length=64, blank=True)
    model_name = models.CharField(max_length=128, blank=True)
    total_tokens = models.PositiveIntegerField(default=0)
    duration_ms = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    request_id = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "-created_at"]),
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["kind"]),
        ]

    def __str__(self) -> str:
        return f"Execution {self.id} ({self.kind}/{self.status})"

    @property
    def is_terminal(self) -> bool:
        return self.status in {ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED}


class ExecutionStep(BaseModel):
    """A single tool invocation (or reasoning phase) inside an execution.

    We record *what* a tool did at a high level (summaries, not raw
    chain-of-thought) so the UI can show progress without exposing private
    model reasoning.
    """

    execution = models.ForeignKey(Execution, on_delete=models.CASCADE, related_name="steps")
    index = models.PositiveIntegerField()
    tool_name = models.CharField(max_length=64, blank=True)
    title = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=16, choices=ExecutionStatus.choices, default=ExecutionStatus.SUCCEEDED
    )
    input_summary = models.JSONField(default=dict, blank=True)
    output_summary = models.JSONField(default=dict, blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["execution", "index"]
        constraints = [
            models.UniqueConstraint(fields=["execution", "index"], name="unique_step_index"),
        ]

    def __str__(self) -> str:
        return f"{self.execution_id}#{self.index} {self.tool_name}"


class AuditLog(AppendOnlyModel):
    """Append-only record of a security-relevant action.

    `organization` is nullable so that account-level events (login/logout) that
    are not yet tied to an organization can still be recorded.
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="audit_entries",
    )
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=64, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    request_id = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "-created_at"]),
            models.Index(fields=["action"]),
            models.Index(fields=["actor"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} by {self.actor_id or 'system'}"
