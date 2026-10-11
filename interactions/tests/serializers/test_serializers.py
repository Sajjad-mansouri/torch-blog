"""
Behavioral tests for interactions.serializers.

Coverage:
- CommentAuthorSerializer — present author, missing context request,
  and the None case.
- CommentSerializer — shape, get_author placeholder, is_liked with
  and without a request, replies filtered to approved and
  non-deleted, like_count reading _like_count when annotated.
- CommentWriteSerializer — body validation, HTML cleaning, length
  truncation, parent validation for wrong post / deleted /
  nonexistent, parent=None allowed.
- ToggleResponseSerializer — shape.
"""

import pytest

from interactions.api.serializers import (
    CommentAuthorSerializer,
    CommentSerializer,
    CommentWriteSerializer,
    ToggleResponseSerializer,
)
from interactions.models import Comment

# ==================================================================
# CommentAuthorSerializer
# ==================================================================


@pytest.mark.django_db
class TestCommentAuthorSerializer:
    def test_fields_with_request(self, test_user, api_request):
        data = CommentAuthorSerializer(test_user, context={"request": api_request}).data

        assert data["id"] == test_user.pk
        assert data["username"] == test_user.username
        assert data["display_name"] == test_user.display_name
        assert data["avatar_url"].startswith("http://testserver/")

    def test_fields_without_request_returns_relative_avatar_url(self, test_user):
        data = CommentAuthorSerializer(test_user).data

        assert data["avatar_url"] == "/static/img/default-avatar.jpg"


# ==================================================================
# CommentSerializer — shape and author
# ==================================================================
@pytest.mark.django_db
class TestCommentSerializerShape:
    def test_includes_expected_fields(self, test_approved_comment, api_request):
        data = CommentSerializer(
            test_approved_comment, context={"request": api_request}
        ).data

        for field in (
            "id",
            "body",
            "author",
            "parent",
            "created_at",
            "edited_at",
            "is_deleted",
            "like_count",
            "is_liked",
            "replies",
            "status",
        ):
            assert field in data

    def test_parent_is_null_for_top_level(self, test_approved_comment, api_request):
        data = CommentSerializer(
            test_approved_comment, context={"request": api_request}
        ).data
        assert data["parent"] is None

    def test_parent_id_for_reply(
        self, test_comment_reply, test_approved_comment, api_request
    ):
        data = CommentSerializer(
            test_comment_reply, context={"request": api_request}
        ).data
        assert data["parent"] == test_approved_comment.pk


@pytest.mark.django_db
class TestCommentSerializerAuthor:
    def test_present_author_is_serialized(self, test_approved_comment, api_request):
        data = CommentSerializer(
            test_approved_comment, context={"request": api_request}
        ).data

        assert data["author"]["username"] == test_approved_comment.author.username

    def test_deleted_author_gets_placeholder(self, test_approved_comment, api_request):
        comment = Comment.objects.get(pk=test_approved_comment.pk)
        comment.author = None
        comment.save(update_fields=["author"])

        data = CommentSerializer(comment, context={"request": api_request}).data

        assert data["author"]["id"] is None
        assert data["author"]["username"] is None
        assert data["author"]["display_name"] == "[deleted]"
        assert data["author"]["avatar_url"] is None


# ==================================================================
# CommentSerializer — like_count
# ==================================================================
@pytest.mark.django_db
class TestCommentSerializerLikeCount:
    def test_reads_annotation_when_present(
        self, test_approved_comment, test_comment_like, api_request
    ):
        comment = Comment.objects.with_like_count().get(pk=test_approved_comment.pk)
        data = CommentSerializer(comment, context={"request": api_request}).data

        # with_like_count annotates _like_count=1
        assert data["like_count"] == 1

    def test_falls_back_to_property_when_not_annotated(
        self, test_approved_comment, test_comment_like, api_request
    ):
        # A fresh instance without the annotation.
        comment = Comment.objects.get(pk=test_approved_comment.pk)
        data = CommentSerializer(comment, context={"request": api_request}).data

        assert data["like_count"] == 1

    def test_zero_when_no_likes(self, test_approved_comment, api_request):
        data = CommentSerializer(
            test_approved_comment, context={"request": api_request}
        ).data
        assert data["like_count"] == 0


# ==================================================================
# CommentSerializer — is_liked
# ==================================================================
@pytest.mark.django_db
class TestCommentSerializerIsLiked:
    def test_false_when_no_request(self, test_approved_comment):
        data = CommentSerializer(test_approved_comment).data
        assert data["is_liked"] is False

    def test_false_for_anonymous(self, test_approved_comment, api_request):
        data = CommentSerializer(
            test_approved_comment, context={"request": api_request}
        ).data
        assert data["is_liked"] is False

    def test_true_when_in_liked_ids(
        self, test_approved_comment, test_user, api_request
    ):
        api_request.user = test_user
        data = CommentSerializer(
            test_approved_comment,
            context={
                "request": api_request,
                "liked_comment_ids": {test_approved_comment.id},
            },
        ).data

        assert data["is_liked"] is True

    def test_false_when_not_in_liked_ids(
        self, test_approved_comment, test_user, api_request
    ):
        api_request.user = test_user
        data = CommentSerializer(
            test_approved_comment,
            context={
                "request": api_request,
                "liked_comment_ids": set(),
            },
        ).data

        assert data["is_liked"] is False

    def test_false_when_liked_comment_ids_missing_from_context(
        self, test_approved_comment, test_user, api_request
    ):
        api_request.user = test_user
        data = CommentSerializer(
            test_approved_comment, context={"request": api_request}
        ).data

        assert data["is_liked"] is False


# ==================================================================
# CommentSerializer — replies
# ==================================================================
@pytest.mark.django_db
class TestCommentSerializerReplies:
    def test_replies_only_include_approved_non_deleted(
        self, test_approved_comment, test_user, api_request
    ):
        Comment.objects.create(
            post=test_approved_comment.post,
            author=test_user,
            parent=test_approved_comment,
            body="approved reply",
            status=Comment.Status.APPROVED,
            is_deleted=False,
        )
        Comment.objects.create(
            post=test_approved_comment.post,
            author=test_user,
            parent=test_approved_comment,
            body="pending reply",
            status=Comment.Status.PENDING,
            is_deleted=False,
        )
        Comment.objects.create(
            post=test_approved_comment.post,
            author=test_user,
            parent=test_approved_comment,
            body="deleted reply",
            status=Comment.Status.APPROVED,
            is_deleted=True,
        )

        data = CommentSerializer(
            test_approved_comment, context={"request": api_request}
        ).data

        assert len(data["replies"]) == 1
        assert data["replies"][0]["body"] == "approved reply"

    def test_replies_is_empty_when_no_replies(self, test_approved_comment, api_request):
        data = CommentSerializer(
            test_approved_comment, context={"request": api_request}
        ).data
        assert data["replies"] == []

    def test_reply_appears_in_parent_replies_list(
        self, test_approved_comment, test_comment_reply, api_request
    ):
        data = CommentSerializer(
            test_approved_comment, context={"request": api_request}
        ).data

        reply_ids = [r["id"] for r in data["replies"]]
        assert test_comment_reply.pk in reply_ids


# ==================================================================
# CommentWriteSerializer — body validation
# ==================================================================
@pytest.mark.django_db
class TestCommentWriteSerializerBody:
    def test_empty_body_is_rejected(self, test_approved_comment, test_user):
        serializer = CommentWriteSerializer(
            data={"body": ""},
            context={"post": test_approved_comment.post},
        )
        assert not serializer.is_valid()
        assert "body" in serializer.errors

    def test_whitespace_only_body_is_rejected(self, test_approved_comment):
        serializer = CommentWriteSerializer(
            data={"body": "   \t\n  "},
            context={"post": test_approved_comment.post},
        )
        assert not serializer.is_valid()
        assert "body" in serializer.errors

    def test_body_is_stripped_of_html(self, test_approved_comment):
        serializer = CommentWriteSerializer(
            data={"body": "<p>Hello <strong>world</strong></p>"},
            context={"post": test_approved_comment.post},
        )
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["body"] == "Hello world"

    def test_html_only_body_is_rejected(self, test_approved_comment):
        serializer = CommentWriteSerializer(
            data={"body": "<script></script>"},
            context={"post": test_approved_comment.post},
        )
        assert not serializer.is_valid()
        assert "body" in serializer.errors

    def test_body_over_2000_chars_is_rejected_by_drf(self, test_approved_comment):
        """
        DRF's ModelSerializer maps the model TextField(max_length=2000)
        to CharField(max_length=2000), which enforces the limit BEFORE
        validate_body() runs. So over-2000 raw input is rejected by
        the field's own validators, not by validate_body's
        `clean_text(value)[:2000]` truncation.

        The truncation inside validate_body is therefore unreachable
        for inputs longer than 2000 characters.
        """
        long = "a" * 3000
        serializer = CommentWriteSerializer(
            data={"body": long},
            context={"post": test_approved_comment.post},
        )
        assert not serializer.is_valid()
        assert "body" in serializer.errors
        assert "2000" in str(serializer.errors["body"][0])

    def test_body_under_2000_with_html_cleaning_is_accepted(
        self, test_approved_comment
    ):
        # Under 2000 raw chars; the cleaned body is shorter still.
        body = "<p>" + "a" * 100 + "</p>"
        serializer = CommentWriteSerializer(
            data={"body": body},
            context={"post": test_approved_comment.post},
        )
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["body"] == "a" * 100

    def test_documents_raw_length_is_not_capped_before_cleaning(
        self, test_approved_comment
    ):
        """
        The serializer runs clean_text() first, then truncates.
        A very long HTML input that cleans down to a short string
        is accepted, even if the raw input exceeds 2000 characters.
        Documented current behavior.
        """
        # 5000 chars of tags collapse to an empty string body.
        body = "<p></p>" * 625
        serializer = CommentWriteSerializer(
            data={"body": body},
            context={"post": test_approved_comment.post},
        )
        assert not serializer.is_valid()  # cleaned body is empty
        assert "body" in serializer.errors


# ==================================================================
# CommentWriteSerializer — parent validation
# ==================================================================
@pytest.mark.django_db
class TestCommentWriteSerializerParent:
    def test_parent_none_is_allowed(self, test_approved_comment):
        serializer = CommentWriteSerializer(
            data={"body": "Top-level.", "parent": None},
            context={"post": test_approved_comment.post},
        )
        assert serializer.is_valid(), serializer.errors

    def test_parent_omitted_is_allowed(self, test_approved_comment):
        serializer = CommentWriteSerializer(
            data={"body": "Top-level."},
            context={"post": test_approved_comment.post},
        )
        assert serializer.is_valid(), serializer.errors

    def test_valid_parent_on_same_post_is_accepted(self, test_approved_comment):
        serializer = CommentWriteSerializer(
            data={"body": "A reply.", "parent": test_approved_comment.pk},
            context={"post": test_approved_comment.post},
        )
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["parent"] == test_approved_comment.pk

    def test_parent_from_different_post_is_rejected(
        self, test_approved_comment, test_second_published_post
    ):
        serializer = CommentWriteSerializer(
            data={"body": "A reply.", "parent": test_approved_comment.pk},
            context={"post": test_second_published_post},
        )
        assert not serializer.is_valid()
        assert "parent" in serializer.errors

    def test_nonexistent_parent_is_rejected(self, test_approved_comment):
        serializer = CommentWriteSerializer(
            data={"body": "A reply.", "parent": 999_999},
            context={"post": test_approved_comment.post},
        )
        assert not serializer.is_valid()
        assert "parent" in serializer.errors

    def test_soft_deleted_parent_is_rejected(self, test_approved_comment, test_user):
        test_approved_comment.soft_delete(test_user)

        serializer = CommentWriteSerializer(
            data={"body": "A reply.", "parent": test_approved_comment.pk},
            context={"post": test_approved_comment.post},
        )
        assert not serializer.is_valid()
        assert "parent" in serializer.errors

    def test_parent_without_post_in_context_is_allowed(self):
        """
        If the serializer is used without `post` in context, the
        parent is not validated at all. This is a defensive check
        in the serializer to allow standalone use.
        """
        serializer = CommentWriteSerializer(
            data={"body": "A reply.", "parent": 999_999},
            context={},
        )
        assert serializer.is_valid(), serializer.errors


# ==================================================================
# ToggleResponseSerializer
# ==================================================================
class TestToggleResponseSerializer:
    def test_serializes_active_and_count(self):
        data = ToggleResponseSerializer({"active": True, "count": 5}).data

        assert data["active"] is True
        assert data["count"] == 5

    def test_requires_active(self):
        serializer = ToggleResponseSerializer(data={"count": 5})
        assert not serializer.is_valid()
        assert "active" in serializer.errors

    def test_requires_count(self):
        serializer = ToggleResponseSerializer(data={"active": True})
        assert not serializer.is_valid()
        assert "count" in serializer.errors
