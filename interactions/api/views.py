# interactions/views.py
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from blog.api.pagination import PostPagination
from blog.api.serializers import PostCardSerializer
from blog.models import Post
from interactions.models import Bookmark, Comment, CommentLike, Like

from .serializers import (
    CommentSerializer,
    CommentWriteSerializer,
    ToggleResponseSerializer,
)
from .services import (
    create_comment,
    toggle_bookmark,
    toggle_comment_like,
    toggle_like,
)

# ============================================================
# Post like / bookmark toggles
# ============================================================


class PostLikeToggleView(APIView):
    """
    POST /api/v1/posts/<slug>/like/
    Toggles a like on the post.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        post = get_object_or_404(Post.objects.published(), slug=slug)
        liked, count = toggle_like(request.user, post)
        return Response(
            ToggleResponseSerializer(
                {
                    "active": liked,
                    "count": count,
                }
            ).data
        )


class PostBookmarkToggleView(APIView):
    """
    POST /api/v1/posts/<slug>/bookmark/
    Toggles a bookmark on the post.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        post = get_object_or_404(Post.objects.published(), slug=slug)
        bookmarked, count = toggle_bookmark(request.user, post)
        return Response(
            ToggleResponseSerializer(
                {
                    "active": bookmarked,
                    "count": count,
                }
            ).data
        )


# ============================================================
# Comment like toggle
# ============================================================


class CommentLikeToggleView(APIView):
    """
    POST /api/v1/comments/<id>/like/
    Toggles a like on the comment.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        comment = get_object_or_404(
            Comment.objects.filter(
                status=Comment.Status.APPROVED,
                is_deleted=False,
            ),
            pk=pk,
        )
        liked, count = toggle_comment_like(request.user, comment)
        return Response(
            ToggleResponseSerializer(
                {
                    "active": liked,
                    "count": count,
                }
            ).data
        )


# ============================================================
# Comments nested under post
# ============================================================


class PostCommentsView(APIView):
    """
    GET  /api/v1/posts/<slug>/comments/   → list comments
    POST /api/v1/posts/<slug>/comments/   → create comment
    """

    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = PostPagination

    # ------------------------------------------------------------
    # GET — list
    # ------------------------------------------------------------

    def get(self, request, slug):
        post = get_object_or_404(Post.objects.published(), slug=slug)

        top_level = (
            Comment.objects.filter(
                post=post,
                parent__isnull=True,
                status=Comment.Status.APPROVED,
                is_deleted=False,
            )
            .select_related("author")
            .prefetch_related(
                Prefetch(
                    "replies",
                    queryset=Comment.objects.filter(
                        status=Comment.Status.APPROVED,
                        is_deleted=False,
                    )
                    .select_related("author")
                    .annotate(like_count=Count("likes", distinct=True))
                    .order_by("created_at"),
                ),
            )
            .annotate(like_count=Count("likes", distinct=True))
            .order_by("created_at")
        )

        # Which comments has the current user liked?
        liked_ids = set()
        if request.user.is_authenticated:
            liked_ids = set(
                CommentLike.objects.filter(
                    user=request.user, comment__post=post
                ).values_list("comment_id", flat=True)
            )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(top_level, request, view=self)

        serializer = CommentSerializer(
            page if page is not None else top_level,
            many=True,
            context={
                "request": request,
                "liked_comment_ids": liked_ids,
            },
        )

        if page is not None:
            return paginator.get_paginated_response(serializer.data)
        return Response(serializer.data)

    # ------------------------------------------------------------
    # POST — create
    # ------------------------------------------------------------

    def post(self, request, slug):
        post = get_object_or_404(Post.objects.published(), slug=slug)

        serializer = CommentWriteSerializer(
            data=request.data,
            context={"request": request, "post": post},
        )
        serializer.is_valid(raise_exception=True)

        parent_id = serializer.validated_data.get("parent")
        body = serializer.validated_data["body"]

        comment = create_comment(
            user=request.user,
            post=post,
            body=body,
            parent_id=parent_id,
        )

        # Build a response with the same shape as the list
        liked_ids = {comment.id} if False else set()
        out = CommentSerializer(
            comment,
            context={
                "request": request,
                "liked_comment_ids": liked_ids,
            },
        )
        return Response(out.data, status=status.HTTP_201_CREATED)


# ============================================================
# Comment edit / delete
# ============================================================


class CommentDetailView(APIView):
    """
    PATCH  /api/v1/comments/<id>/   → edit own comment
    DELETE /api/v1/comments/<id>/   → soft delete own comment
    """

    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(
            Comment.objects.select_related("author"),
            pk=pk,
            is_deleted=False,
        )

    # ------------------------------------------------------------
    # PATCH — edit
    # ------------------------------------------------------------

    def patch(self, request, pk):
        comment = self.get_object(pk)

        # Owner-only edit
        if comment.author != request.user:
            raise PermissionDenied("You can only edit your own comments.")

        serializer = CommentWriteSerializer(
            comment,
            data=request.data,
            partial=True,
            context={"request": request, "post": comment.post},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        comment.mark_edited()

        out = CommentSerializer(
            comment,
            context={
                "request": request,
                "liked_comment_ids": set(),
            },
        )
        return Response(out.data)

    # ------------------------------------------------------------
    # DELETE — soft delete
    # ------------------------------------------------------------

    def delete(self, request, pk):
        comment = self.get_object(pk)

        # Owner or editor
        if comment.author != request.user and not request.user.is_editor:
            raise PermissionDenied("You can only delete your own comments.")

        comment.soft_delete(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================================
# Me — liked posts, bookmarked posts
# ============================================================


class MeLikeListView(APIView):
    """
    GET /api/v1/me/likes/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        post_ids = (
            Like.objects.filter(user=request.user)
            .order_by("-created_at")
            .values_list("post_id", flat=True)
        )
        qs = (
            Post.objects.filter(pk__in=post_ids, is_deleted=False)
            .for_card()
            .order_by("-published_at")
        )
        paginator = PostPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = PostCardSerializer(
            page if page is not None else qs,
            many=True,
            context={"request": request},
        )
        if page is not None:
            return paginator.get_paginated_response(serializer.data)
        return Response(serializer.data)


class MeBookmarkListView(APIView):
    """
    GET /api/v1/me/bookmarks/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        post_ids = (
            Bookmark.objects.filter(user=request.user)
            .order_by("-created_at")
            .values_list("post_id", flat=True)
        )
        qs = (
            Post.objects.filter(pk__in=post_ids, is_deleted=False)
            .for_card()
            .order_by("-published_at")
        )
        paginator = PostPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = PostCardSerializer(
            page if page is not None else qs,
            many=True,
            context={"request": request},
        )
        if page is not None:
            return paginator.get_paginated_response(serializer.data)
        return Response(serializer.data)
