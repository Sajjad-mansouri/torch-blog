# editor/views_posts.py
from django.db import transaction
from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from blog.api.pagination import PostPagination
from blog.api.permissions import IsEditor
from blog.api.serializers import (
    EditorPostCardSerializer,
    PostCardSerializer,
    PostDetailSerializer,
)
from blog.models import Post
from editor.api.serializers import (
    FeaturedReorderSerializer,
    RejectPostSerializer,
    RequestChangesSerializer,
    UnpublishPostSerializer,
)
from editor.api.services import (
    approve_post,
    reject_post,
    request_changes,
    unpublish_post,
)

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
    serializer_class = EditorPostCardSerializer
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
    serializer_class = EditorPostCardSerializer
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


# ============================================================
# Post decisions
# ============================================================


class PostDecisionViewSet(viewsets.GenericViewSet):
    """
    approve:          POST /api/v1/editor/posts/<slug>/approve/
    reject:           POST /api/v1/editor/posts/<slug>/reject/
    request_changes:  POST /api/v1/editor/posts/<slug>/request-changes/
    unpublish:        POST /api/v1/editor/posts/<slug>/unpublish/
    """

    permission_classes = [IsEditor]
    lookup_field = "slug"
    queryset = Post.objects.select_related("author", "category")

    def get_object(self):
        return get_object_or_404(self.get_queryset(), slug=self.kwargs["slug"])

    def _respond(self, post):
        return Response(
            PostDetailSerializer(post, context={"request": self.request}).data
        )

    # ------------------------------------------------------------
    # Approve and publish
    # ------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, slug=None):
        post = self.get_object()
        try:
            approve_post(post, request.user)
        except ValueError as e:
            raise ValidationError({"detail": str(e)}) from None
        return self._respond(post)

    # ------------------------------------------------------------
    # Reject
    # ------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, slug=None):
        post = self.get_object()
        payload = RejectPostSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        try:
            reject_post(post, request.user, payload.validated_data["reason"])
        except ValueError as e:
            raise ValidationError({"detail": str(e)}) from None
        return self._respond(post)

    # ------------------------------------------------------------
    # Request changes
    # ------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="request-changes")
    def request_changes_action(self, request, slug=None):
        post = self.get_object()
        payload = RequestChangesSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        try:
            request_changes(post, request.user, payload.validated_data["note"])
        except ValueError as e:
            raise ValidationError({"detail": str(e)}) from None
        return self._respond(post)

    # ------------------------------------------------------------
    # Unpublish
    # ------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="unpublish")
    def unpublish(self, request, slug=None):
        post = self.get_object()
        payload = UnpublishPostSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        try:
            unpublish_post(
                post,
                request.user,
                payload.validated_data.get("reason", ""),
            )
        except ValueError as e:
            raise ValidationError({"detail": str(e)}) from None
        return self._respond(post)

    @action(detail=True, methods=["post"], url_path="reconsider")
    def reconsider(self, request, slug=None):
        """
        POST /api/v1/editor/posts/<slug>/reconsider/

        Moves a rejected or changes_requested post back to pending
        so it re-enters the review queue. Clears the previous
        decision metadata (rejection_reason, changes_requested_note)
        and the reviewer record.

        This is the undo path for an accidental decision.
        """
        post = self.get_object()

        allowed = {Post.Status.REJECTED, Post.Status.CHANGES_REQUESTED}
        if post.status not in allowed:
            raise ValidationError(
                {
                    "detail": (
                        f'Only posts in "rejected" or "changes_requested" '
                        f'can be reconsidered. Current status: "{post.status}".'
                    )
                }
            )

        with transaction.atomic():
            post.status = Post.Status.PENDING
            post.rejection_reason = ""
            post.changes_requested_note = ""
            post.reviewed_by = None
            post.reviewed_at = None
            post.save(
                update_fields=[
                    "status",
                    "rejection_reason",
                    "changes_requested_note",
                    "reviewed_by",
                    "reviewed_at",
                    "updated_at",
                ]
            )

        return self._respond(post)


# ============================================================
# Featured posts
# ============================================================


# editor/api/views_posts.py (replace the FeaturedPostsViewSet class)


class FeaturedPostsViewSet(viewsets.GenericViewSet):
    """
    list:      GET    /api/v1/editor/featured/
    candidates:GET    /api/v1/editor/featured/candidates/
    add:       POST   /api/v1/editor/featured/<slug>/add/
    remove:    DELETE /api/v1/editor/featured/<slug>/remove/
    reorder:   PATCH  /api/v1/editor/featured/reorder/
    """

    permission_classes = [IsEditor]
    serializer_class = PostCardSerializer
    lookup_field = "slug"

    # ------------------------------------------------------------
    # Base querysets
    # ------------------------------------------------------------

    def get_queryset(self):
        """Currently featured posts, in display order."""
        return (
            Post.objects.filter(is_featured=True, is_deleted=False)
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
            .order_by("featured_order", "-published_at")
        )

    def _candidate_queryset(self):
        """
        Posts eligible to be featured: published, not deleted,
        not already featured.
        """
        return (
            Post.objects.filter(
                status=Post.Status.PUBLISHED,
                is_deleted=False,
                is_featured=False,
            )
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
            .order_by("-published_at")
        )

    # ------------------------------------------------------------
    # List
    # ------------------------------------------------------------

    def list(self, request):
        qs = self.get_queryset()
        serializer = self.get_serializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    # ------------------------------------------------------------
    # Candidates — published posts not yet featured
    # ------------------------------------------------------------

    @action(detail=False, methods=["get"], url_path="candidates")
    def candidates(self, request):
        """
        GET /api/v1/editor/featured/candidates/?search=&page=

        Returns published, non-featured posts for the "add to
        featured" picker. Supports search across title/summary.
        """
        qs = self._candidate_queryset()

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(summary__icontains=search))

        paginator = PostPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        if page is not None:
            serializer = self.get_serializer(
                page, many=True, context={"request": request}
            )
            return paginator.get_paginated_response(serializer.data)

        serializer = self.get_serializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    # ------------------------------------------------------------
    # Add a post to the featured set
    # ------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="add")
    def add(self, request, slug=None):
        """
        POST /api/v1/editor/featured/<slug>/add/

        Sets is_featured=True and appends the post to the end
        of the featured order.
        """
        post = get_object_or_404(
            Post,
            slug=slug,
            is_deleted=False,
            status=Post.Status.PUBLISHED,
        )

        if post.is_featured:
            raise ValidationError({"detail": "Post is already featured."})

        with transaction.atomic():
            max_order = (
                Post.objects.filter(is_featured=True, is_deleted=False)
                .aggregate(m=Max("featured_order"))
                .get("m")
            )
            next_order = 0 if max_order is None else max_order + 1

            post.is_featured = True
            post.featured_order = next_order
            post.save(update_fields=["is_featured", "featured_order", "updated_at"])

        serializer = self.get_serializer(post, context={"request": request})
        return Response(serializer.data, status=201)

    # ------------------------------------------------------------
    # Remove a post from the featured set
    # ------------------------------------------------------------

    @action(detail=True, methods=["delete"], url_path="remove")
    def remove(self, request, slug=None):
        """
        DELETE /api/v1/editor/featured/<slug>/remove/

        Clears is_featured and featured_order.
        """
        post = get_object_or_404(Post, slug=slug, is_deleted=False)

        if not post.is_featured:
            raise ValidationError({"detail": "Post is not featured."})

        post.is_featured = False
        post.featured_order = None
        post.save(update_fields=["is_featured", "featured_order", "updated_at"])

        return Response(status=204)

    # ------------------------------------------------------------
    # Reorder
    # ------------------------------------------------------------

    @action(detail=False, methods=["patch"], url_path="reorder")
    def reorder(self, request):
        """
        PATCH /api/v1/editor/featured/reorder/

        Payload:
        {
            "items": [
                {"id": 42, "order": 0},
                {"id": 43, "order": 1}
            ]
        }

        Only IDs that belong to the featured set are reordered.
        """
        payload = FeaturedReorderSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        items = payload.validated_data["items"]
        ids = [item["id"] for item in items]

        existing = set(
            Post.objects.filter(
                pk__in=ids, is_featured=True, is_deleted=False
            ).values_list("pk", flat=True)
        )
        missing = set(ids) - existing
        if missing:
            raise ValidationError(
                {
                    "items": (
                        f"Posts not found or not featured: "
                        f"{', '.join(str(i) for i in missing)}"
                    )
                }
            )

        with transaction.atomic():
            for item in items:
                Post.objects.filter(pk=item["id"]).update(featured_order=item["order"])

        qs = self.get_queryset()
        serializer = self.get_serializer(qs, many=True, context={"request": request})
        return Response(serializer.data)
