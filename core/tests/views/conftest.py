"""
Fixtures for core view tests.

Throttling is disabled by default so rapid anonymous requests don't
trip DRF's anon rate limit. Tests that exercise the ContactThrottle
re-enable it explicitly.
"""

import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

_REST_FRAMEWORK_WITHOUT_THROTTLING = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}


@pytest.fixture(autouse=True)
def disable_throttling_and_clear_cache():
    cache.clear()
    with override_settings(REST_FRAMEWORK=_REST_FRAMEWORK_WITHOUT_THROTTLING):
        yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()
