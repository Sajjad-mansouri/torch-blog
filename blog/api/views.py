from django.core.cache import cache
from django.db.models import Count, Prefetch, Q
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from blog.models import Category, Post, Tag
from interactions.models import Comment

from .filters import PostFilter
from .pagination import PostPagination
from .serializers import (
    CategorySerializer,
    PostCardSerializer,
    PostDetailSerializer,
    TagSerializer,
)
from .services import (
    get_author_other_posts,
    get_similar_posts,
    record_view,
)


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


class PostListAPIView(generics.ListAPIView):
    """
    GET /api/v1/posts/

    Query params:
    - page: page number (default 1)
    - page_size: items per page (default 12, max 50)
    - category: filter by category slug
    - tag: filter by tag slug
    - author: filter by author username
    - published_after: YYYY-MM-DD
    - published_before: YYYY-MM-DD
    - is_featured: true / false
    - min_views: integer
    - min_likes: integer
    - ordering: field to sort by
      (newest, oldest, most_viewed, most_liked, most_commented)
    - search: search in title, summary, body

    Returns:
    {
        "count": 120,
        "num_pages": 10,
        "current_page": 1,
        "page_size": 12,
        "next": "...",
        "previous": null,
        "results": [ ...PostCard... ]
    }
    """

    permission_classes = [AllowAny]
    serializer_class = PostCardSerializer
    pagination_class = PostPagination
    filterset_class = PostFilter
    filter_backends = [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        # OrderingFilter removed
    ]
    search_fields = ["title", "summary"]

    def get_queryset(self):
        qs = Post.objects.published().for_card()
        if self.request.query_params.get("tag"):
            qs = qs.distinct()

        ordering = self.request.query_params.get("ordering")
        order_map = {
            "newest": "-published_at",
            "oldest": "published_at",
            "most_viewed": "-views_count",
            "most_liked": "-like_count",
            "most_commented": "-comment_count",
            "title_asc": "title",
            "title_desc": "-title",
        }
        order_field = order_map.get(ordering, "-published_at")
        return qs.order_by(order_field)


class PostDetailAPIView(generics.RetrieveAPIView):
    """
    Returns:
    - The full post
    - Nested comments (top-level with replies)
    - Similar posts (based of shared tags)
    - Other posts by the same author
    - is_liked/ is_bookmarked for the current user

    Records a deduplicated view
    """

    permission_classes = [AllowAny]
    serializer_class = PostDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        qs = Post.objects.for_card()
        user = self.request.user
        if not user.is_authenticated or not user.is_editor:
            qs = qs.published()

        return qs

    def retrieve(self, request, *args, **kwargs):
        """
        override to:
        1- Record the view (updates view_count)
        2- build the nested context data
        3- Serialize and return
        """

        post = self.get_object()

        # Record view (deduplicated)
        record_view(request, post)

        # Build context data for the serializer
        context = self.get_serializer_context()
        context.update(self._build_nested_context(post, request))

        serializer = self.get_serializer(post, context=context)
        return Response(serializer.data)

    def _build_nested_context(self, post, request):
        """
        Preload comments, similar posts, and user-specific flags
        into the serializer context.
        """

        top_level_comments = (
            post.comments.filter(
                status="approved", is_deleted=False, parent__isnull=True
            )
            .select_related("author")
            .prefetch_related(
                Prefetch(
                    "replies",
                    queryset=Comment.objects.filter(status="approved", is_deleted=False)
                    .select_related("author")
                    .annotate(like_count=Count("likes", distinct=True))
                    .order_by("created_at"),
                )
            )
            .annotate(like_count=Count("likes", distinct=True))
            .order_by("created_at")
        )

        # Similar posts and author's other posts
        similar_posts = get_similar_posts(post, limit=4)
        author_other_posts = get_author_other_posts(post, limit=3)

        # user-specifif flags

        liked_post_ids = set()
        bookmarked_post_ids = set()
        liked_comment_ids = set()

        if request.user.is_authenticated:
            liked_post_ids = set(
                request.user.post_likes.filter(post_id=post.id).values_list(
                    "post_id", flat=True
                )
            )

            bookmarked_post_ids = set(
                request.user.bookmarks.filter(post_id=post.id).values_list(
                    "post_id", flat=True
                )
            )

            liked_comment_ids = set(
                request.user.comment_likes.filter(comment__post=post).values_list(
                    "comment_id", flat=True
                )
            )

        return {
            "top_level_comments": top_level_comments,
            "similar_posts": similar_posts,
            "author_other_posts": author_other_posts,
            "liked_post_ids": liked_post_ids,
            "bookmarked_post_ids": bookmarked_post_ids,
            "liked_comment_ids": liked_comment_ids,
        }
