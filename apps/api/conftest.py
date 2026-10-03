"""Shared pytest fixtures.

Fixtures build real objects through the ORM so tests exercise the same code paths
production does. Authentication uses *real* JWTs (not `force_authenticate`) so the
token pipeline is covered.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.rbac import Role
from apps.organizations.models import Membership, Organization

User = get_user_model()


@pytest.fixture(autouse=True)
def _media_root(tmp_path, settings):
    """Keep uploaded files out of the repository during tests."""
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="owner@example.com", password="CorrectHorse9!", full_name="Olivia Owner")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(email="rival@example.com", password="CorrectHorse9!", full_name="Rita Rival")


@pytest.fixture
def organization(db, user):
    org = Organization.objects.create(name="Acme Corp", slug="acme", created_by=user)
    Membership.objects.create(organization=org, user=user, role=Role.OWNER.value)
    return org


def _client_for(user) -> APIClient:
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


@pytest.fixture
def client_for() -> callable:
    """Return a factory that builds an authenticated client for any user."""
    return _client_for


@pytest.fixture
def auth_client(user, organization) -> APIClient:
    """Client authenticated as the organization owner."""
    return _client_for(user)


@pytest.fixture
def make_member(db):
    """Create a user with a given role in an organization and return (user, client)."""

    def _make(organization, role: str, email: str | None = None):
        email = email or f"{role}@example.com"
        member = User.objects.create_user(email=email, password="CorrectHorse9!", full_name=role.title())
        Membership.objects.create(organization=organization, user=member, role=role)
        return member, _client_for(member)

    return _make


@pytest.fixture
def text_file() -> SimpleUploadedFile:
    return SimpleUploadedFile("notes.txt", b"DataForge AI test document.\n" * 5, content_type="text/plain")


@pytest.fixture
def pdf_file() -> SimpleUploadedFile:
    return SimpleUploadedFile("report.pdf", b"%PDF-1.4 fake pdf body", content_type="application/pdf")
