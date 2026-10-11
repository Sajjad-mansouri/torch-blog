"""
Fixtures specific to blog service tests.

The root conftest and blog/tests/conftest already provide the
Post / Category / Tag / Comment / Like / Bookmark objects these
tests need. This file only adds helpers that are specific to the
service layer.
"""

import pytest


@pytest.fixture
def request_factory():
    """Django RequestFactory, for building request objects cheaply."""
    from django.test import RequestFactory

    return RequestFactory()


@pytest.fixture
def anonymous_request(request_factory):
    """
    A plain WSGIRequest with an AnonymousUser.
    record_view reads request.user, request.META, and (optionally)
    request.session.
    """
    from django.contrib.auth.models import AnonymousUser

    request = request_factory.get("/")
    request.user = AnonymousUser()
    request.META["REMOTE_ADDR"] = "127.0.0.1"
    request.META["HTTP_USER_AGENT"] = "pytest"
    return request


@pytest.fixture
def authed_request(request_factory, test_user):
    """A WSGIRequest authenticated as test_user."""
    request = request_factory.get("/")
    request.user = test_user
    request.META["REMOTE_ADDR"] = "127.0.0.1"
    request.META["HTTP_USER_AGENT"] = "pytest"
    return request
