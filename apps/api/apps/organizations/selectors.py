"""Selectors: the read side of the organization domain.

All tenant-scoped reads go through this module. Views never build querysets on
Organization/Membership directly, so scoping rules live in exactly one place.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from django.db.models import QuerySet

if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.organizations.models import Membership, Organization


def get_active_membership(*, user: User, organization_id: uuid.UUID) -> Membership | None:
    """Return the caller's active membership, or None. Never leaks other tenants."""
    from apps.organizations.models import Membership

    if not getattr(user, "is_authenticated", False):
        return None
    return (
        Membership.objects.select_related("organization")
        .filter(user=user, organization_id=organization_id, is_active=True,
                organization__is_active=True)
        .first()
    )


def list_organizations_for_user(*, user: User) -> QuerySet[Organization]:
    """Organizations the user can see, ordered by name."""
    from apps.organizations.models import Organization

    return (
        Organization.objects.filter(memberships__user=user, memberships__is_active=True,
                                     is_active=True)
        .distinct()
        .order_by("name")
    )


def list_memberships(*, organization_id: uuid.UUID) -> QuerySet[Membership]:
    from apps.organizations.models import Membership

    return (
        Membership.objects.select_related("user")
        .filter(organization_id=organization_id)
        .order_by("user__email")
    )


def get_organization(*, organization_id: uuid.UUID) -> Organization | None:
    from apps.organizations.models import Organization

    return Organization.objects.filter(id=organization_id, is_active=True).first()


def user_organization_ids(*, user: User) -> set[uuid.UUID]:
    from apps.organizations.models import Membership

    return set(
        Membership.objects.filter(user=user, is_active=True).values_list(
            "organization_id", flat=True
        )
    )
