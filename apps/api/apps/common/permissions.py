"""Authorization permission classes and the tenant-scope authority.

These are the *only* sanctioned way for a view to decide "may this caller touch
this organization's data?". Views must never re-implement the check.

Organization scope is derived from **one** source, in this module:

    URL kwarg ``org_id``  ->  active Membership(user, organization)

A client-supplied ``X-Organization-Id`` header is **deliberately ignored** for
authorization. It is fully attacker-controlled, so accepting it as a scope
fallback would let a member of one tenant read another tenant's data by changing
a single request header. Clients that need multi-organization context must
address the organization in the URL path; the server then verifies membership.
The header ban is enforced structurally by ``scripts/dev/check_boundaries.py``.

A caller with no active membership in the resolved organization is rejected with
**404** (not 403) for object routes, so that the existence of other tenants'
resources is not disclosed. The distinction is deliberate and documented in
docs/architecture/authorization-model.md.
"""
from __future__ import annotations

import uuid

from rest_framework import permissions

from apps.common.exceptions import NotFound
from apps.common.rbac import Permission, permissions_for, role_has_permission


class OrganizationAccess:
    """Mixin that resolves membership and exposes permission checks to a view."""

    @staticmethod
    def resolve_org_id(request) -> uuid.UUID | None:
        """The organization id this request targets, taken only from the URL.

        The client-controlled ``X-Organization-Id`` header is intentionally not
        consulted. A malformed or absent ``org_id`` resolves to ``None``, which
        makes the scope "unresolved" and therefore fail closed.
        """
        match = getattr(request, "resolver_match", None)
        raw = match.kwargs.get("org_id") if match else None
        if not raw:
            return None
        try:
            return uuid.UUID(str(raw))
        except (ValueError, TypeError):
            return None

    def get_membership(self, request):
        """Return the caller's active membership, or None."""
        if getattr(request, "membership", None) is not None:
            return request.membership
        from apps.organizations.selectors import get_active_membership

        org_id = self.resolve_org_id(request)
        if org_id is None:
            return None
        membership = get_active_membership(user=request.user, organization_id=org_id)
        if membership is not None:
            request.membership = membership
            request.organization = membership.organization
        return membership


class IsOrganizationMember(OrganizationAccess, permissions.BasePermission):
    """Allows the request only if the caller has an active membership."""

    message = "You do not have access to this organization."

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        # Org list/creation endpoints are not org-scoped; let them through.
        if view.__class__.__name__ in {"OrganizationListCreateView"}:
            return True
        if self.get_membership(request) is None:
            # 404 (not 403): a non-member must not learn that the org exists.
            raise NotFound("Resource not found.")
        return True


def has_organization_permission(request, permission: Permission) -> bool:
    """Standalone helper for views that cannot use a permission class."""
    membership = getattr(request, "membership", None)
    if membership is None:
        access = OrganizationAccess()
        membership = access.get_membership(request)
    if membership is None:
        return False
    return role_has_permission(membership.role, str(permission))


def require_organization(request):
    """Return the **verified** organization for this request.

    This is the single sanctioned way for a view, service or selector to obtain
    the tenant to operate on. The result comes from the caller's active
    membership — never from the URL id directly, the request body, a query
    parameter or a header. Passing a raw ``org_id`` (from any client-controlled
    source) into a selector bypasses this verification and is forbidden by the
    tenant-scope guard in ``scripts/dev/check_boundaries.py``.

    Raises :class:`NotFound` when there is no verified membership, preserving the
    404-not-403 convention.
    """
    membership = getattr(request, "membership", None)
    if membership is None:
        membership = OrganizationAccess().get_membership(request)
    if membership is None:
        raise NotFound("Resource not found.")
    return membership.organization


class HasOrganizationPermission(OrganizationAccess, permissions.BasePermission):
    """Permission class that requires both membership and a specific permission.

    Subclass and set ``required_permission``, or use :func:`require_permission`.
    """

    required_permission: Permission | None = None
    message = "Your role does not allow this action."

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        membership = self.get_membership(request)
        if membership is None:
            # Org-scoped route the caller cannot see: 404 to avoid disclosure.
            if self.resolve_org_id(request) is not None:
                raise NotFound("Resource not found.")
            # Non-scoped views (e.g. /me/) have no organization; allow.
            return self.required_permission is None
        if self.required_permission is None:
            return True
        return role_has_permission(membership.role, str(self.required_permission))


def require_permission(permission: Permission):
    """Build a permission class requiring one permission (used via `.as_view`)."""

    return type(
        f"Requires{permission.name.title().replace('_', '')}",
        (HasOrganizationPermission,),
        {"required_permission": permission},
    )


__all__ = [
    "HasOrganizationPermission",
    "IsOrganizationMember",
    "OrganizationAccess",
    "has_organization_permission",
    "permissions_for",
    "require_organization",
    "require_permission",
]
