from django.urls import re_path

from apps.realtime.consumers import ExecutionConsumer

websocket_urlpatterns = [
    re_path(r"^ws/orgs/(?P<org_id>[0-9a-fA-F-]{36})/executions/$", ExecutionConsumer.as_asgi()),
]
