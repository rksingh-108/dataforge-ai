"""Authentication endpoints.

Login is throttled (``auth`` scope), returns a short-lived access token and a
rotating refresh token, and is recorded in the audit log (both success and
failure, though failures cannot be attributed to an organization).
"""
from __future__ import annotations

import contextlib
import logging

from django.contrib.auth import authenticate, get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.serializers import (
    CurrentUserSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordChangeSerializer,
    UserSerializer,
)
from apps.analytics.services import record_audit
from apps.common.rbac import permissions_for

logger = logging.getLogger("apps.security.auth")
User = get_user_model()


def _membership_summaries(user) -> list[dict]:
    summaries = []
    memberships = user.memberships.select_related("organization").filter(
        is_active=True, organization__is_active=True
    )
    for membership in memberships:
        summaries.append(
            {
                "organization_id": membership.organization_id,
                "organization_name": membership.organization.name,
                "organization_slug": membership.organization.slug,
                "role": membership.role,
                "permissions": sorted(permissions_for(membership.role)),
            }
        )
    return summaries


class LoginView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    throttle_scope = "auth"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        user = authenticate(
            request, username=email, password=serializer.validated_data["password"]
        )
        if user is None or not user.is_active:
            # Log the attempt without disclosing which part was wrong.
            logger.warning("Failed login attempt for %s", email)
            record_audit(
                organization=None,
                actor=None,
                action="auth.login_failed",
                target_type="user",
                target_id=None,
                metadata={"email_domain": email.split("@")[-1]},
            )
            return Response(
                {"error": {"code": "invalid_credentials",
                           "message": "Invalid email or password.", "details": {}}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)
        record_audit(
            organization=None, actor=user, action="auth.login",
            target_type="user", target_id=str(user.id), metadata={},
        )
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
                "memberships": _membership_summaries(user),
            }
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Already invalid/expired: logout is idempotent.
        with contextlib.suppress(TokenError):
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        record_audit(
            organization=None, actor=request.user, action="auth.logout",
            target_type="user", target_id=str(request.user.id), metadata={},
        )
        return Response(status=status.HTTP_205_RESET_CONTENT)


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        # Invalidate every outstanding refresh token for this user.
        revoked = _revoke_all_refresh_tokens(user)
        record_audit(
            organization=None, actor=user, action="auth.password_changed",
            target_type="user", target_id=str(user.id),
            metadata={"refresh_tokens_revoked": revoked},
        )
        return Response({"revoked_refresh_tokens": revoked})


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payload = {
            "user": UserSerializer(request.user).data,
            "memberships": _membership_summaries(request.user),
            "is_staff": request.user.is_staff,
        }
        return Response(CurrentUserSerializer(payload).data)


def _revoke_all_refresh_tokens(user) -> int:
    from rest_framework_simplejwt.token_blacklist.models import (
        BlacklistedToken,
        OutstandingToken,
    )

    count = 0
    for token in OutstandingToken.objects.filter(user=user):
        _, created = BlacklistedToken.objects.get_or_create(token=token)
        if created:
            count += 1
    return count
