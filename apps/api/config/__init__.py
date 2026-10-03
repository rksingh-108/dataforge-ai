"""Django project configuration for the DataForge AI API."""

from .celery import app as celery_app

__all__ = ("celery_app",)
