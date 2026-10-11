"""
API tests for editor post views and post decisions.
"""

import pytest
from django.utils import timezone

from blog.models import Post
from notifications.models import Notification


# ==================================================================
# ReviewQueueView
# ==================================================================
@pytest.mark.django_db
class TestReviewQueueView:
    def test_requires_editor(self, auth_client):
        response = auth_client.get("/api/v1/editor/review-queue/")
        assert response.status_code == 403

    def test_anonymous_returns_401(self, api_client):
        response = api_client.get("/api/v1/editor/review-queue/")
        assert response.status_code == 401

    def test_returns_only_pending_posts(
        self, editor_client, test_pending_post, test_draft_post, test_published_post
    ):
        response = editor_client.get("/api/v1/editor/review-queue/")
        ids = [p["id"] for p in response.data["results"]]

        assert test_pending_post.pk in ids
        assert test_draft_post.pk not in ids
        assert test_published_post.pk not in ids

    def test_orders_by_updated_at_ascending(
        self, editor_client, test_author, test_category
    ):
        first = Post.objects.create(
            author=test_author,
            title="First Submitted",
            body="<p>Body.</p>",
            category=test_category,
            status=Post.Status.PENDING,
        )
        second = Post.objects.create(
            author=test_author,
            title="Second Submitted",
            body="<p>Body.</p>",
            category=test_category,
            status=Post.Status.PENDING,
        )
        # Force distinct updated_at.
        Post.objects.filter(pk=first.pk).update(
            updated_at=timezone.now() - timezone.timedelta(hours=2)
        )

        response = editor_client.get("/api/v1/editor/review-queue/")
        ids = [p["id"] for p in response.data["results"]]

        assert ids.index(first.pk) < ids.index(second.pk)

    def test_excludes_soft_deleted_pending(
        self, editor_client, test_author, test_category
    ):
        deleted = Post.objects.create(
            author=test_author,
            title="Deleted Pending",
            body="<p>Body.</p>",
            category=test_category,
            status=Post.Status.PENDING,
            is_deleted=True,
        )

        response = editor_client.get("/api/v1/editor/review-queue/")
        ids = [p["id"] for p in response.data["results"]]
        assert deleted.pk not in ids


# ==================================================================
# EditorPostListView
# ==================================================================
@pytest.mark.django_db
class TestEditorPostListView:
    def test_requires_editor(self, auth_client):
        response = auth_client.get("/api/v1/editor/posts-list/")
        assert response.status_code == 403

    def test_returns_posts_in_all_statuses(
        self, editor_client, test_pending_post, test_draft_post, test_published_post
    ):
        response = editor_client.get("/api/v1/editor/posts-list/")
        ids = [p["id"] for p in response.data["results"]]

        assert test_pending_post.pk in ids
        assert test_draft_post.pk in ids
        assert test_published_post.pk in ids

    def test_filter_by_single_status(
        self, editor_client, test_pending_post, test_draft_post
    ):
        response = editor_client.get(
            "/api/v1/editor/posts-list/", {"status": "pending"}
        )
        ids = [p["id"] for p in response.data["results"]]

        assert test_pending_post.pk in ids
        assert test_draft_post.pk not in ids

    def test_filter_by_multiple_statuses_comma_separated(
        self, editor_client, test_pending_post, test_draft_post, test_published_post
    ):
        response = editor_client.get(
            "/api/v1/editor/posts-list/", {"status": "pending,draft"}
        )
        ids = [p["id"] for p in response.data["results"]]

        assert test_pending_post.pk in ids
        assert test_draft_post.pk in ids
        assert test_published_post.pk not in ids

    def test_invalid_status_returns_400(self, editor_client, test_pending_post):
        response = editor_client.get(
            "/api/v1/editor/posts-list/", {"status": "not-a-status"}
        )
        assert response.status_code == 400
        assert "status" in response.data

    def test_filter_by_author(
        self, editor_client, test_pending_post, test_other_authors_post
    ):
        response = editor_client.get(
            "/api/v1/editor/posts-list/", {"author": test_pending_post.author.username}
        )
        ids = [p["id"] for p in response.data["results"]]

        assert test_pending_post.pk in ids
        assert test_other_authors_post.pk not in ids

    def test_filter_by_category(
        self, editor_client, test_pending_post, test_second_category
    ):
        response = editor_client.get(
            "/api/v1/editor/posts-list/", {"category": test_second_category.slug}
        )
        ids = [p["id"] for p in response.data["results"]]
        assert test_pending_post.pk not in ids

    def test_search_filter(self, editor_client, test_pending_post, test_draft_post):
        test_draft_post.title = "Zebra Migration Patterns"
        test_draft_post.save(update_fields=["title"])

        response = editor_client.get("/api/v1/editor/posts-list/", {"search": "Zebra"})
        ids = [p["id"] for p in response.data["results"]]

        assert test_draft_post.pk in ids
        assert test_pending_post.pk not in ids

    def test_invalid_ordering_returns_400(self, editor_client, test_pending_post):
        response = editor_client.get(
            "/api/v1/editor/posts-list/", {"ordering": "not-a-field"}
        )
        assert response.status_code == 400
        assert "ordering" in response.data


# ==================================================================
# PostDecisionViewSet
# ==================================================================
@pytest.mark.django_db
class TestPostDecisionsApprove:
    def test_approve_pending_post(self, editor_client, test_pending_post):
        response = editor_client.post(
            f"/api/v1/editor/posts/{test_pending_post.slug}/approve/"
        )
        assert response.status_code == 200
        test_pending_post.refresh_from_db()
        assert test_pending_post.status == Post.Status.PUBLISHED

    def test_approve_draft_returns_400(self, editor_client, test_draft_post):
        response = editor_client.post(
            f"/api/v1/editor/posts/{test_draft_post.slug}/approve/"
        )
        assert response.status_code == 400

    def test_non_editor_returns_403(self, auth_client, test_pending_post):
        response = auth_client.post(
            f"/api/v1/editor/posts/{test_pending_post.slug}/approve/"
        )
        assert response.status_code == 403

    def test_sends_notification(self, editor_client, test_pending_post):
        editor_client.post(f"/api/v1/editor/posts/{test_pending_post.slug}/approve/")
        assert (
            Notification.objects.filter(verb=Notification.Verb.POST_APPROVED).count()
            == 1
        )


@pytest.mark.django_db
class TestPostDecisionsReject:
    def test_reject_pending_post_with_reason(self, editor_client, test_pending_post):
        response = editor_client.post(
            f"/api/v1/editor/posts/{test_pending_post.slug}/reject/",
            {"reason": "off-topic"},
            format="json",
        )
        assert response.status_code == 200
        test_pending_post.refresh_from_db()
        assert test_pending_post.status == Post.Status.REJECTED
        assert test_pending_post.rejection_reason == "off-topic"

    def test_reject_without_reason_returns_400(self, editor_client, test_pending_post):
        response = editor_client.post(
            f"/api/v1/editor/posts/{test_pending_post.slug}/reject/",
            {},
            format="json",
        )
        assert response.status_code == 400

    def test_reject_published_returns_400(self, editor_client, test_published_post):
        response = editor_client.post(
            f"/api/v1/editor/posts/{test_published_post.slug}/reject/",
            {"reason": "why"},
            format="json",
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestPostDecisionsRequestChanges:
    def test_request_changes_on_pending(self, editor_client, test_pending_post):
        response = editor_client.post(
            f"/api/v1/editor/posts/{test_pending_post.slug}/request-changes/",
            {"note": "tighten intro"},
            format="json",
        )
        assert response.status_code == 200
        test_pending_post.refresh_from_db()
        assert test_pending_post.status == Post.Status.CHANGES_REQUESTED

    def test_request_changes_without_note_returns_400(
        self, editor_client, test_pending_post
    ):
        response = editor_client.post(
            f"/api/v1/editor/posts/{test_pending_post.slug}/request-changes/",
            {},
            format="json",
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestPostDecisionsUnpublish:
    def test_unpublish_published_post(self, editor_client, test_published_post):
        response = editor_client.post(
            f"/api/v1/editor/posts/{test_published_post.slug}/unpublish/",
            {"reason": "needs update"},
            format="json",
        )
        assert response.status_code == 200
        test_published_post.refresh_from_db()
        assert test_published_post.status == Post.Status.UNPUBLISHED

    def test_unpublish_without_reason_is_allowed(
        self, editor_client, test_published_post
    ):
        response = editor_client.post(
            f"/api/v1/editor/posts/{test_published_post.slug}/unpublish/",
            {},
            format="json",
        )
        assert response.status_code == 200

    def test_unpublish_draft_returns_400(self, editor_client, test_draft_post):
        response = editor_client.post(
            f"/api/v1/editor/posts/{test_draft_post.slug}/unpublish/",
            {},
            format="json",
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestPostDecisionsReconsider:
    def test_reconsider_rejected_post(self, editor_client, test_rejected_post):
        response = editor_client.post(
            f"/api/v1/editor/posts/{test_rejected_post.slug}/reconsider/"
        )
        assert response.status_code == 200
        test_rejected_post.refresh_from_db()
        assert test_rejected_post.status == Post.Status.PENDING
        assert test_rejected_post.rejection_reason == ""
        assert test_rejected_post.reviewed_by is None
        assert test_rejected_post.reviewed_at is None

    def test_reconsider_changes_requested_post(
        self, editor_client, test_changes_requested_post
    ):
        response = editor_client.post(
            f"/api/v1/editor/posts/{test_changes_requested_post.slug}/reconsider/"
        )
        assert response.status_code == 200
        test_changes_requested_post.refresh_from_db()
        assert test_changes_requested_post.status == Post.Status.PENDING

    def test_reconsider_draft_returns_400(self, editor_client, test_draft_post):
        response = editor_client.post(
            f"/api/v1/editor/posts/{test_draft_post.slug}/reconsider/"
        )
        assert response.status_code == 400


# ==================================================================
# FeaturedPostsViewSet
# ==================================================================
@pytest.mark.django_db
class TestFeaturedPostsList:
    def test_list_returns_featured_only(
        self, editor_client, test_featured_post, test_published_post
    ):
        response = editor_client.get("/api/v1/editor/featured/")
        assert response.status_code == 200
        # Response is a plain list (no pagination on this action).
        assert isinstance(response.data, list)
        ids = [p["id"] for p in response.data]
        assert test_featured_post.pk in ids
        assert test_published_post.pk not in ids

    def test_requires_editor(self, auth_client):
        response = auth_client.get("/api/v1/editor/featured/")
        assert response.status_code == 403


@pytest.mark.django_db
class TestFeaturedPostsCandidates:
    def test_returns_published_non_featured(
        self, editor_client, test_published_post, test_featured_post
    ):
        response = editor_client.get("/api/v1/editor/featured/candidates/")
        ids = [p["id"] for p in response.data["results"]]

        assert test_published_post.pk in ids
        assert test_featured_post.pk not in ids

    def test_search_filters_candidates(
        self, editor_client, test_published_post, test_second_published_post
    ):
        test_second_published_post.title = "Unique Zebra Topic"
        test_second_published_post.save(update_fields=["title"])

        response = editor_client.get(
            "/api/v1/editor/featured/candidates/", {"search": "Zebra"}
        )
        ids = [p["id"] for p in response.data["results"]]

        assert test_second_published_post.pk in ids
        assert test_published_post.pk not in ids


@pytest.mark.django_db
class TestFeaturedPostsAdd:
    def test_add_publishes_to_featured(self, editor_client, test_published_post):
        response = editor_client.post(
            f"/api/v1/editor/featured/{test_published_post.slug}/add/"
        )
        assert response.status_code == 201
        test_published_post.refresh_from_db()
        assert test_published_post.is_featured is True
        assert test_published_post.featured_order is not None

    def test_add_already_featured_returns_400(self, editor_client, test_featured_post):
        response = editor_client.post(
            f"/api/v1/editor/featured/{test_featured_post.slug}/add/"
        )
        assert response.status_code == 400

    def test_add_draft_returns_404(self, editor_client, test_draft_post):
        response = editor_client.post(
            f"/api/v1/editor/featured/{test_draft_post.slug}/add/"
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestFeaturedPostsRemove:
    def test_remove_clears_featured(self, editor_client, test_featured_post):
        response = editor_client.delete(
            f"/api/v1/editor/featured/{test_featured_post.slug}/remove/"
        )
        assert response.status_code == 204
        test_featured_post.refresh_from_db()
        assert test_featured_post.is_featured is False
        assert test_featured_post.featured_order is None

    def test_remove_non_featured_returns_400(self, editor_client, test_published_post):
        response = editor_client.delete(
            f"/api/v1/editor/featured/{test_published_post.slug}/remove/"
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestFeaturedPostsReorder:
    def test_reorder_updates_featured_order(
        self, editor_client, test_author, test_category, test_featured_post
    ):
        second = Post.objects.create(
            author=test_author,
            title="Second Featured",
            body="<p>Body.</p>",
            category=test_category,
            status=Post.Status.PUBLISHED,
            published_at=timezone.now(),
            is_featured=True,
            featured_order=2,
        )

        response = editor_client.patch(
            "/api/v1/editor/featured/reorder/",
            {
                "items": [
                    {"id": test_featured_post.pk, "order": 5},
                    {"id": second.pk, "order": 1},
                ]
            },
            format="json",
        )
        assert response.status_code == 200

        test_featured_post.refresh_from_db()
        second.refresh_from_db()
        assert test_featured_post.featured_order == 5
        assert second.featured_order == 1

    def test_reorder_duplicate_ids_returns_400(self, editor_client, test_featured_post):
        response = editor_client.patch(
            "/api/v1/editor/featured/reorder/",
            {
                "items": [
                    {"id": test_featured_post.pk, "order": 0},
                    {"id": test_featured_post.pk, "order": 1},
                ]
            },
            format="json",
        )
        assert response.status_code == 400

    def test_reorder_unknown_id_returns_400(self, editor_client, test_featured_post):
        response = editor_client.patch(
            "/api/v1/editor/featured/reorder/",
            {"items": [{"id": 999_999, "order": 0}]},
            format="json",
        )
        assert response.status_code == 400
