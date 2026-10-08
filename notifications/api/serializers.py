# notifications/serializers.py
from rest_framework import serializers

from notifications.models import Notification


class ActorBriefSerializer(serializers.Serializer):
    """
    Minimal info about the user who triggered the notification.
    Uses User model properties. Returns null if the actor was deleted.
    """

    id = serializers.IntegerField(read_only=True, allow_null=True)
    username = serializers.CharField(read_only=True, allow_null=True)
    display_name = serializers.CharField(read_only=True, allow_null=True)
    avatar_url = serializers.SerializerMethodField()

    def get_avatar_url(self, obj):
        if obj is None:
            return None
        request = self.context.get("request")
        url = obj.avatar_url
        if request is not None:
            return request.build_absolute_uri(url)
        return url


class NotificationSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for a notification.

    Exposes:
    - actor (nested brief)
    - verb + verb_display (machine + human)
    - target_type / target_id (for the frontend to build links)
    - message (cached text, may be blank)
    - url (cached deep link, may be blank)
    - is_read, read_at, created_at
    """

    actor = serializers.SerializerMethodField()
    verb_display = serializers.CharField(source="get_verb_display", read_only=True)
    target_type_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
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
        ]

    def get_actor(self, obj):
        if obj.actor is None:
            return None
        return ActorBriefSerializer(obj.actor, context=self.context).data

    def get_target_type_name(self, obj):
        """
        Return the model name (e.g., 'post', 'comment') for the
        frontend to switch on. Null if no target is set.
        """
        if obj.target_type_id is None:
            return None
        return obj.target_type.model
