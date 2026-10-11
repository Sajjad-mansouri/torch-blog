"""
Behavioral tests for notifications.services.

Two categories of tests live in this file:

1. Isolated service tests — they request `disconnect_interactions_signals`
   so the post_save receivers in interactions.signals do not fire.
   The service function under test is called explicitly, and the
   test asserts on exactly what that call produced.

2. Signal-driven tests — they create the triggering object (Comment,
   Like, CommentLike) via `.objects.create(...)` and assert that the
   signal wiring produced the expected Notification.

Keeping the two categories separate lets us test the service's
internal rules (self-suppression, dedup window, target=None branch)
without interference, while still verifying that the production
signal path works end-to-end.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from interactions.models import Comment, CommentLike, Like
from notifications.models import Notification
from notifications.services import (
    create_notification,
    notify_comment_like,
    notify_new_comment,
    notify_post_approved,
    notify_post_changes_requested,
    notify_post_like,
    notify_post_rejected,
    notify_reply,
)


# ==================================================================
# Helper
# ==================================================================
def _make_comment(post, author, parent=None):
    return Comment.objects.create(
        post=post,
        author=author,
        parent=parent,
        body="test comment",
        status=Comment.Status.APPROVED,
        is_deleted=False,
    )


# ==================================================================
# create_notification — isolated
# ==================================================================
@pytest.mark.django_db
class TestCreateNotification:
    def test_creates_notification_with_all_fields(
        self,
        disconnect_interactions_signals,
        test_user,
        test_author,
        test_published_post,
    ):
        n = create_notification(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
            target=test_published_post,
            url="/some-url/",
            message="Hi",
        )

        assert n is not None
        assert n.recipient == test_user
        assert n.actor == test_author
        assert n.verb == Notification.Verb.POST_LIKE
        assert n.target == test_published_post
        assert n.url == "/some-url/"
        assert n.message == "Hi"

    def test_self_notification_is_suppressed(
        self, disconnect_interactions_signals, test_user, test_published_post
    ):
        n = create_notification(
            recipient=test_user,
            actor=test_user,
            verb=Notification.Verb.POST_LIKE,
            target=test_published_post,
        )

        assert n is None
        assert Notification.objects.count() == 0

    def test_target_none_is_allowed(
        self, disconnect_interactions_signals, test_user, test_author
    ):
        n = create_notification(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.NEW_FOLLOWER,
        )

        assert n is not None
        assert n.target is None

    def test_same_actor_target_verb_within_window_is_deduplicated(
        self,
        disconnect_interactions_signals,
        test_user,
        test_author,
        test_published_post,
    ):
        first = create_notification(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
            target=test_published_post,
        )
        second = create_notification(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
            target=test_published_post,
        )

        assert first is not None
        assert second is None
        assert Notification.objects.count() == 1

    def test_dedup_is_per_verb(
        self,
        disconnect_interactions_signals,
        test_user,
        test_author,
        test_published_post,
    ):
        create_notification(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
            target=test_published_post,
        )
        second = create_notification(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.NEW_COMMENT,
            target=test_published_post,
        )

        assert second is not None

    def test_dedup_is_per_actor(
        self,
        disconnect_interactions_signals,
        test_user,
        test_author,
        test_other_author,
        test_published_post,
    ):
        create_notification(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
            target=test_published_post,
        )
        second = create_notification(
            recipient=test_user,
            actor=test_other_author,
            verb=Notification.Verb.POST_LIKE,
            target=test_published_post,
        )

        assert second is not None

    def test_dedup_is_per_recipient(
        self,
        disconnect_interactions_signals,
        test_user,
        test_editor,
        test_author,
        test_published_post,
    ):
        create_notification(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
            target=test_published_post,
        )
        second = create_notification(
            recipient=test_editor,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
            target=test_published_post,
        )

        assert second is not None

    def test_dedup_window_expiry(
        self,
        disconnect_interactions_signals,
        test_user,
        test_author,
        test_published_post,
    ):
        first = create_notification(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
            target=test_published_post,
        )
        Notification.objects.filter(pk=first.pk).update(
            created_at=timezone.now() - timedelta(minutes=6)
        )

        second = create_notification(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
            target=test_published_post,
        )

        assert second is not None
        assert Notification.objects.count() == 2

    def test_no_target_skips_dedup(
        self, disconnect_interactions_signals, test_user, test_author
    ):
        first = create_notification(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.NEW_FOLLOWER,
        )
        second = create_notification(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.NEW_FOLLOWER,
        )

        assert first is not None
        assert second is not None
        assert Notification.objects.count() == 2


# ==================================================================
# notify_new_comment — isolated
# ==================================================================
@pytest.mark.django_db
class TestNotifyNewComment:
    def test_notifies_post_author(
        self, disconnect_interactions_signals, test_published_post, test_user
    ):
        comment = _make_comment(test_published_post, test_user)

        n = notify_new_comment(comment)

        assert n is not None
        assert n.recipient == test_published_post.author
        assert n.actor == test_user
        assert n.verb == Notification.Verb.NEW_COMMENT
        assert n.target == comment
        assert str(comment.id) in n.url

    def test_self_comment_is_suppressed(
        self, disconnect_interactions_signals, test_published_post
    ):
        comment = _make_comment(test_published_post, test_published_post.author)

        n = notify_new_comment(comment)

        assert n is None
        assert Notification.objects.count() == 0


# ==================================================================
# notify_reply — isolated
# ==================================================================
@pytest.mark.django_db
class TestNotifyReply:
    def test_notifies_parent_author_and_post_author(
        self,
        disconnect_interactions_signals,
        test_published_post,
        test_approved_comment,
        test_other_author,
    ):
        reply = _make_comment(
            test_published_post,
            test_other_author,
            parent=test_approved_comment,
        )

        notify_reply(reply)

        recipients = set(Notification.objects.values_list("recipient_id", flat=True))
        assert test_approved_comment.author_id in recipients
        assert test_published_post.author_id in recipients

    def test_actor_is_excluded(
        self,
        disconnect_interactions_signals,
        test_published_post,
        test_approved_comment,
    ):
        reply = _make_comment(
            test_published_post,
            test_published_post.author,
            parent=test_approved_comment,
        )

        notify_reply(reply)

        recipients = set(Notification.objects.values_list("recipient_id", flat=True))
        assert test_published_post.author_id not in recipients
        assert test_approved_comment.author_id in recipients

    def test_dedup_when_parent_author_is_also_post_author(
        self, disconnect_interactions_signals, test_published_post, test_user
    ):
        parent = _make_comment(test_published_post, test_published_post.author)
        reply = _make_comment(test_published_post, test_user, parent=parent)

        notify_reply(reply)

        assert Notification.objects.count() == 1
        assert Notification.objects.get().recipient == test_published_post.author


# ==================================================================
# notify_post_like — isolated
# ==================================================================
@pytest.mark.django_db
class TestNotifyPostLike:
    def test_notifies_post_author(
        self, disconnect_interactions_signals, test_user, test_published_post
    ):
        like = Like.objects.create(user=test_user, post=test_published_post)

        n = notify_post_like(like)

        assert n is not None
        assert n.recipient == test_published_post.author
        assert n.actor == test_user
        assert n.verb == Notification.Verb.POST_LIKE
        assert n.target == test_published_post

    def test_self_like_is_suppressed(
        self, disconnect_interactions_signals, test_published_post
    ):
        like = Like.objects.create(
            user=test_published_post.author, post=test_published_post
        )

        n = notify_post_like(like)

        assert n is None


# ==================================================================
# notify_comment_like — isolated
# ==================================================================
@pytest.mark.django_db
class TestNotifyCommentLike:
    def test_notifies_comment_author(
        self, disconnect_interactions_signals, test_other_author, test_approved_comment
    ):
        cl = CommentLike.objects.create(
            user=test_other_author, comment=test_approved_comment
        )

        n = notify_comment_like(cl)

        assert n is not None
        assert n.recipient == test_approved_comment.author
        assert n.actor == test_other_author
        assert n.verb == Notification.Verb.COMMENT_LIKE
        assert n.target == test_approved_comment

    def test_self_like_is_suppressed(
        self, disconnect_interactions_signals, test_approved_comment
    ):
        cl = CommentLike.objects.create(
            user=test_approved_comment.author, comment=test_approved_comment
        )

        n = notify_comment_like(cl)

        assert n is None


# ==================================================================
# notify_post_approved / rejected / changes_requested — isolated
# ==================================================================
@pytest.mark.django_db
class TestNotifyPostApproved:
    def test_notifies_author(
        self, disconnect_interactions_signals, test_pending_post, test_editor
    ):
        n = notify_post_approved(test_pending_post, test_editor)

        assert n is not None
        assert n.recipient == test_pending_post.author
        assert n.actor == test_editor
        assert n.verb == Notification.Verb.POST_APPROVED
        assert n.target == test_pending_post
        assert test_pending_post.title in n.message


@pytest.mark.django_db
class TestNotifyPostRejected:
    def test_notifies_author_with_reason_in_message(
        self, disconnect_interactions_signals, test_pending_post, test_editor
    ):
        n = notify_post_rejected(test_pending_post, test_editor, "off-topic")

        assert n is not None
        assert n.recipient == test_pending_post.author
        assert n.actor == test_editor
        assert n.verb == Notification.Verb.POST_REJECTED
        assert "off-topic" in n.message


@pytest.mark.django_db
class TestNotifyPostChangesRequested:
    def test_notifies_author_with_note_in_message(
        self, disconnect_interactions_signals, test_pending_post, test_editor
    ):
        n = notify_post_changes_requested(
            test_pending_post, test_editor, "tighten intro"
        )

        assert n is not None
        assert n.recipient == test_pending_post.author
        assert n.actor == test_editor
        assert n.verb == Notification.Verb.POST_CHANGES_REQUESTED
        assert "tighten intro" in n.message


# ==================================================================
# Signal-driven tests — do NOT request disconnect_interactions_signals
# ==================================================================
@pytest.mark.django_db
class TestSignalDrivenComment:
    def test_creating_a_comment_creates_a_notification(
        self, test_published_post, test_user
    ):
        # Signals are active here.
        _make_comment(test_published_post, test_user)

        assert Notification.objects.count() == 1
        n = Notification.objects.get()
        assert n.verb == Notification.Verb.NEW_COMMENT
        assert n.recipient == test_published_post.author

    def test_self_comment_creates_no_notification(self, test_published_post):
        _make_comment(test_published_post, test_published_post.author)

        assert Notification.objects.count() == 0

    def test_pending_comment_creates_no_notification(
        self, test_published_post, test_user
    ):
        Comment.objects.create(
            post=test_published_post,
            author=test_user,
            body="pending",
            status=Comment.Status.PENDING,
            is_deleted=False,
        )
        assert Notification.objects.count() == 0

    def test_reply_creates_notification_for_parent_author_and_post_author(
        self, test_published_post, test_approved_comment, test_other_author
    ):
        _make_comment(
            test_published_post,
            test_other_author,
            parent=test_approved_comment,
        )

        recipients = set(Notification.objects.values_list("recipient_id", flat=True))
        assert test_approved_comment.author_id in recipients
        assert test_published_post.author_id in recipients


@pytest.mark.django_db
class TestSignalDrivenLike:
    def test_creating_a_like_creates_a_notification(
        self, test_user, test_published_post
    ):
        Like.objects.create(user=test_user, post=test_published_post)

        assert Notification.objects.count() == 1
        n = Notification.objects.get()
        assert n.verb == Notification.Verb.POST_LIKE
        assert n.recipient == test_published_post.author

    def test_self_like_creates_no_notification(self, test_published_post):
        Like.objects.create(user=test_published_post.author, post=test_published_post)
        assert Notification.objects.count() == 0


@pytest.mark.django_db
class TestSignalDrivenCommentLike:
    def test_creating_a_comment_like_creates_a_notification(
        self, test_other_author, test_approved_comment
    ):
        # The fixture itself fires the post_save signal and creates a
        # notification. Reset the table so the test observes only the
        # effect of the CommentLike creation.
        Notification.objects.all().delete()

        CommentLike.objects.create(
            user=test_other_author, comment=test_approved_comment
        )

        assert Notification.objects.count() == 1
        n = Notification.objects.get()
        assert n.verb == Notification.Verb.COMMENT_LIKE
        assert n.recipient == test_approved_comment.author

    def test_self_comment_like_creates_no_notification(self, test_approved_comment):
        Notification.objects.all().delete()

        CommentLike.objects.create(
            user=test_approved_comment.author, comment=test_approved_comment
        )
        assert Notification.objects.count() == 0
