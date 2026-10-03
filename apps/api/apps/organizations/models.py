"""Organization tenancy models.

`Organization` is the tenant boundary. `Membership` is the pivot that grants a
user a role inside an organization. Every tenant-owned record in the system
hangs off `Organization`, and every request is scoped through a `Membership`.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel
from apps.common.rbac import Role

ROLE_CHOICES = [(role.value, role.label if hasattr(role, "label") else role.value.title())
                for role in Role]


class Organization(BaseModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="organizations_created",
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(name=""), name="organization_name_not_blank"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.slug})"


class Membership(BaseModel):
    """A user's role within one organization. The unit of authorization."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["organization__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"], name="unique_membership_per_org"
            ),
        ]
        indexes = [models.Index(fields=["user", "is_active"])]

    def __str__(self) -> str:
        return f"{self.user_id} as {self.role} in {self.organization_id}"

    @property
    def permissions(self) -> frozenset[str]:
        from apps.common.rbac import permissions_for

        return permissions_for(self.role)
