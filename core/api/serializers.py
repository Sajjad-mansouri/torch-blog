# core/serializers.py
from rest_framework import serializers

from core.models import ActivityLog, SiteSettings


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = [
            "site_title",
            "tagline",
            "logo",
            "favicon",
            "hero_text",
            "hero_cta_text",
            "hero_cta_link",
            "posts_per_page",
            "featured_count",
            "footer_text",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]


class ActivityLogUserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True, allow_null=True)
    username = serializers.CharField(read_only=True, allow_null=True)
    display_name = serializers.CharField(read_only=True, allow_null=True)


class ActivityLogSerializer(serializers.ModelSerializer):
    user = ActivityLogUserSerializer(read_only=True)
    action_display = serializers.CharField(
        source="get_action_display",
        read_only=True,
    )

    class Meta:
        model = ActivityLog
        fields = [
            "id",
            "user",
            "action",
            "action_display",
            "target_type",
            "target_id",
            "description",
            "metadata",
            "ip_address",
            "created_at",
        ]
