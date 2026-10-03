"""Production settings: fails fast on unsafe configuration."""
from .base import *  # noqa: F403
from .base import SECRET_KEY, env_bool, env_list

DEBUG = False

# Refuse to boot with an obviously unsafe secret.
if len(SECRET_KEY) < 40:
    raise RuntimeError("DJANGO_SECRET_KEY must be at least 40 characters in production.")

# Refuse to boot without the credential-encryption key.
if not DATAFORGE_FERNET_KEY:  # noqa: F405
    raise RuntimeError("DATAFORGE_FERNET_KEY must be set in production.")

# Refuse to boot without an internal service token.
if len(INTERNAL_SERVICE_TOKEN) < 32:  # noqa: F405
    raise RuntimeError("INTERNAL_SERVICE_TOKEN must be at least 32 characters.")

# --- Transport security -----------------------------------------------------
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"

# Trusted origins must be explicit in production (no implicit localhost).
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "")
if not CSRF_TRUSTED_ORIGINS:
    raise RuntimeError("CSRF_TRUSTED_ORIGINS must list the public web origin(s) in production.")

# The browsable API is disabled in production (JSON only, as configured in base).
assert "rest_framework.renderers.BrowsableAPIRenderer" not in REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"]  # noqa: F405
