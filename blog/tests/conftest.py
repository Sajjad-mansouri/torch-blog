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

from blog.models import Category, Post, PostRevision, PostView, Tag
from interactions.models import Comment, CommentLike


# ------------------------------------------------------------------
# Category tree
# ------------------------------------------------------------------
@pytest.fixture
def test_child_category(db, test_category):
    """A child of test_category, for parent/children and descendant tests."""
    return Category.objects.create(
        name="Child Testing",
        description="A child category.",
        parent=test_category,
    )


@pytest.fixture
def test_second_category(db):
    return Category.objects.create(
        name="Engineering",
        description="Engineering posts.",
    )


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
def test_second_tag(db):
    return Tag.objects.create(name="django")


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


# ------------------------------------------------------------------
# Posts in various states
# ------------------------------------------------------------------
@pytest.fixture
def test_pending_post(db, test_author, test_category):
    return Post.objects.create(
        author=test_author,
        title="A Pending Post",
        summary="Awaiting review.",
        body="<p>Body of a pending post.</p>",
        category=test_category,
        status=Post.Status.PENDING,
    )


@pytest.fixture
def test_rejected_post(db, test_author, test_category):
    return Post.objects.create(
        author=test_author,
        title="A Rejected Post",
        summary="Rejected by an editor.",
        body="<p>Body of a rejected post.</p>",
        category=test_category,
        status=Post.Status.REJECTED,
        rejection_reason="Not on topic.",
    )


@pytest.fixture
def test_changes_requested_post(db, test_author, test_category):
    return Post.objects.create(
        author=test_author,
        title="A Post Needing Changes",
        summary="Editor requested changes.",
        body="<p>Body of a post needing changes.</p>",
        category=test_category,
        status=Post.Status.CHANGES_REQUESTED,
        changes_requested_note="Please tighten the introduction.",
    )


@pytest.fixture
def test_featured_post(db, test_author, test_category):
    return Post.objects.create(
        author=test_author,
        title="A Featured Post",
        summary="Featured on the home page.",
        body="<p>Body of a featured post.</p>",
        category=test_category,
        status=Post.Status.PUBLISHED,
        published_at=timezone.now() - timedelta(hours=5),
        is_featured=True,
        featured_order=1,
    )


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
# Comments (reply and likes)
# ------------------------------------------------------------------
@pytest.fixture
def test_comment_reply(db, test_user, test_published_post, test_approved_comment):
    """A reply to an approved top-level comment."""
    return Comment.objects.create(
        post=test_published_post,
        author=test_user,
        parent=test_approved_comment,
        body="A reply to the top-level comment.",
        status=Comment.Status.APPROVED,
        is_deleted=False,
    )


@pytest.fixture
def test_like_on_comment(db, test_user, test_approved_comment):
    return CommentLike.objects.create(
        user=test_user,
        comment=test_approved_comment,
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
