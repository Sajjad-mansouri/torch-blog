"""
Behavioral tests for notifications.serializers.
"""

import pytest

from notifications.api.serializers import (
    ActorBriefSerializer,
    NotificationSerializer,
)
from notifications.models import Notification


# ==================================================================
# ActorBriefSerializer
# ==================================================================
@pytest.mark.django_db
class TestActorBriefSerializer:
    def test_fields_with_request(self, test_user, api_request):
        data = ActorBriefSerializer(test_user, context={"request": api_request}).data

        assert data["id"] == test_user.pk
        assert data["username"] == test_user.username
        assert data["display_name"] == test_user.display_name
        assert data["avatar_url"].startswith("http://testserver/")

    def test_fields_without_request_returns_relative_avatar_url(self, test_user):
        data = ActorBriefSerializer(test_user).data
        assert data["avatar_url"] == "/static/img/default-avatar.jpg"


# ==================================================================
# NotificationSerializer
# ==================================================================
@pytest.mark.django_db
class TestNotificationSerializerShape:
    def test_includes_expected_fields(self, test_notification, api_request):
        data = NotificationSerializer(
            test_notification, context={"request": api_request}
        ).data

        for field in (
            "id",
            "actor",
            "verb",
            "verb_display",
            "target_type_name",
            "target_id",
            "message",
            "url",
            "is_read",
            "read_at",
            "created_at",
        ):
            assert field in data

    def test_verb_display_is_human_readable(self, test_notification, api_request):
        test_notification.verb = Notification.Verb.POST_LIKE
        test_notification.save(update_fields=["verb"])

        data = NotificationSerializer(
            test_notification, context={"request": api_request}
        ).data

        assert data["verb"] == "post_like"
        assert data["verb_display"] == "Post Like"


@pytest.mark.django_db
class TestNotificationSerializerActor:
    def test_actor_is_nested_brief(self, test_notification, api_request):
        data = NotificationSerializer(
            test_notification, context={"request": api_request}
        ).data

        assert data["actor"]["username"] == test_notification.actor.username
        assert "display_name" in data["actor"]

    def test_actor_none_when_set_to_none(self, test_notification, api_request):
        test_notification.actor = None
        test_notification.save(update_fields=["actor"])

        data = NotificationSerializer(
            test_notification, context={"request": api_request}
        ).data

        assert data["actor"] is None


@pytest.mark.django_db
class TestNotificationSerializerTargetTypeName:
    def test_none_when_no_target(self, test_notification, api_request):
        data = NotificationSerializer(
            test_notification, context={"request": api_request}
        ).data

        assert data["target_type_name"] is None
        assert data["target_id"] is None

    def test_model_name_for_post_target(
        self, test_user, test_author, test_published_post, api_request
    ):
        n = Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.POST_LIKE,
            target=test_published_post,
        )
        data = NotificationSerializer(n, context={"request": api_request}).data

        assert data["target_type_name"] == "post"
        assert data["target_id"] == test_published_post.pk

    def test_model_name_for_comment_target(
        self, test_user, test_author, test_approved_comment, api_request
    ):
        n = Notification.objects.create(
            recipient=test_user,
            actor=test_author,
            verb=Notification.Verb.NEW_COMMENT,
            target=test_approved_comment,
        )
        data = NotificationSerializer(n, context={"request": api_request}).data

        assert data["target_type_name"] == "comment"
        assert data["target_id"] == test_approved_comment.pk
