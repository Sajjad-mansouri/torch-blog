"""
Behavioral tests for core.models.

Coverage:
- SiteSettings: singleton enforcement, save cache invalidation,
  delete no-op, get() caching, __str__.
- TechCategory / TechItem: unique-per-category constraint, ordering,
  __str__.
- FeatureGroup / FeatureItem: ordering, __str__.
- ApiEndpoint: method choices, ordering, __str__.
- Screenshot: ordering, __str__.
- RoadmapPhase / RoadmapItem: status choices, ordering, __str__.
- Statistic: ordering, __str__.
- SocialLink: unique platform constraint, ordering, __str__.
- ContactMessage: mark_read, idempotency, ordering, __str__.
- ActivityLog: SET_NULL on user, metadata default, ordering,
  __str__, action choices.
"""

import pytest
from django.core.cache import cache
from django.db import IntegrityError

from core.models import (
    ActivityLog,
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


# ==================================================================
# SiteSettings
# ==================================================================
@pytest.mark.django_db
class TestSiteSettingsSingleton:
    def test_first_save_uses_pk_one(self):
        s = SiteSettings.objects.create(site_title="First")
        assert s.pk == 1

    def test_second_save_overwrites_first(self):
        SiteSettings.objects.create(site_title="First")
        second = SiteSettings(site_title="Second")
        second.save()

        assert second.pk == 1
        assert SiteSettings.objects.count() == 1
        assert SiteSettings.objects.get(pk=1).site_title == "Second"

    def test_default_site_title_is_torch(self):
        s = SiteSettings.objects.create()
        assert s.site_title == "Torch"


@pytest.mark.django_db
class TestSiteSettingsDelete:
    def test_delete_is_a_noop(self):
        s = SiteSettings.objects.create(site_title="Still Here")
        s.delete()

        assert SiteSettings.objects.filter(pk=1).exists()


@pytest.mark.django_db
class TestSiteSettingsGet:
    def test_creates_row_when_missing(self):
        cache.clear()
        assert SiteSettings.objects.count() == 0

        s = SiteSettings.get()

        assert s.pk == 1
        assert SiteSettings.objects.count() == 1

    def test_returns_cached_instance_after_first_call(self):
        cache.clear()
        first = SiteSettings.get()
        second = SiteSettings.get()

        # Same object because LocMemCache returns the cached instance.
        assert first == second
        # Only one DB row.
        assert SiteSettings.objects.count() == 1

    def test_save_invalidates_cache(self):
        cache.clear()
        SiteSettings.get()
        assert cache.get("site_settings") is not None

        s = SiteSettings.objects.get(pk=1)
        s.site_title = "Updated"
        s.save()

        assert cache.get("site_settings") is None


@pytest.mark.django_db
class TestSiteSettingsStr:
    def test_str_returns_site_title(self):
        s = SiteSettings.objects.create(site_title="My Site")
        assert str(s) == "My Site"


# ==================================================================
# TechCategory / TechItem
# ==================================================================
@pytest.mark.django_db
class TestTechCategory:
    def test_create(self):
        c = TechCategory.objects.create(name="Backend", slug="backend")
        assert c.name == "Backend"
        assert c.is_active is True
        assert c.order == 0

    def test_str_returns_name(self):
        c = TechCategory.objects.create(name="Frontend", slug="frontend")
        assert str(c) == "Frontend"

    def test_default_ordering(self):
        a = TechCategory.objects.create(name="A", slug="a", order=2)
        b = TechCategory.objects.create(name="B", slug="b", order=1)
        c = TechCategory.objects.create(name="C", slug="c", order=1)

        ordered = list(TechCategory.objects.all())
        # order asc, then name asc — B before C (both order=1), then A.
        assert ordered == [b, c, a]


@pytest.mark.django_db
class TestTechItem:
    def test_create(self):
        c = TechCategory.objects.create(name="Backend", slug="backend")
        item = TechItem.objects.create(category=c, name="Django")

        assert item.category == c
        assert item.name == "Django"

    def test_str_includes_category_name(self):
        c = TechCategory.objects.create(name="Backend", slug="backend")
        item = TechItem.objects.create(category=c, name="Django")

        assert "Backend" in str(item)
        assert "Django" in str(item)

    def test_unique_name_per_category(self):
        c = TechCategory.objects.create(name="Backend", slug="backend")
        TechItem.objects.create(category=c, name="Django")

        with pytest.raises(IntegrityError):
            TechItem.objects.create(category=c, name="Django")

    def test_same_name_in_different_categories_is_allowed(self):
        c1 = TechCategory.objects.create(name="Backend", slug="backend")
        c2 = TechCategory.objects.create(name="Frontend", slug="frontend")
        TechItem.objects.create(category=c1, name="Django")
        TechItem.objects.create(category=c2, name="Django")

        assert TechItem.objects.filter(name="Django").count() == 2

    def test_deleting_category_cascades_to_items(self):
        c = TechCategory.objects.create(name="Backend", slug="backend")
        item = TechItem.objects.create(category=c, name="Django")

        c.delete()
        assert not TechItem.objects.filter(pk=item.pk).exists()


# ==================================================================
# FeatureGroup / FeatureItem
# ==================================================================
@pytest.mark.django_db
class TestFeatureGroup:
    def test_create(self):
        g = FeatureGroup.objects.create(title="Editor", slug="editor")
        assert g.is_active is True

    def test_str_returns_title(self):
        g = FeatureGroup.objects.create(title="Editor", slug="editor")
        assert str(g) == "Editor"

    def test_default_ordering(self):
        a = FeatureGroup.objects.create(title="A", slug="a", order=2)
        b = FeatureGroup.objects.create(title="B", slug="b", order=1)

        ordered = list(FeatureGroup.objects.all())
        assert ordered == [b, a]


@pytest.mark.django_db
class TestFeatureItem:
    def test_create(self):
        g = FeatureGroup.objects.create(title="Editor", slug="editor")
        item = FeatureItem.objects.create(group=g, title="Rich Text", description="...")

        assert item.title == "Rich Text"

    def test_str_includes_group_and_title(self):
        g = FeatureGroup.objects.create(title="Editor", slug="editor")
        item = FeatureItem.objects.create(group=g, title="Rich Text", description="...")

        assert "Editor" in str(item)
        assert "Rich Text" in str(item)

    def test_deleting_group_cascades_to_items(self):
        g = FeatureGroup.objects.create(title="Editor", slug="editor")
        item = FeatureItem.objects.create(group=g, title="Rich Text", description="...")

        g.delete()
        assert not FeatureItem.objects.filter(pk=item.pk).exists()


# ==================================================================
# ApiEndpoint
# ==================================================================
@pytest.mark.django_db
class TestApiEndpoint:
    def test_default_method_is_get(self):
        e = ApiEndpoint.objects.create(path="/api/v1/posts/")
        assert e.method == ApiEndpoint.Method.GET

    def test_str_includes_method_and_path(self):
        e = ApiEndpoint.objects.create(method="POST", path="/api/v1/contact/")
        assert "POST" in str(e)
        assert "/api/v1/contact/" in str(e)

    def test_ordering_by_group_then_order_then_path(self):
        a = ApiEndpoint.objects.create(method="GET", path="/b/", group="posts", order=1)
        b = ApiEndpoint.objects.create(method="GET", path="/a/", group="posts", order=1)
        c = ApiEndpoint.objects.create(method="GET", path="/c/", group="auth", order=1)

        ordered = list(ApiEndpoint.objects.all())
        # group asc: auth before posts → c first, then b then a.
        assert ordered == [c, b, a]


# ==================================================================
# Screenshot
# ==================================================================
@pytest.mark.django_db
class TestScreenshot:
    def test_create(self):
        s = Screenshot.objects.create(title="Home", image="landing/screenshots/x.png")
        assert s.title == "Home"

    def test_str_returns_title(self):
        s = Screenshot.objects.create(title="Home", image="landing/screenshots/x.png")
        assert str(s) == "Home"

    def test_default_ordering_by_order_then_title(self):
        a = Screenshot.objects.create(title="A", image="x.png", order=2)
        b = Screenshot.objects.create(title="B", image="x.png", order=1)

        ordered = list(Screenshot.objects.all())
        assert ordered == [b, a]


# ==================================================================
# RoadmapPhase / RoadmapItem
# ==================================================================
@pytest.mark.django_db
class TestRoadmapPhase:
    def test_default_status_is_planned(self):
        p = RoadmapPhase.objects.create(title="Phase 1")
        assert p.status == RoadmapPhase.Status.PLANNED

    def test_str_includes_title_and_status(self):
        p = RoadmapPhase.objects.create(title="Phase 1")
        assert "Phase 1" in str(p)
        assert "planned" in str(p)

    def test_ordering_by_order(self):
        a = RoadmapPhase.objects.create(title="A", order=2)
        b = RoadmapPhase.objects.create(title="B", order=1)

        ordered = list(RoadmapPhase.objects.all())
        assert ordered == [b, a]


@pytest.mark.django_db
class TestRoadmapItem:
    def test_create(self):
        p = RoadmapPhase.objects.create(title="Phase 1")
        item = RoadmapItem.objects.create(phase=p, text="Ship it")
        assert item.phase == p

    def test_str_returns_text(self):
        p = RoadmapPhase.objects.create(title="Phase 1")
        item = RoadmapItem.objects.create(phase=p, text="Ship it")
        assert str(item) == "Ship it"

    def test_deleting_phase_cascades_to_items(self):
        p = RoadmapPhase.objects.create(title="Phase 1")
        item = RoadmapItem.objects.create(phase=p, text="Ship it")

        p.delete()
        assert not RoadmapItem.objects.filter(pk=item.pk).exists()


# ==================================================================
# Statistic
# ==================================================================
@pytest.mark.django_db
class TestStatistic:
    def test_create(self):
        s = Statistic.objects.create(label="Posts", value="500")
        assert s.label == "Posts"
        assert s.value == "500"

    def test_str_includes_label_and_value(self):
        s = Statistic.objects.create(label="Posts", value="500")
        assert "Posts" in str(s)
        assert "500" in str(s)

    def test_default_ordering(self):
        a = Statistic.objects.create(label="Z", value="1", order=2)
        b = Statistic.objects.create(label="A", value="1", order=1)

        ordered = list(Statistic.objects.all())
        assert ordered == [b, a]


# ==================================================================
# SocialLink
# ==================================================================
@pytest.mark.django_db
class TestSocialLink:
    def test_create(self):
        s = SocialLink.objects.create(platform="github", url="https://github.com/x")
        assert s.platform == "github"

    def test_str_prefers_username_over_url(self):
        s = SocialLink.objects.create(
            platform="github", url="https://github.com/x", username="x"
        )
        assert "x" in str(s)

    def test_str_falls_back_to_url_without_username(self):
        s = SocialLink.objects.create(platform="github", url="https://github.com/x")
        assert "https://github.com/x" in str(s)

    def test_unique_platform(self):
        SocialLink.objects.create(platform="github", url="https://github.com/x")

        with pytest.raises(IntegrityError):
            SocialLink.objects.create(platform="github", url="https://github.com/y")

    def test_ordering_by_order_then_platform(self):
        a = SocialLink.objects.create(platform="twitter", url="x", order=2)
        b = SocialLink.objects.create(platform="github", url="x", order=1)

        ordered = list(SocialLink.objects.all())
        assert ordered == [b, a]


# ==================================================================
# ContactMessage
# ==================================================================
@pytest.mark.django_db
class TestContactMessage:
    def test_create_defaults(self):
        m = ContactMessage.objects.create(
            name="Alice", email="a@example.com", message="Hello there."
        )
        assert m.is_read is False
        assert m.read_at is None
        assert m.replied is False

    def test_str_format(self):
        m = ContactMessage.objects.create(
            name="Alice", email="a@example.com", message="Hello there."
        )
        assert "Alice" in str(m)
        assert "a@example.com" in str(m)

    def test_mark_read_sets_flag_and_timestamp(self):
        m = ContactMessage.objects.create(
            name="Alice", email="a@example.com", message="Hello."
        )
        m.mark_read()
        m.refresh_from_db()

        assert m.is_read is True
        assert m.read_at is not None

    def test_mark_read_is_idempotent(self):
        m = ContactMessage.objects.create(
            name="Alice", email="a@example.com", message="Hello."
        )
        m.mark_read()
        m.refresh_from_db()
        first_read_at = m.read_at

        m.mark_read()
        m.refresh_from_db()

        assert m.read_at == first_read_at

    def test_ordering_newest_first(self):
        a = ContactMessage.objects.create(
            name="A", email="a@example.com", message="first"
        )
        b = ContactMessage.objects.create(
            name="B", email="b@example.com", message="second"
        )

        ordered = list(ContactMessage.objects.all())
        assert ordered == [b, a]


# ==================================================================
# ActivityLog
# ==================================================================
@pytest.mark.django_db
class TestActivityLog:
    def test_create_with_user(self, test_user):
        log = ActivityLog.objects.create(
            user=test_user,
            action=ActivityLog.Action.POST_CREATED,
        )
        assert log.user == test_user
        assert log.metadata == {}

    def test_user_is_nullable(self):
        log = ActivityLog.objects.create(
            user=None,
            action=ActivityLog.Action.POST_CREATED,
        )
        assert log.user is None

    def test_deleting_user_sets_null(self, test_user):
        log = ActivityLog.objects.create(
            user=test_user,
            action=ActivityLog.Action.POST_CREATED,
        )
        test_user.delete()
        log.refresh_from_db()

        assert log.user is None

    def test_ordering_newest_first(self, test_user):
        a = ActivityLog.objects.create(
            user=test_user, action=ActivityLog.Action.POST_CREATED
        )
        b = ActivityLog.objects.create(
            user=test_user, action=ActivityLog.Action.POST_DELETED
        )

        ordered = list(ActivityLog.objects.all())
        assert ordered == [b, a]

    def test_str_includes_user_and_action(self, test_user):
        log = ActivityLog.objects.create(
            user=test_user, action=ActivityLog.Action.POST_CREATED
        )
        text = str(log)
        assert test_user.username in text
        assert "post_created" in text

    def test_metadata_stored_as_json(self, test_user):
        log = ActivityLog.objects.create(
            user=test_user,
            action=ActivityLog.Action.POST_CREATED,
            metadata={"post_id": 42, "title": "Hi"},
        )
        log.refresh_from_db()

        assert log.metadata == {"post_id": 42, "title": "Hi"}

    def test_action_display(self, test_user):
        log = ActivityLog.objects.create(
            user=test_user, action=ActivityLog.Action.POST_CREATED
        )
        assert log.get_action_display() == "Post Created"

    def test_all_declared_actions_are_choice_values(self):
        declared = {
            "post_created",
            "post_edited",
            "post_submitted",
            "post_published",
            "post_rejected",
            "post_unpublished",
            "post_deleted",
            "post_restored",
            "comment_deleted",
            "user_role_changed",
            "user_banned",
            "settings_updated",
        }
        values = {choice[0] for choice in ActivityLog.Action.choices}
        assert values == declared
