"""Role-Based Access Control.

Roles are organization-scoped. The permission matrix lives in code (not in the
database) so it is version-controlled, reviewable and testable. The database
stores only the role a membership holds.

If a permission is needed that is not in this matrix, add it here *and* add a
test in `tests/security/test_authorization_matrix.py`.
"""
from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class Permission(StrEnum):
    ORG_VIEW = "org.view"
    ORG_MANAGE = "org.manage"
    MEMBER_MANAGE = "member.manage"
    DATASOURCE_VIEW = "datasource.view"
    DATASOURCE_MANAGE = "datasource.manage"
    DOCUMENT_VIEW = "document.view"
    DOCUMENT_MANAGE = "document.manage"
    ANALYST_QUERY = "analyst.query"
    EXECUTION_VIEW = "execution.view"
    AUDIT_VIEW = "audit.view"


_VIEWER = {
    Permission.ORG_VIEW,
    Permission.DATASOURCE_VIEW,
    Permission.DOCUMENT_VIEW,
    Permission.EXECUTION_VIEW,
}

_ANALYST = _VIEWER | {
    Permission.DOCUMENT_MANAGE,
    Permission.ANALYST_QUERY,
}

_ADMIN = _ANALYST | {
    Permission.ORG_MANAGE,
    Permission.MEMBER_MANAGE,
    Permission.DATASOURCE_MANAGE,
    Permission.AUDIT_VIEW,
}

_OWNER = _ADMIN  # Owners additionally control organization lifecycle (see below).

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.VIEWER: frozenset(_VIEWER),
    Role.ANALYST: frozenset(_ANALYST),
    Role.ADMIN: frozenset(_ADMIN),
    Role.OWNER: frozenset(_OWNER),
}


def permissions_for(role: str) -> frozenset[str]:
    """Return the permission strings granted to a role.

    Unknown roles grant nothing (fail closed).
    """
    try:
        resolved = Role(role)
    except ValueError:
        return frozenset()
    return frozenset(str(p) for p in ROLE_PERMISSIONS[resolved])


def role_has_permission(role: str, permission: str) -> bool:
    """True if `role` grants `permission`."""
    return permission in permissions_for(role)


def is_organization_manager(role: str) -> bool:
    """Owners and admins may administrate the organization."""
    return role_has_permission(role, Permission.MEMBER_MANAGE)
