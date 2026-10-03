"""Document endpoints."""
from __future__ import annotations

from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import NotFound
from apps.common.permissions import require_organization, require_permission
from apps.common.rbac import Permission
from apps.documents import selectors, services
from apps.documents.serializers import DocumentSerializer, DocumentUploadSerializer


def _get_document_or_404(request, document_id):
    document = selectors.get_document(
        organization_id=require_organization(request).id, document_id=document_id
    )
    if document is None:
        raise NotFound("Document not found.")
    return document


class DocumentListCreateView(generics.ListCreateAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [require_permission(Permission.DOCUMENT_VIEW)]
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method == "POST":
            return [require_permission(Permission.DOCUMENT_MANAGE)()]
        return super().get_permissions()

    def get_queryset(self):
        # Scope comes from the verified membership, never the raw URL/query value.
        return selectors.list_documents(
            organization_id=require_organization(self.request).id,
            status=self.request.query_params.get("status"),
        )

    def create(self, request, *args, **kwargs):
        payload = DocumentUploadSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        document = services.create_document(
            organization=request.membership.organization,
            actor=request.user,
            uploaded_file=payload.validated_data["file"],
            title=payload.validated_data.get("title", ""),
        )
        services.enqueue_processing(document=document)
        return Response(DocumentSerializer(document).data, status=status.HTTP_201_CREATED)


class DocumentDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [require_permission(Permission.DOCUMENT_MANAGE)]
    http_method_names = ["get", "delete"]

    def get_permissions(self):
        if self.request.method == "GET":
            return [require_permission(Permission.DOCUMENT_VIEW)()]
        return super().get_permissions()

    def get_object(self):
        return _get_document_or_404(self.request, self.kwargs["document_id"])

    def destroy(self, request, *args, **kwargs):
        services.delete_document(document=self.get_object(), actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DocumentReprocessView(APIView):
    permission_classes = [require_permission(Permission.DOCUMENT_MANAGE)]

    def post(self, request, org_id, document_id):
        document = _get_document_or_404(request, document_id)
        services.enqueue_processing(document=document)
        document.refresh_from_db()
        return Response(DocumentSerializer(document).data, status=status.HTTP_202_ACCEPTED)
