# editor/views_posts.py
from django.db.models import Count, Q
from rest_framework import generics
from rest_framework.exceptions import ValidationError

from blog.api.pagination import PostPagination
from blog.api.permissions import IsEditor
from blog.api.serializers import (
    PostCardSerializer,
)
from blog.models import Post

# ============================================================
# Review queue
# ============================================================


class ReviewQueueView(generics.ListAPIView):
    """
    GET /api/v1/editor/review-queue/

    Lists pending posts, oldest first (FIFO — first submitted
    should be reviewed first).
    """

    permission_classes = [IsEditor]
    serializer_class = PostCardSerializer
    pagination_class = PostPagination

    def get_queryset(self):
        return (
            Post.objects.filter(status=Post.Status.PENDING, is_deleted=False)
            .select_related("author", "category")
            .prefetch_related("tags")
            .annotate(
                like_count=Count("likes", distinct=True),
                comment_count=Count(
                    "comments",
                    filter=Q(
                        comments__status="approved",
                        comments__is_deleted=False,
                    ),
                    distinct=True,
                ),
                bookmark_count=Count("bookmarks", distinct=True),
            )
            .order_by("updated_at")  # oldest submission first
        )


# ============================================================
# Manage all posts (any status)
# ============================================================


class EditorPostListView(generics.ListAPIView):
    """
    GET /api/v1/editor/posts/

    Lists all posts regardless of status.

    Query params:
    - status: filter by one or more statuses (comma-separated)
    - author: username
    - category: slug
    - search: title/summary/body
    - ordering: -updated_at (default), -published_at, -views_count
    - page, page_size
    """

    permission_classes = [IsEditor]
    serializer_class = PostCardSerializer
    pagination_class = PostPagination

    def get_queryset(self):
        qs = (
            Post.objects.select_related("author", "category")
            .prefetch_related("tags")
            .annotate(
                like_count=Count("likes", distinct=True),
                comment_count=Count(
                    "comments",
                    filter=Q(
                        comments__status="approved",
                        comments__is_deleted=False,
                    ),
                    distinct=True,
                ),
                bookmark_count=Count("bookmarks", distinct=True),
            )
        )

        # Status filter (comma-separated)
        status_param = self.request.query_params.get("status")
        if status_param:
            statuses = [s.strip() for s in status_param.split(",") if s.strip()]
            valid = {choice[0] for choice in Post.Status.choices}
            invalid = set(statuses) - valid
            if invalid:
                raise ValidationError(
                    {
                        "status": (
                            f"Invalid status values: {', '.join(invalid)}. "
                            f"Valid: {', '.join(valid)}"
                        )
                    }
                )
            qs = qs.filter(status__in=statuses)

        # Author filter
        author = self.request.query_params.get("author")
        if author:
            qs = qs.filter(author__username=author)

        # Category filter
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category__slug=category)

        # Search
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(summary__icontains=search))

        # Ordering
        ordering = self.request.query_params.get("ordering", "-updated_at")
        allowed = {
            "updated_at",
            "-updated_at",
            "created_at",
            "-created_at",
            "published_at",
            "-published_at",
            "views_count",
            "-views_count",
            "title",
            "-title",
        }
        if ordering not in allowed:
            raise ValidationError(
                {"ordering": f"Invalid. Choose from: {', '.join(allowed)}"}
            )
        qs = qs.order_by(ordering)

        return qs
