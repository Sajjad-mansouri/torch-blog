# blog/api/filters.py
import django_filters as filters
from django.db.models import Count, Q

from blog.models import Post


class PostFilter(filters.FilterSet):
    """
    Filters for the post list.

    Query params:
    - search: text search in title and summary
    - category: filter by category slug
    - tag: filter by tag slug
    - author: filter by author username
    - published_after: ISO date (YYYY-MM-DD)
    - published_before: ISO date (YYYY-MM-DD)
    - is_featured: true / false
    - min_views: integer
    - min_likes: integer
    """

    search = filters.CharFilter(
        method="filter_search",
        label="Search in title and summary",
    )
    category = filters.CharFilter(
        field_name="category__slug",
        lookup_expr="exact",
        label="Category slug",
    )
    tag = filters.CharFilter(
        field_name="tags__slug",
        lookup_expr="exact",
        label="Tag slug",
    )
    author = filters.CharFilter(
        field_name="author__username",
        lookup_expr="exact",
        label="Author username",
    )
    published_after = filters.DateFilter(
        field_name="published_at",
        lookup_expr="gte",
        label="Published on or after",
    )
    published_before = filters.DateFilter(
        field_name="published_at",
        lookup_expr="lte",
        label="Published on or before",
    )
    is_featured = filters.BooleanFilter(
        field_name="is_featured",
    )
    min_views = filters.NumberFilter(
        field_name="views_count",
        lookup_expr="gte",
    )
    min_likes = filters.NumberFilter(
        method="filter_min_likes",
    )

    class Meta:
        model = Post
        fields = [
            "search",
            "category",
            "tag",
            "author",
            "published_after",
            "published_before",
            "is_featured",
            "min_views",
            "min_likes",
        ]

    # ------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------

    def filter_search(self, queryset, name, value):
        """
        Search across title and summary. Case-insensitive substring
        match. Skips if the value is blank.
        """
        value = (value or "").strip()
        if not value:
            return queryset
        return queryset.filter(Q(title__icontains=value) | Q(summary__icontains=value))

    def filter_min_likes(self, queryset, name, value):
        """
        Filter by minimum like count.
        Uses annotation because likes are counted via the Like model.
        """
        return queryset.annotate(_like_count=Count("likes", distinct=True)).filter(
            _like_count__gte=value
        )
