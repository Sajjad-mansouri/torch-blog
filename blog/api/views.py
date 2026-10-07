from django.core.cache import cache
from django.db.models import Count, Prefetch, Q
from django.urls import reverse
from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import AuthorBriefSerializer
from blog.models import Category, Post, Tag
from interactions.models import Comment

from .filters import PostFilter
from .mixins import PostOrderingMixin
from .pagination import PostPagination
from .serializers import (
    CategorySerializer,
    PostCardSerializer,
    PostDetailSerializer,
    SearchSuggestItemSerializer,
    TagSerializer,
)
from .services import (
    get_author_other_posts,
    get_similar_posts,
    normalize_query,
    record_view,
    search_authors,
    search_posts,
    search_tags,
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


class PostListAPIView(PostOrderingMixin, generics.ListAPIView):
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

        ordered_qs = self._apply_ordering(qs, self.request)
        return ordered_qs


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


# Category ViewSet
class CategoryViewSet(PostOrderingMixin, viewsets.ReadOnlyModelViewSet):
    """
    list:   GET /api/v1/categories/
    detail: GET /api/v1/categories/<slug>/
    posts:  GET /api/v1/categories/<slug>/posts/
    """

    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    lookup_field = "slug"

    def get_queryset(self):
        """
        Only active categories, with a post count annotated.
        Post count respects published + not deleted.
        """

        return (
            Category.objects.filter(is_active=True)
            .select_related("parent")
            .annotate(
                post_count=Count(
                    "posts",
                    filter=Q(posts__status="published", posts__is_deleted=False),
                    distinct=True,
                )
            )
            .order_by("order", "name")
        )

    # Nested: /categories/<slug>/posts/
    @action(
        detail=True, methods=["get"], url_path="posts", pagination_class=PostPagination
    )
    def posts(self, request, slug=None):
        """
        Posts that belong to this category.
        Supports the same filters, ordering, and search as
        /api/v1/posts/, plus an `include_subcategories` option.
        """
        category = self.get_object()

        # optionally include posts from child categories
        include_children = (
            request.query_params.get("include_subcategories", "false").lower == "true"
        )
        if include_children:
            # Collect this category + all descendants
            child_ids = self._collect_descendant_ids(category)
            category_ids = [category.id] + child_ids
            posts_qs = Post.objects.filter(category_id__in=category_ids)
        else:
            posts_qs = Post.objects.filter(category=category)

        posts_qs = posts_qs.published().for_card()

        # Apply filters
        filterset = PostFilter(data=request.query_params, queryset=posts_qs)

        if filterset.is_valid():
            posts_qs = filterset.qs

        # Apply ordering using the same map as PostListAPIView
        posts_qs = self._apply_ordering(posts_qs, request)

        # Deduplicate (needed if tag filter is applied)
        if request.query_params.get("tag"):
            posts_qs = posts_qs.distinct()

        # paginate
        page = self.paginate_queryset(posts_qs)
        if page is not None:
            serializer = PostCardSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = PostCardSerializer(
            posts_qs, many=True, context={"request": request}
        )
        return Response(serializer.data)

    # helper
    def _collect_descendant_ids(self, category):
        """Recursively collect all descendant category IDs."""
        ids = []
        children = Category.objects.filter(parent=category, is_active=True)
        for child in children:
            ids.append(child.id)
            ids.extend(self._collect_descendant_ids(child))
        return ids


# blog/views.py


class TagViewSet(PostOrderingMixin, viewsets.ReadOnlyModelViewSet):
    """
    list:   GET /api/v1/tags/
    detail: GET /api/v1/tags/<slug>/
    posts:  GET /api/v1/tags/<slug>/posts/
    """

    permission_classes = [AllowAny]
    serializer_class = TagSerializer
    lookup_field = "slug"

    def get_queryset(self):
        """
        Tags ordered by usage count (most used first).
        Optionally filter by name with ?search=
        """
        qs = Tag.objects.all()

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(name__icontains=search)

        return qs.order_by("-usage_count", "name")

    # ------------------------------------------------------------
    # Nested: /tags/<slug>/posts/
    # ------------------------------------------------------------

    @action(
        detail=True,
        methods=["get"],
        url_path="posts",
        pagination_class=PostPagination,
    )
    def posts(self, request, slug=None):
        """
        Posts that have this tag.
        Supports the same filters and ordering as /api/v1/posts/.
        """
        tag = self.get_object()

        posts_qs = Post.objects.published().filter(tags=tag).for_card()

        # Apply filters (tag is already fixed by the route)
        filterset = PostFilter(
            data=request.query_params,
            queryset=posts_qs,
        )
        if filterset.is_valid():
            posts_qs = filterset.qs

        # Apply ordering
        posts_qs = self._apply_ordering(posts_qs, request)

        # Deduplicate — needed because M2M joins can duplicate rows
        posts_qs = posts_qs.distinct()

        # Paginate
        page = self.paginate_queryset(posts_qs)
        if page is not None:
            serializer = PostCardSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = PostCardSerializer(
            posts_qs, many=True, context={"request": request}
        )
        return Response(serializer.data)


class SearchAPIView(APIView):
    """
    GET /api/v1/search/?q=<query>&type=<post|author|tag>

    - `q` is required (min 2 characters).
    - `type` is optional. If omitted, searches all types.
    - `limit` optionally caps per-type results in the mixed view.
    - When `type` is given, results are paginated.

    Response:
    - Mixed: { "query": "...", "posts": {...}, "authors": {...}, "tags": {...} }
    - Typed: { "query": "...", "results": [...], "count": N, ... }
    """

    permission_classes = [AllowAny]
    DEFAULT_LIMIT = 5
    MAX_LIMIT = 20

    def get(self, request):
        raw_query = request.query_params.get("q", "")
        query = normalize_query(raw_query)

        if query is None:
            raise ValidationError(
                {"q": "Query must be at least 2 characters after trimming."}
            )

        result_type = request.query_params.get("type")
        if result_type in (None, "", "all"):
            return Response(self._mixed_response(query, request))

        if result_type == "post":
            return self._typed_post_response(query, request)

        if result_type == "author":
            return self._typed_author_response(query, request)

        if result_type == "tag":
            return self._typed_tag_response(query, request)

        raise ValidationError({"type": "Must be one of :post, author, tag"})

    def _mixed_response(self, query, request):
        limit = self._get_limit(request)
        posts_qs = search_posts(query, limit=limit)
        authors_qs = search_authors(query, limit=limit)
        tags_qs = search_tags(query, limit=limit)
        return {
            "query": query,
            "posts": {
                "count": posts_qs.count()
                if hasattr(posts_qs, "count")
                else len(posts_qs),
                "results": PostCardSerializer(
                    posts_qs, many=True, context={"request": request}
                ).data,
            },
            "authors": {
                "count": authors_qs.count()
                if hasattr(authors_qs, "count")
                else len(authors_qs),
                "results": AuthorBriefSerializer(
                    authors_qs, many=True, context={"request": request}
                ).data,
            },
            "tags": {
                "count": tags_qs.count() if hasattr(tags_qs, "count") else len(tags_qs),
                "results": TagSerializer(tags_qs, many=True).data,
            },
        }

    def _get_limit(self, request):
        try:
            limit = int(request.query_params.get("limit", self.DEFAULT_LIMIT))
        except (TypeError, ValueError):
            raise ValidationError({"limit": "Must be an integer."}) from None
        if limit < 1 or limit > self.MAX_LIMIT:
            raise ValidationError({"limit": f"Must be between 1 and {self.MAX_LIMIT}."})
        return limit

    def _typed_post_response(self, query, request):
        qs = search_posts(query)
        return self._paginated_response(qs, request, PostCardSerializer)

    def _typed_author_response(self, query, request):
        qs = search_authors(query)
        return self._paginated_response(qs, request, AuthorBriefSerializer)

    def _typed_tag_response(self, query, request):
        qs = search_tags(query)
        return self._paginated_response(qs, request, TagSerializer)

    def _paginated_response(
        self, qs, request, serializer_cls, use_post_pagination=True
    ):
        paginator = PostPagination() if use_post_pagination else None
        if paginator:
            page = paginator.paginate_queryset(qs, request, view=self)
            if page is not None:
                serializer = serializer_cls(
                    page, many=True, context={"request": request}
                )
                return Response(
                    {
                        "query": request.query_params.get("q"),
                        **paginator.get_paginated_response(serializer.data).data,
                    }
                )
        serializer = serializer_cls(qs, many=True, context={"request": request})

        return Response(
            {
                "query": request.query_params.get("q"),
                "count": qs.count() if hasattr(qs, "count") else len(qs),
                "results": serializer.data,
            }
        )


class SearchSuggestView(APIView):
    """
    GET /api/v1/search/suggest/?q=<query>

    Returns a flat list of suggestions across posts, tags, and authors.
    Optimized for autocomplete widgets — small payload, fast.
    """

    permission_classes = [AllowAny]

    PER_TYPE_LIMIT = 5

    def get(self, request):
        raw_query = request.query_params.get("q", "")
        query = normalize_query(raw_query)

        if query is None:
            return Response({"query": "", "results": []})

        suggestions = []

        # Posts (title only)
        posts = search_posts(query, limit=self.PER_TYPE_LIMIT)
        for post in posts:
            suggestions.append(
                {
                    "type": "post",
                    "id": post.pk,
                    "label": post.title,
                    "slug": post.slug,
                    "url": reverse("blog:post-detail", kwargs={"slug": post.slug}),
                }
            )

        # Tags
        tags = search_tags(query, limit=self.PER_TYPE_LIMIT)
        for tag in tags:
            suggestions.append(
                {
                    "type": "tag",
                    "id": tag.pk,
                    "label": tag.name,
                    "slug": tag.slug,
                    "url": f"/tag/{tag.slug}/",
                }
            )

        # Authors
        authors = search_authors(query, limit=self.PER_TYPE_LIMIT)
        for author in authors:
            suggestions.append(
                {
                    "type": "author",
                    "id": author.pk,
                    "label": author.display_name,
                    "slug": author.username,
                    "url": f"/author/{author.username}/",
                }
            )

        return Response(
            {
                "query": query,
                "results": SearchSuggestItemSerializer(suggestions, many=True).data,
            }
        )
