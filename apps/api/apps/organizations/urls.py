from django.urls import path

from apps.organizations.views import (
    MembershipDetailView,
    OrganizationDetailView,
    OrganizationListCreateView,
    OrganizationMembersView,
)

urlpatterns = [
    path("", OrganizationListCreateView.as_view(), name="organization-list"),
    path("<uuid:org_id>/", OrganizationDetailView.as_view(), name="organization-detail"),
    path("<uuid:org_id>/members/", OrganizationMembersView.as_view(), name="organization-members"),
    path(
        "<uuid:org_id>/members/<uuid:membership_id>/",
        MembershipDetailView.as_view(),
        name="organization-membership-detail",
    ),
]
