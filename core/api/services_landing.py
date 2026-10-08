# core/services_landing.py
from django.core.cache import cache

from core.models import (
    ApiEndpoint,
    FeatureGroup,
    RoadmapPhase,
    Screenshot,
    SiteSettings,
    SocialLink,
    Statistic,
    TechCategory,
)

CACHE_KEY = "landing_page_data"
CACHE_TTL = 600  # 10 minutes


def get_landing_data():
    """
    Build the landing page payload. Cached for 10 minutes.
    """
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached

    settings_obj = SiteSettings.get()

    data = {
        "project": settings_obj,
        "tech_stack": list(
            TechCategory.objects.filter(is_active=True)
            .prefetch_related("items")
            .order_by("order", "name")
        ),
        "features": list(
            FeatureGroup.objects.filter(is_active=True)
            .prefetch_related("items")
            .order_by("order", "title")
        ),
        "api_endpoints": list(
            ApiEndpoint.objects.filter(is_active=True).order_by(
                "group", "order", "path"
            )
        ),
        "screenshots": list(
            Screenshot.objects.filter(is_active=True).order_by("order", "title")
        ),
        "roadmap": list(
            RoadmapPhase.objects.prefetch_related("items").order_by("order", "title")
        ),
        "stats": list(
            Statistic.objects.filter(is_active=True).order_by("order", "label")
        ),
        "social_links": list(
            SocialLink.objects.filter(is_active=True, show_in_landing=True).order_by(
                "order", "platform"
            )
        ),
    }

    cache.set(CACHE_KEY, data, CACHE_TTL)
    return data


def invalidate_landing_cache():
    """
    Called when landing-related data changes.
    """
    cache.delete(CACHE_KEY)
