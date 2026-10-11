"""
Behavioral tests for core serializers.

Coverage:
- SiteSettingsSerializer
- ActivityLogUserSerializer / ActivityLogSerializer
- ContactMessageSerializer (including honeypot behavior)
- Landing serializers: TechCategory/TechItem, FeatureGroup/FeatureItem,
  ApiEndpoint, Screenshot, RoadmapPhase/RoadmapItem, Statistic,
  LandingSocialLink, ProjectInfo, LandingSerializer, ContactMessage
- The absolute_url helper
"""

import pytest

from core.api.serializers import (
    ActivityLogSerializer,
    ActivityLogUserSerializer,
    SiteSettingsSerializer,
)
from core.api.serializers_landing import (
    ApiEndpointSerializer,
    ContactMessageSerializer,
    FeatureGroupSerializer,
    FeatureItemSerializer,
    LandingSerializer,
    LandingSocialLinkSerializer,
    ProjectInfoSerializer,
    RoadmapItemSerializer,
    RoadmapPhaseSerializer,
    ScreenshotSerializer,
    StatisticSerializer,
    TechCategorySerializer,
    TechItemSerializer,
    absolute_url,
)
from core.models import (
    ActivityLog,
    ApiEndpoint,
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


# ==================================================================
# SiteSettingsSerializer
# ==================================================================
@pytest.mark.django_db
class TestSiteSettingsSerializer:
    def test_fields(self):
        s = SiteSettings.objects.create(site_title="My Site")
        data = SiteSettingsSerializer(s).data

        for field in (
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
        ):
            assert field in data

    def test_updated_at_is_read_only(self):
        s = SiteSettings.objects.create(site_title="My Site")
        serializer = SiteSettingsSerializer(
            s,
            data={"site_title": "New", "updated_at": "2020-01-01T00:00:00Z"},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        # updated_at was not accepted as input.
        assert "updated_at" not in serializer.validated_data


# ==================================================================
# ActivityLogUserSerializer / ActivityLogSerializer
# ==================================================================
@pytest.mark.django_db
class TestActivityLogUserSerializer:
    def test_fields(self, test_user):
        data = ActivityLogUserSerializer(test_user).data
        assert data["id"] == test_user.pk
        assert data["username"] == test_user.username
        assert data["display_name"] == test_user.display_name


@pytest.mark.django_db
class TestActivityLogSerializer:
    def test_shape(self, test_user):
        log = ActivityLog.objects.create(
            user=test_user,
            action=ActivityLog.Action.POST_CREATED,
            description="created a post",
        )
        data = ActivityLogSerializer(log).data

        for field in (
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
        ):
            assert field in data

    def test_action_display(self, test_user):
        log = ActivityLog.objects.create(
            user=test_user, action=ActivityLog.Action.POST_CREATED
        )
        data = ActivityLogSerializer(log).data

        assert data["action"] == "post_created"
        assert data["action_display"] == "Post Created"

    def test_user_is_nested(self, test_user):
        log = ActivityLog.objects.create(
            user=test_user, action=ActivityLog.Action.POST_CREATED
        )
        data = ActivityLogSerializer(log).data

        assert data["user"]["username"] == test_user.username

    def test_user_none_serializes_as_none(self):
        log = ActivityLog.objects.create(
            user=None, action=ActivityLog.Action.POST_CREATED
        )
        data = ActivityLogSerializer(log).data

        assert data["user"] is None


# ==================================================================
# ContactMessageSerializer
# ==================================================================
class TestContactMessageSerializer:
    def _payload(self, **overrides):
        payload = {
            "name": "Alice",
            "email": "alice@example.com",
            "subject": "Hello",
            "message": "This is a sufficiently long message.",
        }
        payload.update(overrides)
        return payload

    def test_valid_payload(self):
        serializer = ContactMessageSerializer(data=self._payload())
        assert serializer.is_valid(), serializer.errors

    def test_short_name_is_rejected(self):
        serializer = ContactMessageSerializer(data=self._payload(name="A"))
        assert not serializer.is_valid()
        assert "name" in serializer.errors

    def test_name_is_stripped(self):
        serializer = ContactMessageSerializer(data=self._payload(name="  Alice  "))
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["name"] == "Alice"

    def test_short_message_is_rejected(self):
        serializer = ContactMessageSerializer(data=self._payload(message="short"))
        assert not serializer.is_valid()
        assert "message" in serializer.errors

    def test_message_is_stripped(self):
        serializer = ContactMessageSerializer(
            data=self._payload(message="     This is a long enough message.     ")
        )
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["message"] == "This is a long enough message."

    def test_subject_is_stripped(self):
        serializer = ContactMessageSerializer(data=self._payload(subject="  Hello  "))
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["subject"] == "Hello"

    def test_subject_is_optional(self):
        payload = self._payload()
        payload.pop("subject")
        serializer = ContactMessageSerializer(data=payload)
        assert serializer.is_valid(), serializer.errors

    def test_honeypot_filled_sets_flag_and_removes_website(self):
        serializer = ContactMessageSerializer(data=self._payload(website="I am a bot"))
        assert serializer.is_valid(), serializer.errors
        # The honeypot value is removed from validated_data; the flag
        # records that the honeypot was tripped.
        assert serializer.validated_data["_honeypot_hit"] is True
        assert "website" not in serializer.validated_data

    def test_honeypot_blank_does_not_set_flag(self):
        serializer = ContactMessageSerializer(data=self._payload(website=""))
        assert serializer.is_valid(), serializer.errors
        assert "_honeypot_hit" not in serializer.validated_data

    def test_honeypot_omitted_does_not_set_flag(self):
        serializer = ContactMessageSerializer(data=self._payload())
        assert serializer.is_valid(), serializer.errors
        assert "_honeypot_hit" not in serializer.validated_data


# ==================================================================
# absolute_url helper
# ==================================================================
class TestAbsoluteUrl:
    def test_returns_none_for_none(self):
        assert absolute_url(None, None) is None

    def test_returns_none_for_empty_image(self):
        class Empty:
            pass

        assert absolute_url(None, Empty()) is None


# ==================================================================
# Tech stack serializers
# ==================================================================
@pytest.mark.django_db
class TestTechItemSerializer:
    def test_fields(self):
        c = TechCategory.objects.create(name="Backend", slug="backend")
        item = TechItem.objects.create(category=c, name="Django", description="x")

        data = TechItemSerializer(item).data

        for field in (
            "id",
            "name",
            "description",
            "icon",
            "icon_image_url",
            "url",
            "version",
            "order",
        ):
            assert field in data
        assert data["name"] == "Django"

    def test_icon_image_url_is_none_without_image(self):
        c = TechCategory.objects.create(name="Backend", slug="backend")
        item = TechItem.objects.create(category=c, name="Django")
        data = TechItemSerializer(item).data

        assert data["icon_image_url"] is None


@pytest.mark.django_db
class TestTechCategorySerializer:
    def test_includes_active_items(self):
        c = TechCategory.objects.create(name="Backend", slug="backend")
        TechItem.objects.create(category=c, name="Django", is_active=True)
        TechItem.objects.create(category=c, name="Old", is_active=False)

        data = TechCategorySerializer(c).data
        names = [i["name"] for i in data["items"]]

        assert "Django" in names
        assert "Old" not in names

    def test_items_ordered_by_order_then_name(self):
        c = TechCategory.objects.create(name="Backend", slug="backend")
        a = TechItem.objects.create(category=c, name="A", order=2)
        b = TechItem.objects.create(category=c, name="B", order=1)

        data = TechCategorySerializer(c).data
        ids = [i["id"] for i in data["items"]]

        assert ids.index(b.pk) < ids.index(a.pk)


# ==================================================================
# Feature serializers
# ==================================================================
@pytest.mark.django_db
class TestFeatureItemSerializer:
    def test_fields(self):
        g = FeatureGroup.objects.create(title="Editor", slug="editor")
        item = FeatureItem.objects.create(group=g, title="Rich Text", description="...")

        data = FeatureItemSerializer(item).data

        for field in (
            "id",
            "title",
            "description",
            "icon",
            "icon_image_url",
            "color",
            "order",
        ):
            assert field in data


@pytest.mark.django_db
class TestFeatureGroupSerializer:
    def test_includes_active_items(self):
        g = FeatureGroup.objects.create(title="Editor", slug="editor")
        FeatureItem.objects.create(
            group=g, title="Active", description="...", is_active=True
        )
        FeatureItem.objects.create(
            group=g, title="Inactive", description="...", is_active=False
        )

        data = FeatureGroupSerializer(g).data
        titles = [i["title"] for i in data["items"]]

        assert "Active" in titles
        assert "Inactive" not in titles


# ==================================================================
# ApiEndpoint / Screenshot
# ==================================================================
@pytest.mark.django_db
class TestApiEndpointSerializer:
    def test_method_display(self):
        e = ApiEndpoint.objects.create(method="POST", path="/api/v1/x/")
        data = ApiEndpointSerializer(e).data

        assert data["method"] == "POST"
        assert data["method_display"] == "POST"


@pytest.mark.django_db
class TestScreenshotSerializer:
    def test_image_url_is_none_without_request(self):
        s = Screenshot.objects.create(title="Home", image="landing/screenshots/x.png")
        data = ScreenshotSerializer(s).data

        # Without a request in context, absolute_url returns the
        # relative URL of the image.
        assert data["image_url"] is not None
        assert isinstance(data["image_url"], str)


# ==================================================================
# Roadmap
# ==================================================================
@pytest.mark.django_db
class TestRoadmapSerializers:
    def test_phase_status_display(self):
        p = RoadmapPhase.objects.create(title="Phase 1", status="done")
        data = RoadmapPhaseSerializer(p).data

        assert data["status"] == "done"
        assert data["status_display"] == "Done"

    def test_phase_includes_items(self):
        p = RoadmapPhase.objects.create(title="Phase 1")
        RoadmapItem.objects.create(phase=p, text="Ship it")

        data = RoadmapPhaseSerializer(p).data
        assert len(data["items"]) == 1
        assert data["items"][0]["text"] == "Ship it"

    def test_roadmap_item_fields(self):
        p = RoadmapPhase.objects.create(title="Phase 1")
        item = RoadmapItem.objects.create(phase=p, text="Ship it")

        data = RoadmapItemSerializer(item).data
        assert data["text"] == "Ship it"


# ==================================================================
# Statistics / social links
# ==================================================================
@pytest.mark.django_db
class TestStatisticSerializer:
    def test_fields(self):
        s = Statistic.objects.create(label="Posts", value="500")
        data = StatisticSerializer(s).data

        assert data["label"] == "Posts"
        assert data["value"] == "500"


@pytest.mark.django_db
class TestLandingSocialLinkSerializer:
    def test_fields(self):
        s = SocialLink.objects.create(
            platform="github", url="https://github.com/x", username="x"
        )
        data = LandingSocialLinkSerializer(s).data

        assert data["platform"] == "github"
        assert data["username"] == "x"


# ==================================================================
# ProjectInfo / Landing
# ==================================================================
@pytest.mark.django_db
class TestProjectInfoSerializer:
    def test_includes_only_project_fields(self):
        s = SiteSettings.objects.create(
            site_title="Torch", project_name="Torch Project"
        )
        data = ProjectInfoSerializer(s).data

        assert data["project_name"] == "Torch Project"
        # Not part of the ProjectInfo field list.
        assert "posts_per_page" not in data


@pytest.mark.django_db
class TestLandingSerializer:
    def test_shape(self):
        s = SiteSettings.objects.create(site_title="Torch")
        data = LandingSerializer(
            {
                "project": s,
                "tech_stack": [],
                "features": [],
                "api_endpoints": [],
                "screenshots": [],
                "roadmap": [],
                "stats": [],
                "social_links": [],
            }
        ).data

        for field in (
            "project",
            "tech_stack",
            "features",
            "api_endpoints",
            "screenshots",
            "roadmap",
            "stats",
            "social_links",
        ):
            assert field in data
