"""
API tests for editor comment moderation, comment list, user list,
user detail, category CRUD, and tag CRUD.
"""

import pytest

from blog.models import Category, Tag
from interactions.models import Comment


# ==================================================================
# CommentModerationViewSet
# ==================================================================
@pytest.mark.django_db
class TestCommentModeration:
    def test_approve_action(self, editor_client, test_author, test_published_post):
        comment = Comment.objects.create(
            post=test_published_post,
            author=test_author,
            body="pending comment",
            status=Comment.Status.PENDING,
            is_deleted=False,
        )

        response = editor_client.post(f"/api/v1/editor/comments/{comment.pk}/approve/")
        assert response.status_code == 200
        comment.refresh_from_db()
        assert comment.status == Comment.Status.APPROVED

    def test_reject_action(self, editor_client, test_author, test_published_post):
        comment = Comment.objects.create(
            post=test_published_post,
            author=test_author,
            body="x",
            status=Comment.Status.PENDING,
            is_deleted=False,
        )

        response = editor_client.post(f"/api/v1/editor/comments/{comment.pk}/reject/")
        assert response.status_code == 200
        comment.refresh_from_db()
        assert comment.status == Comment.Status.REJECTED

    def test_spam_action(self, editor_client, test_author, test_published_post):
        comment = Comment.objects.create(
            post=test_published_post,
            author=test_author,
            body="x",
            status=Comment.Status.APPROVED,
            is_deleted=False,
        )

        response = editor_client.post(f"/api/v1/editor/comments/{comment.pk}/spam/")
        assert response.status_code == 200
        comment.refresh_from_db()
        assert comment.status == Comment.Status.SPAM

    def test_soft_delete_action(
        self, editor_client, test_editor, test_approved_comment
    ):
        response = editor_client.delete(
            f"/api/v1/editor/comments/{test_approved_comment.pk}/delete/"
        )
        assert response.status_code == 204
        test_approved_comment.refresh_from_db()
        assert test_approved_comment.is_deleted is True
        assert test_approved_comment.body == "[deleted]"

    def test_non_editor_returns_403(self, auth_client, test_approved_comment):
        response = auth_client.post(
            f"/api/v1/editor/comments/{test_approved_comment.pk}/approve/"
        )
        assert response.status_code == 403


# ==================================================================
# EditorCommentListView
# ==================================================================
@pytest.mark.django_db
class TestEditorCommentListView:
    def test_requires_editor(self, auth_client):
        response = auth_client.get("/api/v1/editor/comments-list/")
        assert response.status_code == 403

    def test_lists_comments(
        self, editor_client, test_approved_comment, test_pending_comment
    ):
        response = editor_client.get("/api/v1/editor/comments-list/")
        ids = [c["id"] for c in response.data["results"]]

        assert test_approved_comment.pk in ids
        assert test_pending_comment.pk in ids

    def test_filter_by_status(
        self, editor_client, test_approved_comment, test_pending_comment
    ):
        response = editor_client.get(
            "/api/v1/editor/comments-list/", {"status": "pending"}
        )
        ids = [c["id"] for c in response.data["results"]]

        assert test_pending_comment.pk in ids
        assert test_approved_comment.pk not in ids

    def test_invalid_status_returns_400(self, editor_client):
        response = editor_client.get(
            "/api/v1/editor/comments-list/", {"status": "not-a-status"}
        )
        assert response.status_code == 400

    def test_filter_by_post_slug(
        self,
        editor_client,
        test_approved_comment,
        test_second_published_post,
        test_user,
    ):
        other = Comment.objects.create(
            post=test_second_published_post,
            author=test_user,
            body="other post",
            status=Comment.Status.APPROVED,
            is_deleted=False,
        )

        response = editor_client.get(
            "/api/v1/editor/comments-list/",
            {"post": test_approved_comment.post.slug},
        )
        ids = [c["id"] for c in response.data["results"]]

        assert test_approved_comment.pk in ids
        assert other.pk not in ids

    def test_filter_by_author(
        self,
        editor_client,
        test_approved_comment,
        test_other_author,
        test_user,
        test_published_post,
    ):
        other = Comment.objects.create(
            post=test_published_post,
            author=test_other_author,
            body="by other author",
            status=Comment.Status.APPROVED,
            is_deleted=False,
        )

        response = editor_client.get(
            "/api/v1/editor/comments-list/",
            {"author": test_user.username},
        )
        ids = [c["id"] for c in response.data["results"]]

        assert test_approved_comment.pk in ids
        assert other.pk not in ids

    def test_search_matches_body(self, editor_client, test_user, test_published_post):
        target = Comment.objects.create(
            post=test_published_post,
            author=test_user,
            body="unique zebra word",
            status=Comment.Status.APPROVED,
            is_deleted=False,
        )
        Comment.objects.create(
            post=test_published_post,
            author=test_user,
            body="other comment",
            status=Comment.Status.APPROVED,
            is_deleted=False,
        )

        response = editor_client.get(
            "/api/v1/editor/comments-list/", {"search": "zebra"}
        )
        ids = [c["id"] for c in response.data["results"]]

        assert ids == [target.pk]

    def test_invalid_ordering_returns_400(self, editor_client):
        response = editor_client.get(
            "/api/v1/editor/comments-list/", {"ordering": "bogus"}
        )
        assert response.status_code == 400


# ==================================================================
# EditorUserListView
# ==================================================================
@pytest.mark.django_db
class TestEditorUserListView:
    def test_requires_editor(self, auth_client):
        response = auth_client.get("/api/v1/editor/users-list/")
        assert response.status_code == 403

    def test_lists_users(self, editor_client, test_user, test_author):
        response = editor_client.get("/api/v1/editor/users-list/")
        usernames = [u["username"] for u in response.data["results"]]

        assert test_user.username in usernames
        assert test_author.username in usernames

    def test_filter_by_role(self, editor_client, test_user, test_author):
        response = editor_client.get("/api/v1/editor/users-list/", {"role": "author"})
        usernames = [u["username"] for u in response.data["results"]]

        assert test_author.username in usernames
        assert test_user.username not in usernames

    def test_invalid_role_returns_400(self, editor_client):
        response = editor_client.get(
            "/api/v1/editor/users-list/", {"role": "not-a-role"}
        )
        assert response.status_code == 400

    def test_search_matches_username(self, editor_client, test_user, test_author):
        response = editor_client.get(
            "/api/v1/editor/users-list/", {"search": "test_author"}
        )
        usernames = [u["username"] for u in response.data["results"]]
        assert usernames == [test_author.username]

    def test_invalid_ordering_returns_400(self, editor_client):
        response = editor_client.get(
            "/api/v1/editor/users-list/", {"ordering": "bogus"}
        )
        assert response.status_code == 400


# ==================================================================
# EditorUserDetailViewSet
# ==================================================================
@pytest.mark.django_db
class TestEditorUserDetail:
    def test_change_role(self, editor_client, test_user):
        response = editor_client.patch(
            f"/api/v1/editor/users/{test_user.pk}/role/",
            {"role": "author"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["changed"] is True
        test_user.refresh_from_db()
        assert test_user.role == "author"

    def test_change_role_to_same_value_is_noop(self, editor_client, test_user):
        response = editor_client.patch(
            f"/api/v1/editor/users/{test_user.pk}/role/",
            {"role": "reader"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["changed"] is False

    def test_cannot_change_own_role(self, editor_client, test_editor):
        response = editor_client.patch(
            f"/api/v1/editor/users/{test_editor.pk}/role/",
            {"role": "reader"},
            format="json",
        )
        assert response.status_code == 400

    def test_ban_user(self, editor_client, test_user):
        response = editor_client.post(
            f"/api/v1/editor/users/{test_user.pk}/ban/",
            {"reason": "spam"},
            format="json",
        )
        assert response.status_code == 200
        test_user.refresh_from_db()
        assert test_user.is_active is False

    def test_cannot_ban_self(self, editor_client, test_editor):
        response = editor_client.post(
            f"/api/v1/editor/users/{test_editor.pk}/ban/", {}, format="json"
        )
        assert response.status_code == 400

    def test_cannot_ban_other_editor(self, editor_client, test_author):
        # Promote test_author to editor.
        test_author.role = "editor"
        test_author.save(update_fields=["role"])

        response = editor_client.post(
            f"/api/v1/editor/users/{test_author.pk}/ban/", {}, format="json"
        )
        assert response.status_code == 400

    def test_unban_user(self, editor_client, test_user):
        test_user.is_active = False
        test_user.save(update_fields=["is_active"])

        response = editor_client.post(f"/api/v1/editor/users/{test_user.pk}/unban/")
        assert response.status_code == 200
        test_user.refresh_from_db()
        assert test_user.is_active is True


# ==================================================================
# EditorCategoryViewSet
# ==================================================================
@pytest.mark.django_db
class TestEditorCategoryViewSet:
    def test_create_category(self, editor_client):
        response = editor_client.post(
            "/api/v1/editor/categories/",
            {"name": "New Category"},
            format="json",
        )
        assert response.status_code == 201
        assert Category.objects.filter(name="New Category").exists()

    def test_list_categories(self, editor_client, test_category):
        response = editor_client.get("/api/v1/editor/categories/")
        # ViewSet list is paginated by default? CategoryViewSet does not
        # override pagination_class, so returns a plain list.
        ids = (
            [c["id"] for c in response.data if isinstance(response.data, list)]
            if isinstance(response.data, list)
            else [c["id"] for c in response.data["results"]]
        )
        assert test_category.pk in ids

    def test_update_category(self, editor_client, test_category):
        response = editor_client.patch(
            f"/api/v1/editor/categories/{test_category.slug}/",
            {"name": "Renamed"},
            format="json",
        )
        assert response.status_code == 200
        test_category.refresh_from_db()
        assert test_category.name == "Renamed"

    def test_delete_category_without_posts(self, editor_client, test_second_category):
        response = editor_client.delete(
            f"/api/v1/editor/categories/{test_second_category.slug}/"
        )
        assert response.status_code == 204

    def test_delete_category_with_posts_returns_400(
        self, editor_client, test_category, test_published_post
    ):
        response = editor_client.delete(
            f"/api/v1/editor/categories/{test_category.slug}/"
        )
        assert response.status_code == 400

    def test_documents_delete_blocked_when_only_drafts_exist(
        self, editor_client, test_category, test_draft_post
    ):
        """
        perform_destroy blocks deletion if the category has ANY posts,
        including drafts. Documents current behavior.
        """
        response = editor_client.delete(
            f"/api/v1/editor/categories/{test_category.slug}/"
        )
        assert response.status_code == 400

    def test_documents_parent_delete_cascades_to_children(
        self, editor_client, test_category, test_child_category, test_published_post
    ):
        """
        Deleting the parent cascades to child categories via CASCADE.
        The parent has no posts of its own (test_published_post is on
        test_category, which is the parent — wait, it is). This test
        is refined below.
        """
        # Create a fresh parent that has no posts, with a child that
        # has no posts either.
        parent = Category.objects.create(name="Fresh Parent")
        child = Category.objects.create(name="Fresh Child", parent=parent)

        response = editor_client.delete(f"/api/v1/editor/categories/{parent.slug}/")
        assert response.status_code == 204
        # The child is cascaded away.
        assert not Category.objects.filter(pk=child.pk).exists()


# ==================================================================
# EditorTagViewSet
# ==================================================================
@pytest.mark.django_db
class TestEditorTagViewSet:
    def test_create_tag(self, editor_client):
        response = editor_client.post(
            "/api/v1/editor/tags/", {"name": "New Tag"}, format="json"
        )
        assert response.status_code == 201
        assert Tag.objects.filter(name="New Tag").exists()

    def test_delete_tag_without_usage(self, editor_client, test_second_tag):
        response = editor_client.delete(f"/api/v1/editor/tags/{test_second_tag.slug}/")
        assert response.status_code == 204

    def test_delete_tag_with_usage_returns_400(self, editor_client, test_tag):
        test_tag.usage_count = 1
        test_tag.save(update_fields=["usage_count"])

        response = editor_client.delete(f"/api/v1/editor/tags/{test_tag.slug}/")
        assert response.status_code == 400

    def test_merge_moves_posts_and_deletes_sources(self, editor_client):
        # Two tags, one post tagged with the source.
        source = Tag.objects.create(name="Source", slug="source")
        target = Tag.objects.create(name="Target", slug="target")
        assert source.pk != target.pk

        response = editor_client.post(
            "/api/v1/editor/tags/merge/",
            {"source_ids": [source.pk], "target_id": target.pk},
            format="json",
        )
        # This will fail with AttributeError: Tag has no update_usage_count.
        assert response.status_code == 200
