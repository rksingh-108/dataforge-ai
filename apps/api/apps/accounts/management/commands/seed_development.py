"""Seed a development organization and users.

Idempotent: running it twice changes nothing. Refuses to run when DEBUG is off,
so it can never accidentally populate a production database.

    python manage.py seed_development
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.common.rbac import Role
from apps.organizations.models import Membership, Organization

User = get_user_model()

# Development-only accounts. These credentials are intentionally public: they are
# never created outside a DEBUG environment.
SEED_USERS = [
    ("owner@dataforge.local", "Olive Owner", Role.OWNER.value),
    ("admin@dataforge.local", "Adam Admin", Role.ADMIN.value),
    ("analyst@dataforge.local", "Ana Analyst", Role.ANALYST.value),
    ("viewer@dataforge.local", "Vic Viewer", Role.VIEWER.value),
]

DEMO_PASSWORD = "DataForge!Dev1"
ORG_NAME = "DataForge Demo Organization"
ORG_SLUG = "dataforge-demo"


class Command(BaseCommand):
    help = "Create a development organization with one user per role."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--password",
            default=DEMO_PASSWORD,
            help="Password to set for every seeded account (development only).",
        )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        if not settings.DEBUG:
            raise CommandError(
                "seed_development refuses to run with DEBUG=False. "
                "It creates accounts with a known password."
            )

        organization, created = Organization.objects.get_or_create(
            slug=ORG_SLUG,
            defaults={"name": ORG_NAME, "is_active": True},
        )
        self.stdout.write(
            self.style.SUCCESS(f"{'Created' if created else 'Found'} organization {organization.slug}")
        )

        for email, full_name, role in SEED_USERS:
            user, user_created = User.objects.get_or_create(
                email=email, defaults={"full_name": full_name, "is_active": True}
            )
            if user_created:
                user.set_password(options["password"])
                user.save(update_fields=["password"])

            membership, membership_created = Membership.objects.get_or_create(
                organization=organization,
                user=user,
                defaults={"role": role, "is_active": True},
            )
            if not membership_created and membership.role != role:
                membership.role = role
                membership.save(update_fields=["role", "updated_at"])

            state = "created" if user_created else "exists"
            self.stdout.write(f"  {email:<28} {role:<8} ({state})")

        organization.created_by = organization.created_by or User.objects.get(email=SEED_USERS[0][0])
        organization.save(update_fields=["created_by"])

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSign in at http://localhost:3000/login with any seeded email and password: "
                f"{options['password']}"
            )
        )
