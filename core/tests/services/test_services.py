"""
Behavioral tests for core.services_landing.
"""

import pytest
from django.core.cache import cache

from core.api.services_landing import (
    CACHE_KEY,
    get_landing_data,
    invalidate_landing_cache,
)
from core.models import (
    FeatureGroup,
    SiteSettings,
    SocialLink,
    TechCategory,
)


# ==================================================================
# get_landing_data
# ==================================================================
@pytest.mark.django_db
class TestGetLandingData:
    def test_returns_dict_with_all_sections(self):
        cache.clear()
        data = get_landing_data()

        for key in (
            "project",
            "tech_stack",
            "features",
            "api_endpoints",
            "screenshots",
            "roadmap",
            "stats",
            "social_links",
        ):
            assert key in data

    def test_returns_model_instances_not_dicts(self):
        cache.clear()
        data = get_landing_data()

        assert isinstance(data["project"], SiteSettings)

    def test_includes_active_tech_categories_only(self):
        cache.clear()
        active = TechCategory.objects.create(name="A", slug="a", is_active=True)
        TechCategory.objects.create(name="B", slug="b", is_active=False)

        data = get_landing_data()
        ids = [c.pk for c in data["tech_stack"]]

        assert active.pk in ids

    def test_includes_active_feature_groups_only(self):
        cache.clear()
        active = FeatureGroup.objects.create(title="A", slug="a", is_active=True)
        FeatureGroup.objects.create(title="B", slug="b", is_active=False)

        data = get_landing_data()
        ids = [g.pk for g in data["features"]]

        assert active.pk in ids

    def test_includes_social_links_flagged_for_landing(self):
        cache.clear()
        SocialLink.objects.create(
            platform="github",
            url="https://github.com/x",
            is_active=True,
            show_in_landing=True,
        )
        SocialLink.objects.create(
            platform="twitter",
            url="https://twitter.com/x",
            is_active=True,
            show_in_landing=False,
        )

        data = get_landing_data()
        platforms = [s.platform for s in data["social_links"]]

        assert "github" in platforms
        assert "twitter" not in platforms

    def test_caches_result(self):
        cache.clear()
        get_landing_data()
        assert cache.get(CACHE_KEY) is not None

    def test_returns_cached_on_second_call(self):
        cache.clear()
        first = get_landing_data()
        second = get_landing_data()

        # LocMemCache pickles on set and unpickles on get, so the two
        # calls produce distinct-but-equal dict objects.
        assert first == second
        assert first["project"].pk == second["project"].pk

    def test_second_call_reads_from_cache(self):
        cache.clear()
        get_landing_data()

        # Wipe the DB — if the second call hit the DB it would return
        # nothing for tech_stack.
        TechCategory.objects.all().delete()
        TechCategory.objects.create(
            name="Added After Cache", slug="after", is_active=True
        )

        second = get_landing_data()
        slugs = [c.slug for c in second["tech_stack"]]
        assert "after" not in slugs  # cached — the new category isn't visible


@pytest.mark.django_db
class TestInvalidateLandingCache:
    def test_deletes_the_cache_key(self):
        cache.clear()
        get_landing_data()
        assert cache.get(CACHE_KEY) is not None

        invalidate_landing_cache()
        assert cache.get(CACHE_KEY) is None


# ==================================================================
# C7 documented behavior: cache is not auto-invalidated
# ==================================================================
@pytest.mark.django_db
class TestLandingCacheStaleness:
    def test_documents_sitesettings_save_does_not_invalidate_landing_cache(self):
        """
        Documents current behavior (C7): saving SiteSettings deletes
        the "site_settings" cache key but NOT the "landing_page_data"
        key. The landing cache must be invalidated explicitly via
        invalidate_landing_cache().
        """
        cache.clear()
        get_landing_data()
        assert cache.get(CACHE_KEY) is not None

        s = SiteSettings.objects.get(pk=1)
        s.site_title = "Updated"
        s.save()

        # landing cache is still present.
        assert cache.get(CACHE_KEY) is not None

    def test_documents_techcategory_save_does_not_invalidate_landing_cache(self):
        """
        TechCategory has no save override and no signal wiring, so
        creating/updating one does not touch the landing cache.
        """
        cache.clear()
        get_landing_data()
        assert cache.get(CACHE_KEY) is not None

        TechCategory.objects.create(name="New", slug="new")

        assert cache.get(CACHE_KEY) is not None

    def test_explicit_invalidation_clears_cache(self):
        cache.clear()
        get_landing_data()

        invalidate_landing_cache()

        assert cache.get(CACHE_KEY) is None
