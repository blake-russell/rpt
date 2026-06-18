"""
Minimal test settings for CI — inherits from settings.py and overrides for testing.
Uses in-memory SQLite so no db.sqlite3 is created/modified during test runs.
"""

from . import settings as base_settings
from .settings import *  # noqa: F401, F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Faster password hashing in tests
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Disable CSRF in tests
MIDDLEWARE = [middleware for middleware in base_settings.MIDDLEWARE if "Csrf" not in middleware]
