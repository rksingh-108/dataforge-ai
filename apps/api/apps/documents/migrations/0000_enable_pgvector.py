"""Enable the `vector` extension.

This must run before any `VectorField` column or HNSW index is created, so the
document migrations depend on it explicitly.
"""
from django.db import migrations
from pgvector.django import VectorExtension


class Migration(migrations.Migration):
    initial = False

    dependencies = [
        ("organizations", "0001_initial"),
    ]

    operations = [
        VectorExtension(),
    ]
