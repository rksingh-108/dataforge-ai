"""Organization serializers.

Serializers are for shape/validation only. They deliberately contain no
business rules; those live in `services.py`.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.common.rbac import Role, permissions_for
from apps.organizations.models import Membership, Organization


class OrganizationSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "is_active", "role", "member_count", "created_at"]
        read_only_fields = ["id", "slug", "is_active", "created_at"]

    def get_role(self, obj: Organization) -> str | None:
        membership = self.context.get("membership_by_org", {}).get(obj.id)
        return membership.role if membership else None

    def get_member_count(self, obj: Organization) -> int:
        return obj.memberships.filter(is_active=True).count()


class OrganizationCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, trim_whitespace=True)

    def validate_name(self, value: str) -> str:
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Organization name is too short.")
        return value.strip()


class RoleChoiceField(serializers.ChoiceField):
    def __init__(self, **kwargs):
        super().__init__(choices=[r.value for r in Role], **kwargs)


class MembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = [
            "id", "user", "user_email", "user_name",
            "role", "is_active", "permissions", "created_at",
        ]
        read_only_fields = ["id", "user", "user_email", "user_name", "permissions", "created_at"]

    def get_permissions(self, obj: Membership) -> list[str]:
        return sorted(permissions_for(obj.role))


class AddMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = RoleChoiceField()


class ChangeRoleSerializer(serializers.Serializer):
    role = RoleChoiceField()
