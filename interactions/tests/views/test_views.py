"""
API tests for interactions.views.

Coverage:
- PostLikeToggleView, PostBookmarkToggleView, CommentLikeToggleView
- PostCommentsView (GET list, POST create)
- CommentDetailView (PATCH, DELETE)
- MeLikeListView, MeBookmarkListView

Tests whose names contain "documents" assert the current observable
behavior of the implementation.
"""

import pytest

from interactions.models import Bookmark, Comment, CommentLike, Like


# ==================================================================
# PostLikeToggleView
# ==================================================================
@pytest.mark.django_db
class TestPostLikeToggleView:
    def url(self, post):
        return f"/api/v1/posts/{post.slug}/like/"

    def test_anonymous_returns_401(self, api_client, test_published_post):
        response = api_client.post(self.url(test_published_post))
        assert response.status_code == 401

    def test_authenticated_toggle_on(self, auth_client, test_published_post):
        response = auth_client.post(self.url(test_published_post))

        assert response.status_code == 200
        assert response.data["active"] is True
        assert response.data["count"] == 1
        assert Like.objects.filter(post=test_published_post).count() == 1

    def test_authenticated_toggle_off_on_second_call(
        self, auth_client, test_published_post
    ):
        auth_client.post(self.url(test_published_post))
        response = auth_client.post(self.url(test_published_post))

        assert response.data["active"] is False
        assert response.data["count"] == 0
        assert Like.objects.filter(post=test_published_post).count() == 0

    def test_unknown_slug_returns_404(self, auth_client):
        response = auth_client.post("/api/v1/posts/does-not-exist/like/")
        assert response.status_code == 404

    def test_draft_slug_returns_404(self, auth_client, test_draft_post):
        response = auth_client.post(self.url(test_draft_post))
        assert response.status_code == 404

    def test_response_shape(self, auth_client, test_published_post):
        response = auth_client.post(self.url(test_published_post))

        assert set(response.data.keys()) == {"active", "count"}


# ==================================================================
# PostBookmarkToggleView
# ==================================================================
@pytest.mark.django_db
class TestPostBookmarkToggleView:
    def url(self, post):
        return f"/api/v1/posts/{post.slug}/bookmark/"

    def test_anonymous_returns_401(self, api_client, test_published_post):
        response = api_client.post(self.url(test_published_post))
        assert response.status_code == 401

    def test_authenticated_toggle_on(self, auth_client, test_published_post):
        response = auth_client.post(self.url(test_published_post))

        assert response.status_code == 200
        assert response.data["active"] is True
        assert response.data["count"] == 1
        assert Bookmark.objects.filter(post=test_published_post).count() == 1

    def test_authenticated_toggle_off_on_second_call(
        self, auth_client, test_published_post
    ):
        auth_client.post(self.url(test_published_post))
        response = auth_client.post(self.url(test_published_post))

        assert response.data["active"] is False
        assert response.data["count"] == 0

    def test_unknown_slug_returns_404(self, auth_client):
        response = auth_client.post("/api/v1/posts/does-not-exist/bookmark/")
        assert response.status_code == 404

    def test_response_shape(self, auth_client, test_published_post):
        response = auth_client.post(self.url(test_published_post))
        assert set(response.data.keys()) == {"active", "count"}


# ==================================================================
# CommentLikeToggleView
# ==================================================================
@pytest.mark.django_db
class TestCommentLikeToggleView:
    def url(self, comment):
        return f"/api/v1/comments/{comment.pk}/like/"

    def test_anonymous_returns_401(self, api_client, test_approved_comment):
        response = api_client.post(self.url(test_approved_comment))
        assert response.status_code == 401

    def test_authenticated_toggle_on(self, auth_client, test_approved_comment):
        response = auth_client.post(self.url(test_approved_comment))

        assert response.status_code == 200
        assert response.data["active"] is True
        assert response.data["count"] == 1

    def test_authenticated_toggle_off_on_second_call(
        self, auth_client, test_approved_comment
    ):
        auth_client.post(self.url(test_approved_comment))
        response = auth_client.post(self.url(test_approved_comment))

        assert response.data["active"] is False
        assert response.data["count"] == 0

    def test_pending_comment_returns_404(self, auth_client, test_pending_comment):
        response = auth_client.post(self.url(test_pending_comment))
        assert response.status_code == 404

    def test_soft_deleted_comment_returns_404(
        self, auth_client, test_soft_deleted_comment
    ):
        response = auth_client.post(self.url(test_soft_deleted_comment))
        assert response.status_code == 404

    def test_unknown_id_returns_404(self, auth_client):
        response = auth_client.post("/api/v1/comments/999999/like/")
        assert response.status_code == 404


# ==================================================================
# PostCommentsView — GET
# ==================================================================
@pytest.mark.django_db
class TestPostCommentsViewGet:
    def url(self, post):
        return f"/api/v1/posts/{post.slug}/comments/"

    def test_anonymous_can_list(
        self, api_client, test_published_post, test_approved_comment
    ):
        response = api_client.get(self.url(test_published_post))

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == test_approved_comment.pk

    def test_only_approved_non_deleted_top_level(
        self,
        api_client,
        test_published_post,
        test_approved_comment,
        test_pending_comment,
        test_soft_deleted_comment,
    ):
        response = api_client.get(self.url(test_published_post))
        ids = [c["id"] for c in response.data["results"]]

        assert test_approved_comment.pk in ids
        assert test_pending_comment.pk not in ids
        assert test_soft_deleted_comment.pk not in ids

    def test_replies_are_nested(
        self, api_client, test_published_post, test_approved_comment, test_comment_reply
    ):
        response = api_client.get(self.url(test_published_post))
        comment = response.data["results"][0]

        assert len(comment["replies"]) == 1
        assert comment["replies"][0]["id"] == test_comment_reply.pk

    def test_pending_reply_is_excluded(
        self, api_client, test_published_post, test_approved_comment, test_user
    ):
        Comment.objects.create(
            post=test_published_post,
            author=test_user,
            parent=test_approved_comment,
            body="pending reply",
            status=Comment.Status.PENDING,
            is_deleted=False,
        )

        response = api_client.get(self.url(test_published_post))
        comment = response.data["results"][0]
        assert comment["replies"] == []

    def test_is_liked_reflects_current_user(
        self, auth_client, test_user, test_published_post, test_approved_comment
    ):
        CommentLike.objects.create(user=test_user, comment=test_approved_comment)

        response = auth_client.get(self.url(test_published_post))
        comment = response.data["results"][0]

        assert comment["is_liked"] is True

    def test_is_liked_false_for_anonymous(
        self, api_client, test_user, test_published_post, test_approved_comment
    ):
        CommentLike.objects.create(user=test_user, comment=test_approved_comment)

        response = api_client.get(self.url(test_published_post))
        comment = response.data["results"][0]

        assert comment["is_liked"] is False

    def test_draft_post_returns_404(self, api_client, test_draft_post):
        response = api_client.get(self.url(test_draft_post))
        assert response.status_code == 404


# ==================================================================
# PostCommentsView — POST
# ==================================================================
@pytest.mark.django_db
class TestPostCommentsViewPost:
    def url(self, post):
        return f"/api/v1/posts/{post.slug}/comments/"

    def test_anonymous_returns_401(self, api_client, test_published_post):
        response = api_client.post(
            self.url(test_published_post), {"body": "hi"}, format="json"
        )
        assert response.status_code == 401

    def test_creates_top_level_comment(
        self, auth_client, test_user, test_published_post
    ):
        response = auth_client.post(
            self.url(test_published_post), {"body": "A new comment."}, format="json"
        )

        assert response.status_code == 201
        assert (
            Comment.objects.filter(
                post=test_published_post, author=test_user, parent__isnull=True
            ).count()
            == 1
        )

    def test_creates_reply_with_valid_parent(
        self, auth_client, test_user, test_published_post, test_approved_comment
    ):
        response = auth_client.post(
            self.url(test_published_post),
            {"body": "A reply.", "parent": test_approved_comment.pk},
            format="json",
        )

        assert response.status_code == 201
        assert (
            Comment.objects.filter(
                post=test_published_post, parent=test_approved_comment
            ).count()
            == 1
        )

    def test_empty_body_returns_400(self, auth_client, test_published_post):
        response = auth_client.post(
            self.url(test_published_post), {"body": ""}, format="json"
        )
        assert response.status_code == 400
        assert "body" in response.data

    def test_parent_from_wrong_post_returns_400(
        self, auth_client, test_second_published_post, test_approved_comment
    ):
        response = auth_client.post(
            self.url(test_second_published_post),
            {"body": "A reply.", "parent": test_approved_comment.pk},
            format="json",
        )
        assert response.status_code == 400
        assert "parent" in response.data

    def test_response_shape_matches_list_item(self, auth_client, test_published_post):
        response = auth_client.post(
            self.url(test_published_post), {"body": "Shape check."}, format="json"
        )
        # Same fields as list items.
        for field in ("id", "body", "author", "parent", "is_liked", "replies"):
            assert field in response.data

    def test_new_comment_is_liked_false(self, auth_client, test_published_post):
        """
        Regression test: previously, the POST handler built
        liked_ids with dead code that set is_liked=True for the
        author's own just-created comment.
        """
        response = auth_client.post(
            self.url(test_published_post), {"body": "Fresh comment."}, format="json"
        )
        assert response.data["is_liked"] is False


# ==================================================================
# CommentDetailView — PATCH
# ==================================================================
@pytest.mark.django_db
class TestCommentDetailViewPatch:
    def url(self, comment):
        return f"/api/v1/comments/{comment.pk}/"

    def test_owner_can_edit_body(self, auth_client, test_user, test_approved_comment):
        assert test_approved_comment.author == test_user

        response = auth_client.patch(
            self.url(test_approved_comment),
            {"body": "Edited body."},
            format="json",
        )

        assert response.status_code == 200
        test_approved_comment.refresh_from_db()
        assert test_approved_comment.body == "Edited body."
        assert test_approved_comment.edited_at is not None

    def test_non_owner_returns_403(self, other_author_client, test_approved_comment):
        response = other_author_client.patch(
            self.url(test_approved_comment),
            {"body": "Hijack."},
            format="json",
        )
        assert response.status_code == 403

    def test_soft_deleted_comment_returns_404(
        self, auth_client, test_soft_deleted_comment
    ):
        response = auth_client.patch(
            self.url(test_soft_deleted_comment),
            {"body": "Edit."},
            format="json",
        )
        assert response.status_code == 404

    def test_anonymous_returns_401(self, api_client, test_approved_comment):
        response = api_client.patch(
            self.url(test_approved_comment),
            {"body": "Anon edit."},
            format="json",
        )
        assert response.status_code == 401

    def test_parent_is_ignored_on_patch(
        self, auth_client, test_user, test_published_post, test_approved_comment
    ):
        """
        CommentWriteSerializer.update() explicitly discards `parent`
        from validated_data. Sending `parent` in a PATCH returns 200
        but does not change the comment's parent.
        """
        original_parent_id = test_approved_comment.parent_id
        assert original_parent_id is None

        other_parent = Comment.objects.create(
            post=test_published_post,
            author=test_user,
            body="Another top-level.",
            status=Comment.Status.APPROVED,
            is_deleted=False,
        )

        response = auth_client.patch(
            self.url(test_approved_comment),
            {"parent": other_parent.pk},
            format="json",
        )

        assert response.status_code == 200
        test_approved_comment.refresh_from_db()
        # Parent is unchanged.
        assert test_approved_comment.parent_id == original_parent_id


# ==================================================================
# CommentDetailView — DELETE
# ==================================================================
@pytest.mark.django_db
class TestCommentDetailViewDelete:
    def url(self, comment):
        return f"/api/v1/comments/{comment.pk}/"

    def test_owner_can_soft_delete(self, auth_client, test_user, test_approved_comment):
        response = auth_client.delete(self.url(test_approved_comment))

        assert response.status_code == 204
        test_approved_comment.refresh_from_db()
        assert test_approved_comment.is_deleted is True
        assert test_approved_comment.body == "[deleted]"

    def test_editor_can_soft_delete_others_comment(
        self, editor_client, test_editor, test_approved_comment
    ):
        response = editor_client.delete(self.url(test_approved_comment))

        assert response.status_code == 204
        test_approved_comment.refresh_from_db()
        assert test_approved_comment.is_deleted is True

    def test_non_owner_non_editor_returns_403(
        self, other_author_client, test_approved_comment
    ):
        response = other_author_client.delete(self.url(test_approved_comment))
        assert response.status_code == 403

    def test_already_deleted_returns_404(
        self, auth_client, test_user, test_approved_comment
    ):
        test_approved_comment.soft_delete(test_user)

        response = auth_client.delete(self.url(test_approved_comment))
        assert response.status_code == 404

    def test_anonymous_returns_401(self, api_client, test_approved_comment):
        response = api_client.delete(self.url(test_approved_comment))
        assert response.status_code == 401


# ==================================================================
# MeLikeListView
# ==================================================================
@pytest.mark.django_db
class TestMeLikeListView:
    def test_anonymous_returns_401(self, api_client):
        response = api_client.get("/api/v1/me/likes/")
        assert response.status_code == 401

    def test_returns_liked_posts(self, auth_client, test_user, test_published_post):
        Like.objects.create(user=test_user, post=test_published_post)

        response = auth_client.get("/api/v1/me/likes/")

        assert response.status_code == 200
        slugs = [p["slug"] for p in response.data["results"]]
        assert test_published_post.slug in slugs

    def test_excludes_posts_not_liked(
        self, auth_client, test_user, test_published_post, test_second_published_post
    ):
        Like.objects.create(user=test_user, post=test_published_post)

        response = auth_client.get("/api/v1/me/likes/")
        slugs = [p["slug"] for p in response.data["results"]]

        assert test_published_post.slug in slugs
        assert test_second_published_post.slug not in slugs

    def test_documents_liked_draft_still_appears(
        self, auth_client, test_user, test_draft_post
    ):
        """
        MeLikeListView filters Post.objects.filter(pk__in=..., is_deleted=False)
        but does NOT filter on status='published'. A Like on a post
        that is now a draft still appears in the list.

        Documents current behavior.
        """
        Like.objects.create(user=test_user, post=test_draft_post)

        response = auth_client.get("/api/v1/me/likes/")
        slugs = [p["slug"] for p in response.data["results"]]

        assert test_draft_post.slug in slugs


# ==================================================================
# MeBookmarkListView
# ==================================================================
@pytest.mark.django_db
class TestMeBookmarkListView:
    def test_anonymous_returns_401(self, api_client):
        response = api_client.get("/api/v1/me/bookmarks/")
        assert response.status_code == 401

    def test_returns_bookmarked_posts(
        self, auth_client, test_user, test_published_post
    ):
        Bookmark.objects.create(user=test_user, post=test_published_post)

        response = auth_client.get("/api/v1/me/bookmarks/")
        slugs = [p["slug"] for p in response.data["results"]]

        assert test_published_post.slug in slugs

    def test_documents_bookmarked_draft_still_appears(
        self, auth_client, test_user, test_draft_post
    ):
        """
        Same as MeLikeListView: no status filter, so a Bookmark on a
        post that is now a draft still appears.

        Documents current behavior.
        """
        Bookmark.objects.create(user=test_user, post=test_draft_post)

        response = auth_client.get("/api/v1/me/bookmarks/")
        slugs = [p["slug"] for p in response.data["results"]]

        assert test_draft_post.slug in slugs
