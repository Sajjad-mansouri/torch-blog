"""
Behavioral tests for interactions.services.

Coverage:
- toggle_like / toggle_comment_like / toggle_bookmark — the three
  toggle primitives, including create/delete cycle, count
  recomputation, and the (bool, int) return shape.
- create_comment — top-level creation, reply creation, parent
  validation.

Assertions reflect the actual observable behavior of the current
implementation. Where the behavior deserves a note, it is called
out in the test name or docstring.
"""

import pytest

from interactions.api.services import (
    create_comment,
    toggle_bookmark,
    toggle_comment_like,
    toggle_like,
)
from interactions.models import Bookmark, Comment, CommentLike, Like


# ==================================================================
# toggle_like
# ==================================================================
@pytest.mark.django_db
class TestToggleLike:
    def test_first_call_creates_like_and_returns_true(
        self, test_user, test_published_post
    ):
        liked, count = toggle_like(test_user, test_published_post)

        assert liked is True
        assert count == 1
        assert Like.objects.filter(user=test_user, post=test_published_post).exists()

    def test_second_call_removes_like_and_returns_false(
        self, test_user, test_published_post
    ):
        toggle_like(test_user, test_published_post)
        liked, count = toggle_like(test_user, test_published_post)

        assert liked is False
        assert count == 0
        assert not Like.objects.filter(
            user=test_user, post=test_published_post
        ).exists()

    def test_count_reflects_other_users_likes(
        self, test_user, test_other_author, test_published_post
    ):
        Like.objects.create(user=test_other_author, post=test_published_post)

        liked, count = toggle_like(test_user, test_published_post)

        assert liked is True
        assert count == 2

    def test_toggle_does_not_affect_other_users_like(
        self, test_user, test_other_author, test_published_post
    ):
        Like.objects.create(user=test_other_author, post=test_published_post)
        toggle_like(test_user, test_published_post)
        toggle_like(test_user, test_published_post)  # toggle back off

        assert Like.objects.filter(
            user=test_other_author, post=test_published_post
        ).exists()

    def test_toggle_is_scoped_to_post(
        self, test_user, test_published_post, test_second_published_post
    ):
        toggle_like(test_user, test_published_post)
        liked, count = toggle_like(test_user, test_second_published_post)

        assert liked is True
        assert count == 1
        assert Like.objects.filter(user=test_user).count() == 2


# ==================================================================
# toggle_comment_like
# ==================================================================
@pytest.mark.django_db
class TestToggleCommentLike:
    def test_first_call_creates_like_and_returns_true(
        self, test_user, test_approved_comment
    ):
        liked, count = toggle_comment_like(test_user, test_approved_comment)

        assert liked is True
        assert count == 1

    def test_second_call_removes_like_and_returns_false(
        self, test_user, test_approved_comment
    ):
        toggle_comment_like(test_user, test_approved_comment)
        liked, count = toggle_comment_like(test_user, test_approved_comment)

        assert liked is False
        assert count == 0

    def test_count_reflects_other_users_likes(
        self, test_user, test_other_author, test_approved_comment
    ):
        CommentLike.objects.create(
            user=test_other_author, comment=test_approved_comment
        )

        liked, count = toggle_comment_like(test_user, test_approved_comment)

        assert liked is True
        assert count == 2


# ==================================================================
# toggle_bookmark
# ==================================================================
@pytest.mark.django_db
class TestToggleBookmark:
    def test_first_call_creates_bookmark_and_returns_true(
        self, test_user, test_published_post
    ):
        bookmarked, count = toggle_bookmark(test_user, test_published_post)

        assert bookmarked is True
        assert count == 1

    def test_second_call_removes_bookmark_and_returns_false(
        self, test_user, test_published_post
    ):
        toggle_bookmark(test_user, test_published_post)
        bookmarked, count = toggle_bookmark(test_user, test_published_post)

        assert bookmarked is False
        assert count == 0

    def test_count_reflects_other_users_bookmarks(
        self, test_user, test_other_author, test_published_post
    ):
        Bookmark.objects.create(user=test_other_author, post=test_published_post)

        bookmarked, count = toggle_bookmark(test_user, test_published_post)

        assert bookmarked is True
        assert count == 2


# ==================================================================
# create_comment
# ==================================================================
@pytest.mark.django_db
class TestCreateCommentTopLevel:
    def test_creates_top_level_comment(self, test_user, test_published_post):
        comment = create_comment(
            user=test_user,
            post=test_published_post,
            body="A new comment.",
        )

        assert comment.pk is not None
        assert comment.author == test_user
        assert comment.post == test_published_post
        assert comment.parent is None
        assert comment.body == "A new comment."

    def test_status_defaults_to_approved(self, test_user, test_published_post):
        comment = create_comment(
            user=test_user,
            post=test_published_post,
            body="Body.",
        )
        assert comment.status == Comment.Status.APPROVED

    def test_comment_is_persisted(self, test_user, test_published_post):
        comment = create_comment(
            user=test_user,
            post=test_published_post,
            body="Persisted comment.",
        )

        assert Comment.objects.filter(pk=comment.pk).exists()


@pytest.mark.django_db
class TestCreateCommentReply:
    def test_creates_reply_with_valid_parent(
        self, test_user, test_published_post, test_approved_comment
    ):
        reply = create_comment(
            user=test_user,
            post=test_published_post,
            body="A reply.",
            parent_id=test_approved_comment.pk,
        )

        assert reply.parent == test_approved_comment

    def test_reply_status_defaults_to_approved(
        self, test_user, test_published_post, test_approved_comment
    ):
        reply = create_comment(
            user=test_user,
            post=test_published_post,
            body="A reply.",
            parent_id=test_approved_comment.pk,
        )
        assert reply.status == Comment.Status.APPROVED

    def test_parent_from_different_post_raises_value_error(
        self,
        test_user,
        test_published_post,
        test_second_published_post,
        test_approved_comment,
    ):
        # test_approved_comment is on test_published_post, not
        # test_second_published_post.
        with pytest.raises(ValueError):
            create_comment(
                user=test_user,
                post=test_second_published_post,
                body="Bad reply.",
                parent_id=test_approved_comment.pk,
            )

    def test_nonexistent_parent_raises_value_error(
        self, test_user, test_published_post
    ):
        with pytest.raises(ValueError):
            create_comment(
                user=test_user,
                post=test_published_post,
                body="Bad reply.",
                parent_id=999_999,
            )

    def test_deleted_parent_is_rejected(
        self, test_user, test_published_post, test_approved_comment
    ):
        """
        create_comment's parent lookup filters is_deleted=False, so a
        soft-deleted parent raises ValueError. This matches
        CommentWriteSerializer.validate_parent.
        """
        test_approved_comment.soft_delete(test_user)

        with pytest.raises(ValueError):
            create_comment(
                user=test_user,
                post=test_published_post,
                body="Reply to deleted parent.",
                parent_id=test_approved_comment.pk,
            )


@pytest.mark.django_db
class TestCreateCommentParentIdNone:
    def test_parent_id_none_creates_top_level(self, test_user, test_published_post):
        comment = create_comment(
            user=test_user,
            post=test_published_post,
            body="Top-level.",
            parent_id=None,
        )

        assert comment.parent is None

    def test_parent_id_falsy_zero_is_treated_as_no_parent(
        self, test_user, test_published_post
    ):
        """
        `if parent_id:` treats 0 and empty-string as no parent.
        pk=0 will not exist anyway, but the branch behavior is
        documented here.
        """
        comment = create_comment(
            user=test_user,
            post=test_published_post,
            body="Zero parent.",
            parent_id=0,
        )

        assert comment.parent is None
