"""
Fixtures for editor view/API tests.

Throttling is disabled. Authenticated clients for editor and other
roles are provided. The cache is cleared before every test so that
cached objects (SiteSettings) do not leak between tests.
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


@pytest.fixture
def editor_client(test_editor):
    client = APIClient()
    client.force_authenticate(user=test_editor)
    return client


@pytest.fixture
def author_client(test_author):
    client = APIClient()
    client.force_authenticate(user=test_author)
    return client


@pytest.fixture
def auth_client(test_user):
    client = APIClient()
    client.force_authenticate(user=test_user)
    return client
