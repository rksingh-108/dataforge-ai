"""pgvector retrieval tests.

These run against real Postgres + pgvector. They assert that retrieval ranks by
cosine distance and — critically — that it never crosses a tenant boundary.
"""
from __future__ import annotations

import pytest

from apps.common.rbac import Role
from apps.documents.models import Document, DocumentChunk, DocumentStatus
from apps.documents.selectors import search_chunks
from apps.organizations.models import Membership, Organization

pytestmark = [pytest.mark.django_db, pytest.mark.requires_postgres]

DIM = 1536


def _vec(axis: int, value: float = 1.0) -> list[float]:
    vec = [0.0] * DIM
    vec[axis] = value
    return vec


def _document(organization, user, title: str) -> Document:
    return Document.objects.create(
        organization=organization,
        title=title,
        original_filename=f"{title}.txt",
        content_type="text/plain",
        size_bytes=10,
        status=DocumentStatus.READY,
        uploaded_by=user,
    )


def _chunk(document, index: int, content: str, embedding: list[float]) -> DocumentChunk:
    return DocumentChunk.objects.create(
        document=document,
        organization=document.organization,
        chunk_index=index,
        content=content,
        char_count=len(content),
        embedding=embedding,
    )


def test_search_returns_nearest_chunk_first(organization, user):
    document = _document(organization, user, "handbook")
    _chunk(document, 0, "about holidays", _vec(0))
    _chunk(document, 1, "about payroll", _vec(1))
    _chunk(document, 2, "about laptops", _vec(2))

    results = search_chunks(organization_id=organization.id, embedding=_vec(0), top_k=2)

    assert results[0]["content"] == "about holidays"
    assert results[0]["similarity"] == pytest.approx(1.0, abs=1e-3)
    assert results[0]["document_title"] == "handbook"
    assert len(results) == 2


def test_search_is_tenant_scoped(organization, user, other_user):
    mine = _document(organization, user, "mine")
    _chunk(mine, 0, "my secret chunk", _vec(0))

    foreign_org = Organization.objects.create(name="Globex", slug="globex", created_by=other_user)
    Membership.objects.create(organization=foreign_org, user=other_user, role=Role.OWNER.value)
    foreign = _document(foreign_org, other_user, "theirs")
    _chunk(foreign, 0, "their secret chunk", _vec(0))

    results = search_chunks(organization_id=organization.id, embedding=_vec(0), top_k=10)

    assert [r["content"] for r in results] == ["my secret chunk"]


def test_search_ignores_documents_that_are_not_ready(organization, user):
    document = _document(organization, user, "pending")
    document.status = DocumentStatus.PROCESSING
    document.save(update_fields=["status"])
    _chunk(document, 0, "still processing", _vec(0))

    assert search_chunks(organization_id=organization.id, embedding=_vec(0), top_k=5) == []
