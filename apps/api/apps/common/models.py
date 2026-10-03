"""Abstract base models.

Conventions:
- Every model uses a UUID primary key (safe to expose, no enumeration).
- Every model records ``created_at`` / ``updated_at``.
- Tenant-owned models inherit ``OrganizationScopedModel`` so that the tenant
  column is impossible to forget.
"""
from __future__ import annotations

import uuid

from django.db import models


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimeStampedModel):
    class Meta:
        abstract = True


class OrganizationScopedModel(BaseModel):
    """Base for any model that belongs to exactly one organization."""

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_set",
        db_index=True,
    )

    class Meta:
        abstract = True


class AppendOnlyModel(BaseModel):
    """Base for records that must never be modified after creation (audit).

    ``save`` on an existing row and ``delete`` are blocked by the manager so the
    guarantee is enforced in the code path, not only by convention.
    """

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self._state.adding is False and not kwargs.pop("_allow_update", False):
            raise ValueError(f"{type(self).__name__} records are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError(f"{type(self).__name__} records cannot be deleted.")
