"""
API tests for notifications.views.NotificationViewSet.

All endpoints are scoped by recipient=request.user. A user must never
see or modify another user's notifications.
"""

import pytest
from django.utils import timezone

from notifications.models import Notification


# ==================================================================
# List
# ==================================================================
@pytest.mark.django_db
class TestNotificationList:
    def test_anonymous_returns_401(self, api_client):
        response = api_client.get("/api/v1/notifications/")
        assert response.status_code == 401

    def test_returns_only_own_notifications(
        self, auth_client, test_user, test_author, test_other_author
    ):
        mine = Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
        )
        theirs = Notification.objects.create(
            recipient=test_other_author,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
        )

        response = auth_client.get("/api/v1/notifications/")
        ids = [n["id"] for n in response.data["results"]]

        assert mine.pk in ids
        assert theirs.pk not in ids

    def test_filter_by_is_read_true(self, auth_client, test_user, test_author):
        read = Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
            is_read=True,
            read_at=timezone.now(),
        )
        Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.NEW_COMMENT,
        )

        response = auth_client.get("/api/v1/notifications/", {"is_read": "true"})
        ids = [n["id"] for n in response.data["results"]]

        assert ids == [read.pk]

    def test_filter_by_is_read_false(self, auth_client, test_user, test_author):
        Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
            is_read=True,
            read_at=timezone.now(),
        )
        unread = Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.NEW_COMMENT,
        )

        response = auth_client.get("/api/v1/notifications/", {"is_read": "false"})
        ids = [n["id"] for n in response.data["results"]]

        assert ids == [unread.pk]

    def test_filter_by_verb(self, auth_client, test_user, test_author):
        like = Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
        )
        Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.NEW_COMMENT,
        )

        response = auth_client.get("/api/v1/notifications/", {"verb": "post_like"})
        ids = [n["id"] for n in response.data["results"]]

        assert ids == [like.pk]

    def test_invalid_verb_returns_400(self, auth_client):
        response = auth_client.get("/api/v1/notifications/", {"verb": "not-a-verb"})
        assert response.status_code == 400
        assert "verb" in response.data

    def test_documents_invalid_is_read_is_silently_treated_as_false(
        self, auth_client, test_user, test_author
    ):
        """
        `is_read=yes` evaluates to `False` in the filter, so the
        endpoint returns unread notifications silently, whereas
        an invalid `verb` returns 400. Documented inconsistency.
        """
        unread = Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
        )
        Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.NEW_COMMENT,
            is_read=True,
            read_at=timezone.now(),
        )

        response = auth_client.get("/api/v1/notifications/", {"is_read": "yes"})
        ids = [n["id"] for n in response.data["results"]]

        assert ids == [unread.pk]

    def test_ordering_newest_first(self, auth_client, test_user, test_author):
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

        response = auth_client.get("/api/v1/notifications/")
        ids = [n["id"] for n in response.data["results"]]

        assert ids == [second.pk, first.pk]


# ==================================================================
# Retrieve
# ==================================================================
@pytest.mark.django_db
class TestNotificationRetrieve:
    def test_own_notification_is_returned(self, auth_client, test_notification):
        response = auth_client.get(f"/api/v1/notifications/{test_notification.pk}/")

        assert response.status_code == 200
        assert response.data["id"] == test_notification.pk

    def test_other_users_notification_returns_404(
        self, auth_client, test_notification, test_other_author
    ):
        test_notification.recipient = test_other_author
        test_notification.save(update_fields=["recipient"])

        response = auth_client.get(f"/api/v1/notifications/{test_notification.pk}/")
        assert response.status_code == 404

    def test_anonymous_returns_401(self, api_client, test_notification):
        response = api_client.get(f"/api/v1/notifications/{test_notification.pk}/")
        assert response.status_code == 401


# ==================================================================
# Destroy
# ==================================================================
@pytest.mark.django_db
class TestNotificationDestroy:
    def test_own_notification_is_deleted(self, auth_client, test_notification):
        pk = test_notification.pk
        response = auth_client.delete(f"/api/v1/notifications/{pk}/")

        assert response.status_code == 204
        assert not Notification.objects.filter(pk=pk).exists()

    def test_other_users_notification_returns_404(
        self, auth_client, test_notification, test_other_author
    ):
        test_notification.recipient = test_other_author
        test_notification.save(update_fields=["recipient"])

        response = auth_client.delete(f"/api/v1/notifications/{test_notification.pk}/")
        assert response.status_code == 404
        assert Notification.objects.filter(pk=test_notification.pk).exists()

    def test_anonymous_returns_401(self, api_client, test_notification):
        response = api_client.delete(f"/api/v1/notifications/{test_notification.pk}/")
        assert response.status_code == 401


# ==================================================================
# mark_read action
# ==================================================================
@pytest.mark.django_db
class TestNotificationMarkRead:
    def test_marks_own_notification_as_read(self, auth_client, test_notification):
        response = auth_client.post(
            f"/api/v1/notifications/{test_notification.pk}/read/"
        )

        assert response.status_code == 200
        test_notification.refresh_from_db()
        assert test_notification.is_read is True
        assert test_notification.read_at is not None

    def test_other_users_notification_returns_404(
        self, auth_client, test_notification, test_other_author
    ):
        test_notification.recipient = test_other_author
        test_notification.save(update_fields=["recipient"])

        response = auth_client.post(
            f"/api/v1/notifications/{test_notification.pk}/read/"
        )
        assert response.status_code == 404
        test_notification.refresh_from_db()
        assert test_notification.is_read is False

    def test_anonymous_returns_401(self, api_client, test_notification):
        response = api_client.post(
            f"/api/v1/notifications/{test_notification.pk}/read/"
        )
        assert response.status_code == 401


# ==================================================================
# read_all action
# ==================================================================
@pytest.mark.django_db
class TestNotificationReadAll:
    def test_marks_all_own_unread_as_read(self, auth_client, test_user, test_author):
        a = Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
        )
        b = Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.NEW_COMMENT,
        )

        response = auth_client.post("/api/v1/notifications/read-all/")

        assert response.status_code == 200
        assert response.data["updated"] == 2

        a.refresh_from_db()
        b.refresh_from_db()
        assert a.is_read is True
        assert b.is_read is True
        assert a.read_at is not None
        assert b.read_at is not None

    def test_does_not_touch_other_users_notifications(
        self, auth_client, test_user, test_author, test_other_author
    ):
        Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
        )
        theirs = Notification.objects.create(
            recipient=test_other_author,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
        )

        auth_client.post("/api/v1/notifications/read-all/")

        theirs.refresh_from_db()
        assert theirs.is_read is False

    def test_only_counts_unread(self, auth_client, test_user, test_author):
        Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
            is_read=True,
            read_at=timezone.now(),
        )
        Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.NEW_COMMENT,
        )

        response = auth_client.post("/api/v1/notifications/read-all/")
        assert response.data["updated"] == 1

    def test_anonymous_returns_401(self, api_client):
        response = api_client.post("/api/v1/notifications/read-all/")
        assert response.status_code == 401


# ==================================================================
# unread_count action
# ==================================================================
@pytest.mark.django_db
class TestNotificationUnreadCount:
    def test_counts_unread(self, auth_client, test_user, test_author):
        Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
        )
        Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.NEW_COMMENT,
        )
        Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.REPLY,
            is_read=True,
            read_at=timezone.now(),
        )

        response = auth_client.get("/api/v1/notifications/unread-count/")

        assert response.status_code == 200
        assert response.data["unread"] == 2

    def test_zero_when_no_unread(self, auth_client, test_user, test_author):
        Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
            is_read=True,
            read_at=timezone.now(),
        )

        response = auth_client.get("/api/v1/notifications/unread-count/")
        assert response.data["unread"] == 0

    def test_does_not_count_other_users(
        self, auth_client, test_user, test_author, test_other_author
    ):
        Notification.objects.create(
            recipient=test_other_author,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
        )

        response = auth_client.get("/api/v1/notifications/unread-count/")
        assert response.data["unread"] == 0

    def test_anonymous_returns_401(self, api_client):
        response = api_client.get("/api/v1/notifications/unread-count/")
        assert response.status_code == 401


# ==================================================================
# clear action
# ==================================================================
@pytest.mark.django_db
class TestNotificationClear:
    def test_deletes_only_own_notifications(
        self, auth_client, test_user, test_author, test_other_author
    ):
        Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
        )
        Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.NEW_COMMENT,
        )
        theirs = Notification.objects.create(
            recipient=test_other_author,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
        )

        response = auth_client.delete("/api/v1/notifications/clear/")

        assert response.status_code == 200
        assert response.data["deleted"] == 2
        assert Notification.objects.filter(recipient=test_user).count() == 0
        assert Notification.objects.filter(pk=theirs.pk).exists()

    def test_returns_zero_when_nothing_to_delete(self, auth_client):
        response = auth_client.delete("/api/v1/notifications/clear/")
        assert response.data["deleted"] == 0

    def test_anonymous_returns_401(self, api_client):
        response = api_client.delete("/api/v1/notifications/clear/")
        assert response.status_code == 401
