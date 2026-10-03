from django.urls import path

from apps.ai_bridge.views import AnalystQueryView

urlpatterns = [
    path("query/", AnalystQueryView.as_view(), name="analyst-query"),
]
