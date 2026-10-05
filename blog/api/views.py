from django.core.cache import cache
from django.db.models import Count, Q
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from blog.models import Category, Post, Tag

from .serializers import CategorySerializer, PostCardSerializer, TagSerializer


class HomeAPIView(APIView):
    """
    GET /api/v1/home/

    Returns everything the home page needs in one request:
    - featured posts (5)
    - latest posts (10)
    - trending posts (5, last 7 days)
    - categories (8, with post counts)
    - hot tags (10, by usage)

    Response is cached for 5 minutes and invalidated by
    Post.save(), Category.save(), and Tag.save().
    """

    permission_classes = [AllowAny]
    CACHE_KEY = "home_page_data"
    CACHE_TTL = 300

    FEATURED_LIMIT = 5
    LATEST_LIMIT = 10
    TRENDING_LIMIT = 5
    CATEGORY_LIMIT = 8
    HOT_TAG_LIMIT = 10
    TRENDING_DAYS = 7

    def get(self, request):
        cached = cache.get(self.CACHE_KEY)
        if cached is not None:
            return Response(cached)

        data = self._buil_home_data()
        cache.set(self.CACHE_KEY, data, self.CACHE_TTL)
        return Response(data)

    def _build_home_data(self):
        return {
            "featured": self._get_featured(),
            "latest": self._get_latest(),
            "trending": self._get_trending(),
            "categories": self._get_categories(),
            "hot_tags": self._get_hot_tags(),
        }

    def _get_featured(self):
        qs = Post.objects.featured().for_card()[: self.FEATURED_LIMIT]
        return PostCardSerializer(qs, many=True).data

    def _get_latest(self):
        qs = Post.objects.latest().for_card()[: self.LATEST_LIMIT]

        return PostCardSerializer(qs, many=True).data

    def _get_trending(self):
        qs = Post.objects.trending(days=self.TRENDING_DAYS).for_card()[
            : self.TRENDING_LIMIT
        ]
        return PostCardSerializer(qs, many=True).data

    def _get_categories(self):
        qs = (
            Category.objects.filter(is_active=True, parent__isnull=True)
            .annotate(
                post_count=Count(
                    "posts",
                    filter=Q(posts__status="published", posts__is_deleted=False),
                    distinct=True,
                )
            )
            .order_by("order", "name")[: self.CATEGORY_LIMIT]
        )

        return CategorySerializer(qs, many=True).data

    def _get_hot_tags(self):
        qs = Tag.objects.filter(usage_count__gt=0).order_by("-usage_count")[
            : self.HOT_TAG_LIMIT
        ]
        return TagSerializer(qs, many=True).data
