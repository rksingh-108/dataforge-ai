"""Document upload, validation and RAG-processing tests.

The embedding/LLM provider is the only thing faked here (it is a third-party
network call); extraction → chunk persistence → status transitions run for real.
"""
from __future__ import annotations

from unittest import mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.common.rbac import Role
from apps.documents.models import Document, DocumentChunk, DocumentStatus

pytestmark = pytest.mark.django_db


def _list(org_id):
    return reverse("document-list", kwargs={"org_id": org_id})


def _embedding(seed: float = 0.1) -> list[float]:
    return [seed] * 1536


def _ai_result(chunks: int = 3) -> dict:
    return {
        "page_count": 1,
        "chunk_count": chunks,
        "chunks": [
            {
                "index": i,
                "content": f"chunk number {i}",
                "source_label": f"page-{i + 1}",
                "embedding": _embedding(0.1 + i * 0.01),
                "metadata": {},
            }
            for i in range(chunks)
        ],
    }


def test_upload_rejects_disallowed_extension(auth_client, organization):
    upload = SimpleUploadedFile("payload.exe", b"MZ\x90\x00", content_type="application/octet-stream")
    response = auth_client.post(_list(organization.id), {"file": upload}, format="multipart")
    assert response.status_code == 400


def test_upload_rejects_magic_byte_mismatch(auth_client, organization):
    # Declares PDF but the body is not a PDF.
    upload = SimpleUploadedFile("fake.pdf", b"clearly not a pdf", content_type="application/pdf")
    response = auth_client.post(_list(organization.id), {"file": upload}, format="multipart")
    assert response.status_code == 400


def test_upload_rejects_duplicate_content(auth_client, organization):
    body = b"DataForge AI test document.\n" * 5
    first_upload = SimpleUploadedFile("notes.txt", body, content_type="text/plain")
    again = SimpleUploadedFile("copy.txt", body, content_type="text/plain")

    with mock.patch("apps.documents.services.enqueue_processing"):
        assert auth_client.post(
            _list(organization.id), {"file": first_upload}, format="multipart"
        ).status_code == 201
        second = auth_client.post(_list(organization.id), {"file": again}, format="multipart")
    assert second.status_code == 409


def test_upload_runs_rag_pipeline(auth_client, organization, text_file):
    with mock.patch("apps.documents.tasks.AIServiceClient") as client_cls:
        client_cls.return_value.process_document.return_value = _ai_result(3)
        response = auth_client.post(_list(organization.id), {"file": text_file},
                                    format="multipart")

    assert response.status_code == 201
    document = Document.objects.get(id=response.json()["id"])
    assert document.status == DocumentStatus.READY
    assert document.chunk_count == 3
    assert DocumentChunk.objects.filter(document=document).count() == 3
    # Every chunk is tenant-scoped to the owning organization.
    assert set(
        DocumentChunk.objects.filter(document=document).values_list("organization_id", flat=True)
    ) == {organization.id}


def test_processing_failure_marks_document_failed(auth_client, organization, text_file):
    with mock.patch("apps.documents.tasks.AIServiceClient") as client_cls:
        client_cls.return_value.process_document.side_effect = Exception("provider exploded")
        auth_client.post(_list(organization.id), {"file": text_file}, format="multipart")

    document = Document.objects.get(organization=organization)
    assert document.status == DocumentStatus.FAILED
    assert "provider exploded" in document.error


def test_viewer_cannot_upload(organization, make_member, text_file):
    _viewer, client = make_member(organization, Role.VIEWER.value)
    response = client.post(_list(organization.id), {"file": text_file}, format="multipart")
    assert response.status_code == 403


def test_documents_are_tenant_isolated(auth_client, organization, other_user, client_for, text_file):
    from apps.organizations.models import Membership, Organization

    foreign = Organization.objects.create(name="Globex", slug="globex", created_by=other_user)
    Membership.objects.create(organization=foreign, user=other_user, role=Role.OWNER.value)
    rival = client_for(other_user)

    with mock.patch("apps.documents.services.enqueue_processing"):
        auth_client.post(_list(organization.id), {"file": text_file}, format="multipart")

    assert rival.get(_list(foreign.id)).json()["count"] == 0
