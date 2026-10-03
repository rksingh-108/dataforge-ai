"""Services: the write side of the organization domain.

Views call these functions; they do not touch models for writes directly. Each
service enforces invariants (e.g. "an organization always has at least one owner")
and records an audit entry for security-relevant changes.
"""
from __future__ import annotations

from django.db import transaction
from django.utils.text import slugify

from apps.accounts.models import User
from apps.common.exceptions import Conflict
from apps.common.rbac import Role
from apps.organizations.models import Membership, Organization


def _record(action: str, *, organization: Organization, actor: User | None, **metadata) -> None:
    # Imported lazily to keep the app dependency direction acyclic.
    from apps.analytics.services import record_audit

    record_audit(
        organization=organization,
        actor=actor,
        action=action,
        target_type="organization",
        target_id=str(organization.id),
        metadata=metadata,
    )


def _unique_slug(name: str) -> str:
    base = slugify(name)[:180] or "org"
    slug = base
    suffix = 1
    while Organization.objects.filter(slug=slug).exists():
        suffix += 1
        slug = f"{base}-{suffix}"
    return slug


@transaction.atomic
def create_organization(*, name: str, actor: User) -> Organization:
    """Create an organization and make `actor` its owner."""
    organization = Organization.objects.create(
        name=name.strip(), slug=_unique_slug(name), created_by=actor
    )
    Membership.objects.create(organization=organization, user=actor, role=Role.OWNER.value)
    _record("organization.created", organization=organization, actor=actor, name=organization.name)
    return organization


@transaction.atomic
def add_member(*, organization: Organization, actor: User, email: str, role: str) -> Membership:
    """Add an existing user to the organization, or reactivate a prior membership."""
    try:
        user = User.objects.get(email__iexact=email.strip())
    except User.DoesNotExist as exc:
        raise Conflict(detail={"email": "No user with that email exists yet."}) from exc

    membership, created = Membership.objects.get_or_create(
        organization=organization,
        user=user,
        defaults={"role": role, "is_active": True},
    )
    if not created:
        if membership.is_active:
            raise Conflict(detail={"email": "That user is already a member."})
        membership.is_active = True
        membership.role = role
        membership.save(update_fields=["is_active", "role", "updated_at"])

    _record("membership.added", organization=organization, actor=actor,
            member=str(user.id), role=role)
    return membership


@transaction.atomic
def change_role(*, organization: Organization, actor: User, membership: Membership,
                role: str) -> Membership:
    _ensure_not_last_owner(organization, membership, new_role=role)
    old = membership.role
    membership.role = role
    membership.save(update_fields=["role", "updated_at"])
    _record("membership.role_changed", organization=organization, actor=actor,
            member=str(membership.user_id), from_role=old, to_role=role)
    return membership


@transaction.atomic
def remove_member(*, organization: Organization, actor: User, membership: Membership) -> None:
    _ensure_not_last_owner(organization, membership, new_role=None)
    membership.is_active = False
    membership.save(update_fields=["is_active", "updated_at"])
    _record("membership.removed", organization=organization, actor=actor,
            member=str(membership.user_id))


def _ensure_not_last_owner(organization: Organization, membership: Membership,
                           new_role: str | None) -> None:
    """An organization must always retain at least one active owner."""
    if membership.role != Role.OWNER.value:
        return
    if new_role == Role.OWNER.value:
        return
    remaining = Membership.objects.filter(
        organization=organization, role=Role.OWNER.value, is_active=True
    ).exclude(pk=membership.pk).count()
    if remaining == 0:
        raise Conflict(detail={"role": "An organization must keep at least one owner."})
