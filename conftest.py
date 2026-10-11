"""
Project-wide test fixtures.

pytest only auto-loads a conftest.py for tests located at or below
its own directory. Fixtures that must be available across multiple
apps therefore live here, at the project root.

Sections:
- Media isolation
- Accounts: users
- Accounts: image helper
- Accounts: api request
- Blog / interactions: Category, Tag, Post
- Blog / interactions: Like, Comment, Bookmark
"""

from datetime import timedelta
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from django.utils import timezone
from PIL import Image

from accounts.models import User
from blog.models import Category, Post, Tag
from interactions.models import Bookmark, Comment, Like


# ==================================================================
# Media isolation
# ==================================================================
@pytest.fixture
def media_root(tmp_path, settings):
    """
    Redirect MEDIA_ROOT to a per-test temporary directory.

    tmp_path is a pytest builtin: unique per test, auto-cleaned.
    We do not make this autouse so pure-function tests stay fast.
    Upload tests must request it explicitly.
    """
    settings.MEDIA_ROOT = str(tmp_path)
    yield tmp_path


# ==================================================================
# Accounts: users
# ==================================================================
@pytest.fixture
def test_user(db):
    """Default reader user with a usable password."""
    return User.objects.create_user(
        username="test_reader",
        email="reader@example.com",
        password="testpass123",
    )


@pytest.fixture
def test_author(db):
    """A user with the author role."""
    return User.objects.create_user(
        username="test_author",
        email="author@example.com",
        password="testpass123",
        role=User.Role.AUTHOR,
    )


@pytest.fixture
def test_editor(db):
    """A user with the editor role."""
    return User.objects.create_user(
        username="test_editor",
        email="editor@example.com",
        password="testpass123",
        role=User.Role.EDITOR,
    )


@pytest.fixture
def test_other_author(db):
    """A second author, for cross-author filter tests."""
    return User.objects.create_user(
        username="other_author",
        email="other_author@example.com",
        password="testpass123",
        role=User.Role.AUTHOR,
    )


# ==================================================================
# Accounts: image helper
# ==================================================================
@pytest.fixture
def test_image():
    """A small valid PNG, as a SimpleUploadedFile."""
    buf = BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buf, format="PNG")
    buf.seek(0)
    return SimpleUploadedFile(
        name="test-avatar.png",
        content=buf.read(),
        content_type="image/png",
    )


# ==================================================================
# Accounts: request helpers
# ==================================================================
@pytest.fixture
def rf():
    """Django RequestFactory for building request objects cheaply."""
    return RequestFactory()


@pytest.fixture
def api_request(rf):
    """
    A request object suitable for serializers that call
    request.build_absolute_uri / request.is_secure / get_current_site.

    django.contrib.sites is not in INSTALLED_APPS, so get_current_site
    falls back to RequestSite(request), using the request's Host header.
    """
    request = rf.get("/api/v1/auth/me/")
    request.META["HTTP_HOST"] = "testserver"
    return request


# ==================================================================
# Blog / interactions: Category, Tag, Post
# ==================================================================
@pytest.fixture
def test_category(db):
    return Category.objects.create(
        name="Testing",
        description="Posts about testing.",
    )


@pytest.fixture
def test_tag(db):
    return Tag.objects.create(name="pytest")


@pytest.fixture
def test_published_post(db, test_author, test_category):
    """A published post. published_at is in the past."""
    return Post.objects.create(
        author=test_author,
        title="A Published Post",
        summary="Summary of a published post.",
        body="<p>Body of a published post.</p>",
        category=test_category,
        status=Post.Status.PUBLISHED,
        published_at=timezone.now() - timedelta(hours=1),
    )


@pytest.fixture
def test_second_published_post(db, test_author, test_category):
    return Post.objects.create(
        author=test_author,
        title="Another Published Post",
        summary="Summary of another published post.",
        body="<p>Body of another published post.</p>",
        category=test_category,
        status=Post.Status.PUBLISHED,
        published_at=timezone.now() - timedelta(minutes=30),
    )


@pytest.fixture
def test_draft_post(db, test_author, test_category):
    return Post.objects.create(
        author=test_author,
        title="A Draft Post",
        summary="Summary of a draft.",
        body="<p>Body of a draft.</p>",
        category=test_category,
        status=Post.Status.DRAFT,
    )


@pytest.fixture
def test_scheduled_future_post(db, test_author, test_category):
    """Status=published but published_at in the future."""
    return Post.objects.create(
        author=test_author,
        title="A Future Post",
        summary="Scheduled for later.",
        body="<p>Not yet live.</p>",
        category=test_category,
        status=Post.Status.PUBLISHED,
        published_at=timezone.now() + timedelta(days=1),
    )


@pytest.fixture
def test_soft_deleted_post(db, test_author, test_category):
    """Status=published but is_deleted=True."""
    return Post.objects.create(
        author=test_author,
        title="A Soft-Deleted Post",
        summary="Deleted but still in the table.",
        body="<p>Should not appear.</p>",
        category=test_category,
        status=Post.Status.PUBLISHED,
        published_at=timezone.now() - timedelta(hours=2),
        is_deleted=True,
    )


@pytest.fixture
def test_other_authors_post(db, test_other_author, test_category):
    return Post.objects.create(
        author=test_other_author,
        title="Someone Else's Post",
        summary="Belongs to a different author.",
        body="<p>Not ours.</p>",
        category=test_category,
        status=Post.Status.PUBLISHED,
        published_at=timezone.now() - timedelta(hours=3),
    )


# ==================================================================
# Interactions: like, comment, bookmark
# ==================================================================
@pytest.fixture
def test_like(db, test_user, test_published_post):
    return Like.objects.create(user=test_user, post=test_published_post)


@pytest.fixture
def test_approved_comment(db, test_user, test_published_post):
    return Comment.objects.create(
        post=test_published_post,
        author=test_user,
        body="An approved comment.",
        status=Comment.Status.APPROVED,
        is_deleted=False,
    )


@pytest.fixture
def test_pending_comment(db, test_user, test_published_post):
    return Comment.objects.create(
        post=test_published_post,
        author=test_user,
        body="Awaiting moderation.",
        status=Comment.Status.PENDING,
        is_deleted=False,
    )


@pytest.fixture
def test_soft_deleted_comment(db, test_user, test_published_post):
    return Comment.objects.create(
        post=test_published_post,
        author=test_user,
        body="Removed.",
        status=Comment.Status.APPROVED,
        is_deleted=True,
    )


@pytest.fixture
def test_bookmark(db, test_user, test_published_post):
    return Bookmark.objects.create(user=test_user, post=test_published_post)
