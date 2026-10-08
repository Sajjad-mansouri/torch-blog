# core/serializers_landing.py
from rest_framework import serializers

from core.models import (
    ApiEndpoint,
    ContactMessage,
    FeatureGroup,
    FeatureItem,
    RoadmapItem,
    RoadmapPhase,
    Screenshot,
    SiteSettings,
    SocialLink,
    Statistic,
    TechCategory,
    TechItem,
)

# ============================================================
# Media URL helper
# ============================================================


def absolute_url(request, image):
    """Return an absolute URL for an image, or None."""
    if not image or not hasattr(image, "url"):
        return None
    url = image.url
    if request is not None:
        return request.build_absolute_uri(url)
    return url


# ============================================================
# Tech stack
# ============================================================


class TechItemSerializer(serializers.ModelSerializer):
    icon_image_url = serializers.SerializerMethodField()

    class Meta:
        model = TechItem
        fields = [
            "id",
            "name",
            "description",
            "icon",
            "icon_image_url",
            "url",
            "version",
            "order",
        ]

    def get_icon_image_url(self, obj):
        return absolute_url(self.context.get("request"), obj.icon_image)


class TechCategorySerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = TechCategory
        fields = ["id", "name", "slug", "icon", "order", "items"]

    def get_items(self, obj):
        items = obj.items.filter(is_active=True).order_by("order", "name")
        return TechItemSerializer(items, many=True, context=self.context).data


# ============================================================
# Features
# ============================================================


class FeatureItemSerializer(serializers.ModelSerializer):
    icon_image_url = serializers.SerializerMethodField()

    class Meta:
        model = FeatureItem
        fields = [
            "id",
            "title",
            "description",
            "icon",
            "icon_image_url",
            "color",
            "order",
        ]

    def get_icon_image_url(self, obj):
        return absolute_url(self.context.get("request"), obj.icon_image)


class FeatureGroupSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = FeatureGroup
        fields = ["id", "title", "slug", "description", "icon", "order", "items"]

    def get_items(self, obj):
        items = obj.items.filter(is_active=True).order_by("order", "title")
        return FeatureItemSerializer(items, many=True, context=self.context).data


# ============================================================
# API endpoints
# ============================================================


class ApiEndpointSerializer(serializers.ModelSerializer):
    method_display = serializers.CharField(source="get_method_display", read_only=True)

    class Meta:
        model = ApiEndpoint
        fields = [
            "id",
            "method",
            "method_display",
            "path",
            "description",
            "auth_required",
            "group",
            "order",
        ]


# ============================================================
# Screenshots
# ============================================================


class ScreenshotSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Screenshot
        fields = ["id", "title", "caption", "image_url", "order"]

    def get_image_url(self, obj):
        return absolute_url(self.context.get("request"), obj.image)


# ============================================================
# Roadmap
# ============================================================


class RoadmapItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoadmapItem
        fields = ["id", "text", "order"]


class RoadmapPhaseSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    items = serializers.SerializerMethodField()

    class Meta:
        model = RoadmapPhase
        fields = [
            "id",
            "title",
            "status",
            "status_display",
            "description",
            "order",
            "items",
        ]

    def get_items(self, obj):
        items = obj.items.order_by("order", "text")
        return RoadmapItemSerializer(items, many=True).data


# ============================================================
# Stats and social links
# ============================================================


class StatisticSerializer(serializers.ModelSerializer):
    class Meta:
        model = Statistic
        fields = ["id", "label", "value", "icon", "order"]


class SocialLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialLink
        fields = ["id", "platform", "url", "icon", "username", "order"]


# ============================================================
# Landing aggregate response
# ============================================================


class ProjectInfoSerializer(serializers.ModelSerializer):
    """
    Read-only view of the project-level fields on SiteSettings.
    """

    class Meta:
        model = SiteSettings
        fields = [
            "project_name",
            "project_tagline",
            "project_description",
            "project_goal",
            "project_repo_url",
            "project_demo_url",
            "contact_email",
            "footer_text",
            "site_title",
            "tagline",
        ]


class LandingSerializer(serializers.Serializer):
    """
    The entire landing page payload.
    """

    project = ProjectInfoSerializer(read_only=True)
    tech_stack = TechCategorySerializer(many=True, read_only=True)
    features = FeatureGroupSerializer(many=True, read_only=True)
    api_endpoints = ApiEndpointSerializer(many=True, read_only=True)
    screenshots = ScreenshotSerializer(many=True, read_only=True)
    roadmap = RoadmapPhaseSerializer(many=True, read_only=True)
    stats = StatisticSerializer(many=True, read_only=True)
    social_links = SocialLinkSerializer(many=True, read_only=True)


# ============================================================
# Contact
# ============================================================


class ContactMessageSerializer(serializers.ModelSerializer):
    """
    Write-only serializer for the contact form.
    """

    # Honeypot: bots fill every field. Real users leave it blank.
    website = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
        help_text="Leave this blank.",
    )

    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message", "website"]

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters.")
        return value

    def validate_subject(self, value):
        return value.strip() if value else value

    def validate_message(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError("Message must be at least 10 characters.")
        return value

    def validate(self, attrs):
        # Honeypot check: if filled, silently reject (return 200 but skip save)
        if attrs.get("website"):
            raise serializers.ValidationError({"detail": "Invalid submission."})
        return attrs
