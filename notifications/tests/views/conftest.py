"""
Fixtures for notifications view/API tests.

Throttling is disabled for tests in this directory.
"""

import pytest
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
def disable_throttling():
    with override_settings(REST_FRAMEWORK=_REST_FRAMEWORK_WITHOUT_THROTTLING):
        yield


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(test_user):
    client = APIClient()
    client.force_authenticate(user=test_user)
    return client


@pytest.fixture
def other_author_client(test_other_author):
    client = APIClient()
    client.force_authenticate(user=test_other_author)
    return client
