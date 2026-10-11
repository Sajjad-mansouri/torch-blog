"""
Behavioral tests for notifications.models.Notification.

Coverage:
- __str__ format.
- mark_as_read — flips is_read, sets read_at, idempotency.
- Meta.ordering.
- recipient CASCADE, actor SET_NULL.
- Generic ForeignKey target assignment and retrieval.
- Verb enum values.

Assertions reflect the actual observable behavior of the current
implementation.
"""

import pytest

from notifications.models import Notification


# ==================================================================
# __str__
# ==================================================================
@pytest.mark.django_db
class TestNotificationStr:
    def test_includes_recipient_username_and_verb(self, test_notification):
        text = str(test_notification)

        assert test_notification.recipient.username in text
        assert test_notification.verb in text


# ==================================================================
# mark_as_read
# ==================================================================
@pytest.mark.django_db
class TestMarkAsRead:
    def test_flips_flag_and_sets_read_at(self, test_notification):
        assert test_notification.is_read is False
        assert test_notification.read_at is None

        test_notification.mark_as_read()
        test_notification.refresh_from_db()

        assert test_notification.is_read is True
        assert test_notification.read_at is not None

    def test_idempotent_second_call_does_not_change_read_at(self, test_notification):
        test_notification.mark_as_read()
        test_notification.refresh_from_db()
        first_read_at = test_notification.read_at

        test_notification.mark_as_read()
        test_notification.refresh_from_db()

        # read_at is not touched on the second call, because the
        # method early-returns when is_read is already True.
        assert test_notification.read_at == first_read_at

    def test_does_nothing_when_already_read(self, test_notification):
        # Simulate the "already read" state directly.
        test_notification.is_read = True
        test_notification.save(update_fields=["is_read"])

        test_notification.mark_as_read()
        test_notification.refresh_from_db()

        # read_at is not set because the guard short-circuits.
        assert test_notification.read_at is None


# ==================================================================
# Meta.ordering
# ==================================================================
@pytest.mark.django_db
class TestNotificationOrdering:
    def test_ordering_is_newest_first(self, test_user, test_author):
        first = Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
        )
        second = Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.NEW_COMMENT,
        )

        results = list(Notification.objects.filter(recipient=test_user))
        assert results[0] == second
        assert results[1] == first


# ==================================================================
# Cascades
# ==================================================================
@pytest.mark.django_db
class TestNotificationCascades:
    def test_deleting_recipient_cascades_to_notifications(
        self, test_notification, test_user
    ):
        pk = test_notification.pk
        test_user.delete()

        assert not Notification.objects.filter(pk=pk).exists()

    def test_deleting_actor_sets_actor_null(self, test_notification, test_author):
        pk = test_notification.pk
        test_author.delete()

        notification = Notification.objects.get(pk=pk)
        assert notification.actor is None
        assert notification.recipient is not None


# ==================================================================
# Generic ForeignKey target
# ==================================================================
@pytest.mark.django_db
class TestNotificationGenericTarget:
    def test_target_is_none_by_default(self, test_notification):
        assert test_notification.target is None
        assert test_notification.target_id is None
        assert test_notification.target_type_id is None

    def test_can_assign_a_post_as_target(
        self, test_user, test_author, test_published_post
    ):
        n = Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
            target=test_published_post,
        )

        refreshed = Notification.objects.get(pk=n.pk)
        assert refreshed.target == test_published_post
        assert refreshed.target_id == test_published_post.pk
        assert refreshed.target_type.model == "post"

    def test_can_assign_a_comment_as_target(
        self, test_user, test_author, test_approved_comment
    ):
        n = Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.NEW_COMMENT,
            target=test_approved_comment,
        )

        refreshed = Notification.objects.get(pk=n.pk)
        assert refreshed.target == test_approved_comment
        assert refreshed.target_type.model == "comment"

    def test_target_deleted_leaves_dangling_reference(
        self, test_user, test_author, test_published_post
    ):
        """
        The generic FK does not enforce referential integrity at the
        DB level. Deleting the target leaves target_type and
        target_id in place; accessing `.target` returns None because
        the referenced row is gone.
        """
        n = Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
            target=test_published_post,
        )
        pk = n.pk
        post_pk = test_published_post.pk
        test_published_post.delete()

        refreshed = Notification.objects.get(pk=pk)
        assert refreshed.target_id == post_pk
        assert refreshed.target is None


# ==================================================================
# Verb enum
# ==================================================================
@pytest.mark.django_db
class TestVerbEnum:
    def test_all_declared_verbs_are_choice_values(self):
        declared = {
            "new_comment",
            "reply",
            "post_like",
            "comment_like",
            "post_approved",
            "post_rejected",
            "post_changes_requested",
            "post_published",
            "new_follower",
        }
        values = {choice[0] for choice in Notification.Verb.choices}

        assert values == declared

    def test_default_message_and_url_are_blank(self, test_user, test_author):
        n = Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.NEW_COMMENT,
        )
        assert n.message == ""
        assert n.url == ""


# ==================================================================
# Boolean default and timestamp
# ==================================================================
@pytest.mark.django_db
class TestNotificationDefaults:
    def test_new_notification_is_unread(self, test_user, test_author):
        n = Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.NEW_COMMENT,
        )
        assert n.is_read is False
        assert n.read_at is None

    def test_created_at_is_set_automatically(self, test_user, test_author):
        n = Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.NEW_COMMENT,
        )
        assert n.created_at is not None
