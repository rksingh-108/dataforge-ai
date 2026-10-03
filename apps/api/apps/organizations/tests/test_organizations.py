"""Organization, membership and RBAC tests."""
from __future__ import annotations

import pytest
from django.urls import reverse

from apps.common.rbac import Role
from apps.organizations.models import Membership, Organization

pytestmark = pytest.mark.django_db


def _detail(org_id):
    return reverse("organization-detail", kwargs={"org_id": org_id})


def _members(org_id):
    return reverse("organization-members", kwargs={"org_id": org_id})


def test_list_shows_only_my_organizations(auth_client, user, organization, other_user):
    foreign = Organization.objects.create(name="Globex", slug="globex", created_by=other_user)
    Membership.objects.create(organization=foreign, user=other_user, role=Role.OWNER.value)

    response = auth_client.get(reverse("organization-list"))
    assert response.status_code == 200
    ids = {row["id"] for row in response.json()}
    assert ids == {str(organization.id)}


def test_create_organization_makes_caller_owner(auth_client, user):
    response = auth_client.post(reverse("organization-list"), {"name": "Initech"}, format="json")
    assert response.status_code == 201
    org_id = response.json()["id"]
    assert Membership.objects.get(organization_id=org_id, user=user).role == Role.OWNER.value


def test_non_member_cannot_read_organization(auth_client, other_user):
    foreign = Organization.objects.create(name="Globex", slug="globex", created_by=other_user)
    Membership.objects.create(organization=foreign, user=other_user, role=Role.OWNER.value)
    # 404, so the existence of another tenant's org is not disclosed.
    assert auth_client.get(_detail(foreign.id)).status_code == 404


def test_admin_can_add_member(auth_client, organization, other_user, make_member):
    _admin, admin_client = make_member(organization, Role.ADMIN.value)
    response = admin_client.post(
        _members(organization.id), {"email": other_user.email, "role": Role.ANALYST.value},
        format="json",
    )
    assert response.status_code == 201
    assert Membership.objects.filter(organization=organization, user=other_user).exists()


def test_analyst_cannot_add_member(organization, other_user, make_member):
    _analyst, client = make_member(organization, Role.ANALYST.value)
    response = client.post(
        _members(organization.id), {"email": other_user.email, "role": Role.VIEWER.value},
        format="json",
    )
    assert response.status_code == 403


def test_cannot_remove_last_owner(auth_client, organization, user):
    membership = Membership.objects.get(organization=organization, user=user)
    url = reverse("organization-membership-detail",
                  kwargs={"org_id": organization.id, "membership_id": membership.id})
    assert auth_client.delete(url).status_code == 409


def test_cannot_demote_last_owner(auth_client, organization, user):
    membership = Membership.objects.get(organization=organization, user=user)
    url = reverse("organization-membership-detail",
                  kwargs={"org_id": organization.id, "membership_id": membership.id})
    response = auth_client.patch(url, {"role": Role.ADMIN.value}, format="json")
    assert response.status_code == 409


def test_owner_can_remove_a_second_owner(auth_client, organization, user, make_member):
    second, _ = make_member(organization, Role.OWNER.value, email="second-owner@example.com")
    membership = Membership.objects.get(organization=organization, user=second)
    url = reverse("organization-membership-detail",
                  kwargs={"org_id": organization.id, "membership_id": membership.id})
    assert auth_client.delete(url).status_code == 204
    membership.refresh_from_db()
    assert membership.is_active is False
