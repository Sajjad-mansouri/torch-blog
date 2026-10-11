# accounts/views.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from accounts.models import User
from blog.api.filters import PostFilter
from blog.api.pagination import PostPagination
from blog.api.serializers import PostCardSerializer
from blog.models import Post

from .serializers import AuthorBriefSerializer, AuthorProfileSerializer
from .services import get_author_stats


class AuthorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/authors/
    detail: GET /api/v1/authors/<username>/
    posts:  GET /api/v1/authors/<username>/posts/
    """

    pagination_class = PostPagination
    permission_classes = [AllowAny]
    lookup_field = "username"

    def get_queryset(self):
        """
        Only authors and editors have public profiles.
        Readers don't publish, so they don't need one.
        """
        return (
            User.objects.filter(role__in=[User.Role.AUTHOR, User.Role.EDITOR])
            .order_by("username")
            .prefetch_related("social_links")
        )

    def get_serializer_class(self):
        # List action gets a lightweight serializer
        if self.action == "list":
            return AuthorBriefSerializer
        # Detail and posts actions use the full profile
        return AuthorProfileSerializer

    # ------------------------------------------------------------
    # Detail: /authors/<username>/
    # ------------------------------------------------------------

    def retrieve(self, request, *args, **kwargs):
        """
        Override to inject stats and recent_posts into the context.
        """
        author = self.get_object()

        context = self.get_serializer_context()
        context["stats"] = get_author_stats(author)
        context["recent_posts"] = (
            Post.objects.published()
            .filter(author=author)
            .for_card()
            .order_by("-published_at")[:5]
        )

        serializer = self.get_serializer(author, context=context)
        return Response(serializer.data)

    # ------------------------------------------------------------
    # Nested: /authors/<username>/posts/
    # ------------------------------------------------------------

    @action(
        detail=True,
        methods=["get"],
        url_path="posts",
        pagination_class=PostPagination,
    )
    def posts(self, request, username=None):
        """
        Published posts by this author.
        Supports the same filters and ordering as /api/v1/posts/.
        """
        author = self.get_object()

        qs = Post.objects.published().filter(author=author).for_card()

        # Apply filters (author is already fixed by the route)
        filterset = PostFilter(
            data=request.query_params,
            queryset=qs,
        )
        if filterset.is_valid():
            qs = filterset.qs

        # Deduplicate if tag filter was applied
        if request.query_params.get("tag"):
            qs = qs.distinct()

        # Apply ordering using the same map as PostListView
        qs = self._apply_ordering(qs, request)

        # Paginate
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = PostCardSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = PostCardSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------

    def _apply_ordering(self, qs, request):
        """
        Same ordering map as PostListView and the category/tag views.
        Consider extracting to a shared mixin when this appears a
        fourth time.
        """
        order_map = {
            "newest": "-published_at",
            "oldest": "published_at",
            "most_viewed": "-views_count",
            "most_liked": "-like_count",
            "most_commented": "-comment_count",
            "title_asc": "title",
            "title_desc": "-title",
        }
        ordering = request.query_params.get("ordering")
        if ordering and ordering not in order_map:
            raise ValidationError(
                {
                    "ordering": (
                        f'Invalid value "{ordering}". '
                        f"Choose from: {', '.join(order_map.keys())}"
                    )
                }
            )
        order_field = order_map.get(ordering, "-published_at")
        return qs.order_by(order_field)
