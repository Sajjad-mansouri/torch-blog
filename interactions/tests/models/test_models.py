"""
Behavioral tests for interactions.models.

Covers Comment, CommentQuerySet, Like, CommentLike, and Bookmark:
field behavior, custom methods and properties, ordering,
constraints, and cascade rules.

Assertions reflect the actual observable behavior of the current
implementation. Where the behavior deserves a note, it is called
out in the test name or docstring.
"""

import pytest
from django.db import IntegrityError

from interactions.models import Bookmark, Comment, CommentLike, Like


# ==================================================================
# Comment — __str__
# ==================================================================
@pytest.mark.django_db
class TestCommentStr:
    def test_str_includes_author_and_post_id(self, test_approved_comment, test_user):
        text = str(test_approved_comment)
        assert test_user.username in text
        assert str(test_approved_comment.post_id) in text

    def test_str_uses_deleted_placeholder_when_author_is_none(
        self, test_approved_comment
    ):
        comment = Comment.objects.get(pk=test_approved_comment.pk)
        comment.author = None
        comment.save(update_fields=["author"])

        assert "deleted" in str(comment)


# ==================================================================
# Comment — properties
# ==================================================================
@pytest.mark.django_db
class TestCommentIsReply:
    def test_top_level_comment_is_not_reply(self, test_approved_comment):
        assert test_approved_comment.is_reply is False

    def test_reply_is_reply(self, test_comment_reply):
        assert test_comment_reply.is_reply is True


@pytest.mark.django_db
class TestCommentIsEdited:
    def test_new_comment_is_not_edited(self, test_approved_comment):
        assert test_approved_comment.is_edited is False

    def test_after_mark_edited_is_edited(self, test_approved_comment):
        test_approved_comment.mark_edited()
        test_approved_comment.refresh_from_db()
        assert test_approved_comment.is_edited is True


@pytest.mark.django_db
class TestCommentLikeCountProperty:
    def test_zero_when_no_likes(self, test_approved_comment):
        assert test_approved_comment.like_count == 0

    def test_counts_comment_likes(self, test_approved_comment, test_comment_like):
        assert test_approved_comment.like_count == 1

    def test_counts_multiple_likes(
        self, test_approved_comment, test_user, test_other_author
    ):
        CommentLike.objects.create(user=test_user, comment=test_approved_comment)
        CommentLike.objects.create(
            user=test_other_author, comment=test_approved_comment
        )
        assert test_approved_comment.like_count == 2


@pytest.mark.django_db
class TestCommentIsVisible:
    def test_approved_non_deleted_on_published_post_is_visible(
        self, test_approved_comment
    ):
        assert test_approved_comment.is_visible is True

    def test_pending_comment_is_not_visible(self, test_pending_comment):
        assert test_pending_comment.is_visible is False

    def test_soft_deleted_comment_is_not_visible(self, test_soft_deleted_comment):
        assert test_soft_deleted_comment.is_visible is False

    def test_comment_on_draft_post_is_not_visible(
        self, test_author, test_draft_post, test_user
    ):
        comment = Comment.objects.create(
            post=test_draft_post,
            author=test_user,
            body="On a draft.",
            status=Comment.Status.APPROVED,
            is_deleted=False,
        )
        assert comment.is_visible is False

    def test_comment_on_soft_deleted_post_is_not_visible(
        self, test_soft_deleted_post, test_user
    ):
        comment = Comment.objects.create(
            post=test_soft_deleted_post,
            author=test_user,
            body="On a soft-deleted post.",
            status=Comment.Status.APPROVED,
            is_deleted=False,
        )
        assert comment.is_visible is False


# ==================================================================
# Comment — mutations
# ==================================================================
@pytest.mark.django_db
class TestCommentSoftDelete:
    def test_sets_flags_and_body(self, test_approved_comment, test_editor):
        test_approved_comment.soft_delete(test_editor)
        test_approved_comment.refresh_from_db()

        assert test_approved_comment.is_deleted is True
        assert test_approved_comment.deleted_by == test_editor
        assert test_approved_comment.deleted_at is not None
        assert test_approved_comment.body == "[deleted]"

    def test_row_still_exists_after_soft_delete(
        self, test_approved_comment, test_editor
    ):
        pk = test_approved_comment.pk
        test_approved_comment.soft_delete(test_editor)

        assert Comment.objects.filter(pk=pk).exists()

    def test_updated_at_is_not_changed_by_soft_delete(
        self, test_approved_comment, test_editor
    ):
        """
        soft_delete uses save(update_fields=[...]) without including
        updated_at, so auto_now does not fire. This is the current
        behavior.
        """
        before = test_approved_comment.updated_at
        test_approved_comment.soft_delete(test_editor)
        test_approved_comment.refresh_from_db()

        assert test_approved_comment.updated_at == before


@pytest.mark.django_db
class TestCommentMarkEdited:
    def test_sets_edited_at(self, test_approved_comment):
        assert test_approved_comment.edited_at is None

        test_approved_comment.mark_edited()
        test_approved_comment.refresh_from_db()

        assert test_approved_comment.edited_at is not None

    def test_does_not_change_body(self, test_approved_comment):
        original = test_approved_comment.body
        test_approved_comment.mark_edited()
        test_approved_comment.refresh_from_db()

        assert test_approved_comment.body == original


# ==================================================================
# CommentQuerySet.with_like_count
# ==================================================================
@pytest.mark.django_db
class TestWithLikeCount:
    def test_annotates_underscore_like_count(
        self, test_approved_comment, test_comment_like
    ):
        comment = Comment.objects.with_like_count().get(pk=test_approved_comment.pk)
        assert comment._like_count == 1

    def test_annotation_does_not_collide_with_property(
        self, test_approved_comment, test_comment_like
    ):
        # The whole reason for the _like_count name: the property
        # like_count has no setter, so annotating with that name
        # raises AttributeError. Using the underscore-prefixed name
        # avoids the collision.
        comment = Comment.objects.with_like_count().get(pk=test_approved_comment.pk)

        # Both the annotation and the property are readable.
        assert comment._like_count == 1
        assert comment.like_count == 1

    def test_zero_when_no_likes(self, test_approved_comment):
        comment = Comment.objects.with_like_count().get(pk=test_approved_comment.pk)
        assert comment._like_count == 0

    def test_counts_multiple_likes_distinctly(
        self, test_approved_comment, test_user, test_other_author
    ):
        CommentLike.objects.create(user=test_user, comment=test_approved_comment)
        CommentLike.objects.create(
            user=test_other_author, comment=test_approved_comment
        )

        comment = Comment.objects.with_like_count().get(pk=test_approved_comment.pk)
        assert comment._like_count == 2


# ==================================================================
# Comment — Meta ordering and cascade behavior
# ==================================================================
@pytest.mark.django_db
class TestCommentOrdering:
    def test_default_ordering_is_created_at_asc(self, test_published_post, test_user):
        first = Comment.objects.create(
            post=test_published_post,
            author=test_user,
            body="first",
        )
        second = Comment.objects.create(
            post=test_published_post,
            author=test_user,
            body="second",
        )

        results = list(Comment.objects.filter(post=test_published_post))
        assert results[0] == first
        assert results[1] == second


@pytest.mark.django_db
class TestCommentCascades:
    def test_deleting_post_cascades_to_comments(
        self, test_published_post, test_approved_comment
    ):
        pk = test_approved_comment.pk
        test_published_post.delete()

        assert not Comment.objects.filter(pk=pk).exists()

    def test_deleting_author_sets_comment_author_null(
        self, test_approved_comment, test_user
    ):
        pk = test_approved_comment.pk
        test_user.delete()

        comment = Comment.objects.get(pk=pk)
        assert comment.author is None

    def test_deleting_parent_comment_cascades_to_replies(
        self, test_approved_comment, test_comment_reply
    ):
        reply_pk = test_comment_reply.pk
        test_approved_comment.delete()

        assert not Comment.objects.filter(pk=reply_pk).exists()


# ==================================================================
# Like
# ==================================================================
@pytest.mark.django_db
class TestLikeConstraints:
    def test_unique_user_post(self, test_user, test_published_post, test_like):
        with pytest.raises(IntegrityError):
            Like.objects.create(user=test_user, post=test_published_post)

    def test_same_user_two_posts_allowed(
        self, test_user, test_published_post, test_second_published_post
    ):
        Like.objects.create(user=test_user, post=test_published_post)
        Like.objects.create(user=test_user, post=test_second_published_post)

        assert Like.objects.filter(user=test_user).count() == 2

    def test_two_users_same_post_allowed(
        self, test_user, test_other_author, test_published_post
    ):
        Like.objects.create(user=test_user, post=test_published_post)
        Like.objects.create(user=test_other_author, post=test_published_post)

        assert Like.objects.filter(post=test_published_post).count() == 2


@pytest.mark.django_db
class TestLikeCascades:
    def test_deleting_user_cascades_to_likes(self, test_user, test_like):
        pk = test_like.pk
        test_user.delete()

        assert not Like.objects.filter(pk=pk).exists()

    def test_deleting_post_cascades_to_likes(self, test_published_post, test_like):
        pk = test_like.pk
        test_published_post.delete()

        assert not Like.objects.filter(pk=pk).exists()


@pytest.mark.django_db
class TestLikeStr:
    def test_str_format(self, test_user, test_published_post, test_like):
        text = str(test_like)
        assert test_user.username in text
        assert str(test_published_post.pk) in text


# ==================================================================
# CommentLike
# ==================================================================
@pytest.mark.django_db
class TestCommentLikeConstraints:
    def test_unique_user_comment(
        self, test_user, test_approved_comment, test_comment_like
    ):
        with pytest.raises(IntegrityError):
            CommentLike.objects.create(user=test_user, comment=test_approved_comment)

    def test_same_user_two_comments_allowed(
        self, test_user, test_approved_comment, test_pending_comment
    ):
        CommentLike.objects.create(user=test_user, comment=test_approved_comment)
        CommentLike.objects.create(user=test_user, comment=test_pending_comment)

        assert CommentLike.objects.filter(user=test_user).count() == 2

    def test_two_users_same_comment_allowed(
        self, test_user, test_other_author, test_approved_comment
    ):
        CommentLike.objects.create(user=test_user, comment=test_approved_comment)
        CommentLike.objects.create(
            user=test_other_author, comment=test_approved_comment
        )

        assert CommentLike.objects.filter(comment=test_approved_comment).count() == 2


@pytest.mark.django_db
class TestCommentLikeCascades:
    def test_deleting_user_cascades_to_comment_likes(
        self, test_user, test_comment_like
    ):
        pk = test_comment_like.pk
        test_user.delete()

        assert not CommentLike.objects.filter(pk=pk).exists()

    def test_deleting_comment_cascades_to_comment_likes(
        self, test_approved_comment, test_comment_like
    ):
        pk = test_comment_like.pk
        test_approved_comment.delete()

        assert not CommentLike.objects.filter(pk=pk).exists()


@pytest.mark.django_db
class TestCommentLikeStr:
    def test_str_format(self, test_user, test_approved_comment, test_comment_like):
        text = str(test_comment_like)
        assert test_user.username in text
        assert str(test_approved_comment.pk) in text


# ==================================================================
# Bookmark
# ==================================================================
@pytest.mark.django_db
class TestBookmarkConstraints:
    def test_unique_user_post(self, test_user, test_published_post, test_bookmark):
        with pytest.raises(IntegrityError):
            Bookmark.objects.create(user=test_user, post=test_published_post)

    def test_same_user_two_posts_allowed(
        self, test_user, test_published_post, test_second_published_post
    ):
        Bookmark.objects.create(user=test_user, post=test_published_post)
        Bookmark.objects.create(user=test_user, post=test_second_published_post)

        assert Bookmark.objects.filter(user=test_user).count() == 2


@pytest.mark.django_db
class TestBookmarkOrdering:
    def test_ordering_is_newest_first(
        self, test_user, test_published_post, test_second_published_post
    ):
        first = Bookmark.objects.create(user=test_user, post=test_published_post)
        second = Bookmark.objects.create(
            user=test_user, post=test_second_published_post
        )

        results = list(Bookmark.objects.filter(user=test_user))
        assert results[0] == second
        assert results[1] == first


@pytest.mark.django_db
class TestBookmarkCascades:
    def test_deleting_user_cascades_to_bookmarks(self, test_user, test_bookmark):
        pk = test_bookmark.pk
        test_user.delete()

        assert not Bookmark.objects.filter(pk=pk).exists()

    def test_deleting_post_cascades_to_bookmarks(
        self, test_published_post, test_bookmark
    ):
        pk = test_bookmark.pk
        test_published_post.delete()

        assert not Bookmark.objects.filter(pk=pk).exists()


@pytest.mark.django_db
class TestBookmarkStr:
    def test_str_format(self, test_user, test_published_post, test_bookmark):
        text = str(test_bookmark)
        assert test_user.username in text
        assert str(test_published_post.pk) in text
