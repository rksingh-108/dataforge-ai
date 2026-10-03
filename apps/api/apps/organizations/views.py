"""Organization and membership endpoints.

Thin views: resolve authorization (via permission classes), delegate to
selectors for reads and services for writes, and let serializers shape output.
"""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import (
    HasOrganizationPermission,
    IsOrganizationMember,
    require_organization,
    require_permission,
)
from apps.common.rbac import Permission
from apps.organizations import selectors, services
from apps.organizations.models import Membership, Organization
from apps.organizations.serializers import (
    AddMemberSerializer,
    ChangeRoleSerializer,
    MembershipSerializer,
    OrganizationCreateSerializer,
    OrganizationSerializer,
)


class OrganizationListCreateView(generics.ListCreateAPIView):
    """`GET /api/v1/orgs/` lists my organizations; `POST` creates one."""

    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationSerializer
    pagination_class = None

    def get_queryset(self):
        return selectors.list_organizations_for_user(user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        memberships = Membership.objects.filter(
            user=self.request.user, is_active=True
        ).select_related("organization")
        context["membership_by_org"] = {m.organization_id: m for m in memberships}
        return context

    def create(self, request, *args, **kwargs):
        payload = OrganizationCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        organization = services.create_organization(
            name=payload.validated_data["name"], actor=request.user
        )
        data = OrganizationSerializer(organization).data
        data["role"] = "owner"
        return Response(data, status=status.HTTP_201_CREATED)


class OrganizationDetailView(generics.RetrieveAPIView):
    permission_classes = [IsOrganizationMember]
    serializer_class = OrganizationSerializer

    def get_object(self) -> Organization:
        # The verified organization (membership already checked by the permission
        # class) — not the raw URL id.
        organization = require_organization(self.request)
        self.request.organization = organization
        return organization

    def get_serializer_context(self):
        context = super().get_serializer_context()
        membership = getattr(self.request, "membership", None)
        context["membership_by_org"] = (
            {membership.organization_id: membership} if membership else {}
        )
        return context


class OrganizationMembersView(generics.ListCreateAPIView):
    """Members of an organization. Reading requires membership, writing requires
    `member.manage`."""

    permission_classes = [IsOrganizationMember]
    serializer_class = MembershipSerializer
    pagination_class = None

    def get_permissions(self):
        if self.request.method == "POST":
            return [require_permission(Permission.MEMBER_MANAGE)()]
        return super().get_permissions()

    def get_queryset(self):
        return selectors.list_memberships(organization_id=require_organization(self.request).id)

    def create(self, request, *args, **kwargs):
        payload = AddMemberSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        organization = require_organization(request)
        membership = services.add_member(
            organization=organization,
            actor=request.user,
            email=payload.validated_data["email"],
            role=payload.validated_data["role"],
        )
        return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


class MembershipDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [require_permission(Permission.MEMBER_MANAGE)]
    serializer_class = MembershipSerializer
    http_method_names = ["get", "patch", "delete"]

    def get_object(self) -> Membership:
        return get_object_or_404(
            Membership,
            id=self.kwargs["membership_id"],
            organization_id=require_organization(self.request).id,
        )

    def update(self, request, *args, **kwargs):
        payload = ChangeRoleSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        membership = services.change_role(
            organization=self.request.membership.organization,
            actor=request.user,
            membership=self.get_object(),
            role=payload.validated_data["role"],
        )
        return Response(MembershipSerializer(membership).data)

    def destroy(self, request, *args, **kwargs):
        services.remove_member(
            organization=self.request.membership.organization,
            actor=request.user,
            membership=self.get_object(),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


__all__ = [
    "HasOrganizationPermission",
    "MembershipDetailView",
    "OrganizationDetailView",
    "OrganizationListCreateView",
    "OrganizationMembersView",
]
