"""
Fixtures specific to the interactions app tests.

Cross-app fixtures (users, posts, comments, likes) live in the
project-root conftest.py and are discovered upward. This file adds
fixtures that are only meaningful to interactions tests.
"""

import pytest

from interactions.models import CommentLike


@pytest.fixture
def test_comment_like(db, test_user, test_approved_comment):
    """A CommentLike by test_user on test_approved_comment."""
    return CommentLike.objects.create(
        user=test_user,
        comment=test_approved_comment,
    )
