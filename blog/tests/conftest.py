"""
Fixtures specific to the blog app's test suite.

Cross-app fixtures (users, categories, base posts, comments, likes,
bookmarks) live in the project-root conftest.py and are discovered
upward. This file adds blog-specific fixtures that are only meaningful
to blog tests.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from blog.models import Category, Post, PostRevision, PostView

# ------------------------------------------------------------------
# Category tree
# ------------------------------------------------------------------


@pytest.fixture
def test_inactive_category(db):
    return Category.objects.create(
        name="Archived Category",
        description="Not active.",
        is_active=False,
    )


# ------------------------------------------------------------------
# Tags
# ------------------------------------------------------------------


@pytest.fixture
def test_post_with_tags(db, test_author, test_category, test_tag, test_second_tag):
    """A published post with two tags attached."""
    post = Post.objects.create(
        author=test_author,
        title="A Tagged Post",
        summary="Post with tags.",
        body="<p>Body of a tagged post.</p>",
        category=test_category,
        status=Post.Status.PUBLISHED,
        published_at=timezone.now() - timedelta(hours=4),
    )
    post.tags.set([test_tag, test_second_tag])
    return post


@pytest.fixture
def test_post_by_other_author(db, test_other_author, test_category):
    """A draft owned by test_other_author, for ownership tests."""
    return Post.objects.create(
        author=test_other_author,
        title="Another Author's Draft",
        summary="Someone else's draft.",
        body="<p>Not ours.</p>",
        category=test_category,
        status=Post.Status.DRAFT,
    )


# ------------------------------------------------------------------
# Post views (for record_view dedup tests)
# ------------------------------------------------------------------
@pytest.fixture
def test_post_view(db, test_published_post, test_user):
    return PostView.objects.create(
        post=test_published_post,
        user=test_user,
        ip_address="127.0.0.1",
        user_agent="pytest",
    )


# ------------------------------------------------------------------
# Post revisions
# ------------------------------------------------------------------
@pytest.fixture
def test_post_revision(db, test_published_post, test_author):
    return PostRevision.create_for_post(
        post=test_published_post,
        user=test_author,
        change_note="initial",
    )
