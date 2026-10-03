"""Root URL configuration for the DataForge AI API."""
from django.contrib import admin
from django.urls import include, path

from apps.common.health import health_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("_health/", health_view, name="health"),
    # Public, versioned product API.
    path("api/v1/", include("config.api_urls")),
    # Service-to-service endpoints. Not part of the public API surface.
    path("internal/", include("apps.ai_bridge.internal_urls")),
]
