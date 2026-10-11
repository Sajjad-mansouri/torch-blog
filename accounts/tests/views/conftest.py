"""
Fixtures for accounts view/API tests.

- Authenticated API clients for reader, author, and editor.
- A throttle override that disables DRF's default throttling for
  the duration of each test in this directory, so that rapid
  anonymous requests don't trip the anon rate limit and produce
  misleading 429s.

Tests that specifically exercise throttling (see
TestResendVerificationThrottle) must request the throttle explicitly
by re-enabling it via override_settings inside the test, which
takes precedence over this fixture.
"""

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

# The full REST_FRAMEWORK dict is required: override_settings
# replaces the whole setting, it does not merge.
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
    """
    Autouse within accounts/tests/views/ only.

    Without this, the anon/user rate limits in DEFAULT_THROTTLE_RATES
    will fire during the run and 429 responses will be indistinguishable
    from real bugs.
    """
    with override_settings(REST_FRAMEWORK=_REST_FRAMEWORK_WITHOUT_THROTTLING):
        yield


@pytest.fixture
def api_client():
    """An anonymous DRF APIClient."""
    return APIClient()


@pytest.fixture
def auth_client(test_user):
    """DRF APIClient authenticated as a reader (test_user)."""
    client = APIClient()
    client.force_authenticate(user=test_user)
    return client


@pytest.fixture
def author_client(test_author):
    """DRF APIClient authenticated as an author (test_author)."""
    client = APIClient()
    client.force_authenticate(user=test_author)
    return client


@pytest.fixture
def editor_client(test_editor):
    """DRF APIClient authenticated as an editor (test_editor)."""
    client = APIClient()
    client.force_authenticate(user=test_editor)
    return client
