# core/serializers.py
from rest_framework import serializers

from core.models import SiteSettings


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
