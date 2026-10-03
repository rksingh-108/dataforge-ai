"""Development settings: convenient defaults, never used in production."""
from .base import *  # noqa: F403
from .base import env

DEBUG = True
ALLOWED_HOSTS = ["*"]

# The browsable API is a real productivity tool locally; it is disabled in prod.
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_RENDERER_CLASSES": (  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
)}

# Local development is over plain HTTP; production enforces TLS-only cookies.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

CSRF_TRUSTED_ORIGINS = [
    *CSRF_TRUSTED_ORIGINS,  # noqa: F405
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

LOG_LEVEL = env("LOG_LEVEL", "DEBUG")
LOGGING["root"]["level"] = LOG_LEVEL  # type: ignore[index]  # noqa: F405
