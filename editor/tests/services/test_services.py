"""
Behavioral tests for editor.services.

Coverage:
- approve_post: pending-only, published transition, published_at
  set-if-missing, review metadata, rejection/note cleared, and the
  POST_APPROVED notification side effect.
- reject_post: pending and changes_requested both allowed, reason
  required, reason stripped, other statuses rejected, POST_REJECTED
  notification.
- request_changes: pending-only, note required, note stripped,
  POST_CHANGES_REQUESTED notification.
- unpublish_post: published-only, reason optional, no notification.
- Atomicity: a failed transition leaves the post unchanged.

Notifications are created explicitly by these services (there are
no post_save signals on Post), so each test can assert on exactly
what was created.
"""

import pytest

from blog.models import Post
from editor.api.services import (
    approve_post,
    reject_post,
    request_changes,
    unpublish_post,
)
from notifications.models import Notification


# ==================================================================
# approve_post
# ==================================================================
@pytest.mark.django_db
class TestApprovePost:
    def test_happy_path_transitions_to_published(self, test_pending_post, test_editor):
        approve_post(test_pending_post, test_editor)
        test_pending_post.refresh_from_db()

        assert test_pending_post.status == Post.Status.PUBLISHED

    def test_sets_reviewed_by_and_reviewed_at(self, test_pending_post, test_editor):
        approve_post(test_pending_post, test_editor)
        test_pending_post.refresh_from_db()

        assert test_pending_post.reviewed_by == test_editor
        assert test_pending_post.reviewed_at is not None

    def test_sets_published_at_if_missing(self, test_pending_post, test_editor):
        assert test_pending_post.published_at is None

        approve_post(test_pending_post, test_editor)
        test_pending_post.refresh_from_db()

        assert test_pending_post.published_at is not None

    def test_preserves_existing_published_at(
        self, test_author, test_category, test_editor
    ):
        from django.utils import timezone

        original = timezone.now() - timezone.timedelta(days=3)
        post = Post.objects.create(
            author=test_author,
            title="Already had published_at",
            body="<p>Body.</p>",
            category=test_category,
            status=Post.Status.PENDING,
            published_at=original,
        )

        approve_post(post, test_editor)
        post.refresh_from_db()

        assert post.published_at == original

    def test_clears_rejection_reason_and_changes_note(
        self, test_author, test_category, test_editor
    ):
        post = Post.objects.create(
            author=test_author,
            title="Has stale fields",
            body="<p>Body.</p>",
            category=test_category,
            status=Post.Status.PENDING,
            rejection_reason="old rejection",
            changes_requested_note="old note",
        )

        approve_post(post, test_editor)
        post.refresh_from_db()

        assert post.rejection_reason == ""
        assert post.changes_requested_note == ""

    def test_sends_post_approved_notification(self, test_pending_post, test_editor):
        approve_post(test_pending_post, test_editor)

        assert Notification.objects.count() == 1
        n = Notification.objects.get()
        assert n.verb == Notification.Verb.POST_APPROVED
        assert n.recipient == test_pending_post.author
        assert n.actor == test_editor

    def test_non_pending_status_raises_value_error(self, test_draft_post, test_editor):
        with pytest.raises(ValueError):
            approve_post(test_draft_post, test_editor)

    def test_published_status_raises_value_error(
        self, test_published_post, test_editor
    ):
        with pytest.raises(ValueError):
            approve_post(test_published_post, test_editor)

    def test_post_is_unchanged_after_failed_approval(
        self, test_draft_post, test_editor
    ):
        original_status = test_draft_post.status

        with pytest.raises(ValueError):
            approve_post(test_draft_post, test_editor)

        test_draft_post.refresh_from_db()
        assert test_draft_post.status == original_status
        assert Notification.objects.count() == 0


# ==================================================================
# reject_post
# ==================================================================
@pytest.mark.django_db
class TestRejectPost:
    def test_pending_can_be_rejected(self, test_pending_post, test_editor):
        reject_post(test_pending_post, test_editor, "off-topic")
        test_pending_post.refresh_from_db()

        assert test_pending_post.status == Post.Status.REJECTED

    def test_changes_requested_can_be_rejected(
        self, test_author, test_category, test_editor
    ):
        post = Post.objects.create(
            author=test_author,
            title="A Post Needing Changes",
            body="<p>Body.</p>",
            category=test_category,
            status=Post.Status.CHANGES_REQUESTED,
            changes_requested_note="Please tighten the introduction.",
        )
        reject_post(post, test_editor, "still off")
        post.refresh_from_db()

        assert post.status == Post.Status.REJECTED

    def test_sets_reviewer_and_reviewed_at(self, test_pending_post, test_editor):
        reject_post(test_pending_post, test_editor, "reason")
        test_pending_post.refresh_from_db()

        assert test_pending_post.reviewed_by == test_editor
        assert test_pending_post.reviewed_at is not None

    def test_stores_stripped_reason(self, test_pending_post, test_editor):
        reject_post(test_pending_post, test_editor, "  off-topic  ")
        test_pending_post.refresh_from_db()

        assert test_pending_post.rejection_reason == "off-topic"

    def test_clears_changes_requested_note(self, test_pending_post, test_editor):
        test_pending_post.changes_requested_note = "old note"
        test_pending_post.save(update_fields=["changes_requested_note"])

        reject_post(test_pending_post, test_editor, "reason")
        test_pending_post.refresh_from_db()

        assert test_pending_post.changes_requested_note == ""

    def test_empty_reason_raises_value_error(self, test_pending_post, test_editor):
        with pytest.raises(ValueError):
            reject_post(test_pending_post, test_editor, "")

    def test_whitespace_only_reason_raises_value_error(
        self, test_pending_post, test_editor
    ):
        with pytest.raises(ValueError):
            reject_post(test_pending_post, test_editor, "   \t\n")

    def test_draft_status_raises_value_error(self, test_draft_post, test_editor):
        with pytest.raises(ValueError):
            reject_post(test_draft_post, test_editor, "reason")

    def test_published_status_raises_value_error(
        self, test_published_post, test_editor
    ):
        with pytest.raises(ValueError):
            reject_post(test_published_post, test_editor, "reason")

    def test_sends_post_rejected_notification(self, test_pending_post, test_editor):
        reject_post(test_pending_post, test_editor, "off-topic")

        assert Notification.objects.count() == 1
        n = Notification.objects.get()
        assert n.verb == Notification.Verb.POST_REJECTED
        assert n.recipient == test_pending_post.author
        assert n.actor == test_editor
        assert "off-topic" in n.message

    def test_post_is_unchanged_after_failed_rejection(
        self, test_draft_post, test_editor
    ):
        original_status = test_draft_post.status

        with pytest.raises(ValueError):
            reject_post(test_draft_post, test_editor, "reason")

        test_draft_post.refresh_from_db()
        assert test_draft_post.status == original_status
        assert Notification.objects.count() == 0


# ==================================================================
# request_changes
# ==================================================================
@pytest.mark.django_db
class TestRequestChanges:
    def test_pending_transitions_to_changes_requested(
        self, test_pending_post, test_editor
    ):
        request_changes(test_pending_post, test_editor, "tighten intro")
        test_pending_post.refresh_from_db()

        assert test_pending_post.status == Post.Status.CHANGES_REQUESTED

    def test_sets_reviewer_and_reviewed_at(self, test_pending_post, test_editor):
        request_changes(test_pending_post, test_editor, "note")
        test_pending_post.refresh_from_db()

        assert test_pending_post.reviewed_by == test_editor
        assert test_pending_post.reviewed_at is not None

    def test_stores_stripped_note(self, test_pending_post, test_editor):
        request_changes(test_pending_post, test_editor, "  tighten  ")
        test_pending_post.refresh_from_db()

        assert test_pending_post.changes_requested_note == "tighten"

    def test_clears_rejection_reason(self, test_pending_post, test_editor):
        test_pending_post.rejection_reason = "old"
        test_pending_post.save(update_fields=["rejection_reason"])

        request_changes(test_pending_post, test_editor, "note")
        test_pending_post.refresh_from_db()

        assert test_pending_post.rejection_reason == ""

    def test_empty_note_raises_value_error(self, test_pending_post, test_editor):
        with pytest.raises(ValueError):
            request_changes(test_pending_post, test_editor, "")

    def test_whitespace_only_note_raises_value_error(
        self, test_pending_post, test_editor
    ):
        with pytest.raises(ValueError):
            request_changes(test_pending_post, test_editor, "   ")

    def test_draft_status_raises_value_error(self, test_draft_post, test_editor):
        with pytest.raises(ValueError):
            request_changes(test_draft_post, test_editor, "note")

    def test_published_status_raises_value_error(
        self, test_published_post, test_editor
    ):
        with pytest.raises(ValueError):
            request_changes(test_published_post, test_editor, "note")

    def test_sends_post_changes_requested_notification(
        self, test_pending_post, test_editor
    ):
        request_changes(test_pending_post, test_editor, "tighten intro")

        assert Notification.objects.count() == 1
        n = Notification.objects.get()
        assert n.verb == Notification.Verb.POST_CHANGES_REQUESTED
        assert n.recipient == test_pending_post.author
        assert n.actor == test_editor
        assert "tighten intro" in n.message

    def test_post_is_unchanged_after_failed_request_changes(
        self, test_draft_post, test_editor
    ):
        original_status = test_draft_post.status

        with pytest.raises(ValueError):
            request_changes(test_draft_post, test_editor, "note")

        test_draft_post.refresh_from_db()
        assert test_draft_post.status == original_status
        assert Notification.objects.count() == 0


# ==================================================================
# unpublish_post
# ==================================================================
@pytest.mark.django_db
class TestUnpublishPost:
    def test_published_transitions_to_unpublished(
        self, test_published_post, test_editor
    ):
        unpublish_post(test_published_post, test_editor, "needs update")
        test_published_post.refresh_from_db()

        assert test_published_post.status == Post.Status.UNPUBLISHED

    def test_sets_reviewer_and_reviewed_at(self, test_published_post, test_editor):
        unpublish_post(test_published_post, test_editor)
        test_published_post.refresh_from_db()

        assert test_published_post.reviewed_by == test_editor
        assert test_published_post.reviewed_at is not None

    def test_reason_is_optional(self, test_published_post, test_editor):
        unpublish_post(test_published_post, test_editor)
        test_published_post.refresh_from_db()

        assert test_published_post.rejection_reason == ""

    def test_reason_is_stripped_when_provided(self, test_published_post, test_editor):
        unpublish_post(test_published_post, test_editor, "  reason  ")
        test_published_post.refresh_from_db()

        assert test_published_post.rejection_reason == "reason"

    def test_draft_status_raises_value_error(self, test_draft_post, test_editor):
        with pytest.raises(ValueError):
            unpublish_post(test_draft_post, test_editor)

    def test_pending_status_raises_value_error(self, test_pending_post, test_editor):
        with pytest.raises(ValueError):
            unpublish_post(test_pending_post, test_editor)

    def test_unpublished_status_raises_value_error(
        self, test_author, test_category, test_editor
    ):
        post = Post.objects.create(
            author=test_author,
            title="Already unpublished",
            body="<p>Body.</p>",
            category=test_category,
            status=Post.Status.UNPUBLISHED,
        )
        with pytest.raises(ValueError):
            unpublish_post(post, test_editor)

    def test_sends_no_notification(self, test_published_post, test_editor):
        """
        Unlike approve/reject/request_changes, unpublish_post does
        not call any notify_* service. Documented current behavior.
        """
        unpublish_post(test_published_post, test_editor, "reason")

        assert Notification.objects.count() == 0

    def test_post_is_unchanged_after_failed_unpublish(
        self, test_draft_post, test_editor
    ):
        original_status = test_draft_post.status

        with pytest.raises(ValueError):
            unpublish_post(test_draft_post, test_editor)

        test_draft_post.refresh_from_db()
        assert test_draft_post.status == original_status
