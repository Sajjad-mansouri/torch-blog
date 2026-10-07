# editor/views_comments.py
from django.shortcuts import get_object_or_404
from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from blog.pagination import PostPagination
from blog.permissions import IsEditor
from interactions.models import Comment
from interactions.serializers import CommentSerializer

# ============================================================
# Comment moderation list
# ============================================================


class EditorCommentListView(generics.ListAPIView):
    """
    GET /api/v1/editor/comments/

    Query params:
    - status: pending | approved | rejected | spam (default: all)
    - post: slug
    - author: username
    - search: body
    - ordering: -created_at (default)
    """

    permission_classes = [IsEditor]
    serializer_class = CommentSerializer
    pagination_class = PostPagination

    def get_queryset(self):
        qs = Comment.objects.select_related("post", "author", "parent").order_by(
            "-created_at"
        )

        # Status filter
        status_param = self.request.query_params.get("status")
        if status_param:
            valid = {choice[0] for choice in Comment.Status.choices}
            if status_param not in valid:
                raise ValidationError(
                    {"status": f"Invalid. Choose from: {', '.join(valid)}"}
                )
            qs = qs.filter(status=status_param)

        # Post filter
        post_slug = self.request.query_params.get("post")
        if post_slug:
            qs = qs.filter(post__slug=post_slug)

        # Author filter
        author = self.request.query_params.get("author")
        if author:
            qs = qs.filter(author__username=author)

        # Search in body
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(body__icontains=search)

        # Ordering
        ordering = self.request.query_params.get("ordering", "-created_at")
        allowed = {
            "created_at",
            "-created_at",
            "updated_at",
            "-updated_at",
        }
        if ordering not in allowed:
            raise ValidationError(
                {"ordering": f"Invalid. Choose from: {', '.join(allowed)}"}
            )
        qs = qs.order_by(ordering)

        return qs

    def get_serializer_context(self):
        # Editors see comment data without "liked" flags
        return {
            "request": self.request,
            "liked_comment_ids": set(),
        }


# ============================================================
# Comment moderation actions
# ============================================================


class CommentModerationViewSet(viewsets.GenericViewSet):
    """
    approve: POST /api/v1/editor/comments/<id>/approve/
    reject:  POST /api/v1/editor/comments/<id>/reject/
    spam:    POST /api/v1/editor/comments/<id>/spam/
    delete:  DELETE /api/v1/editor/comments/<id>/
    """

    permission_classes = [IsEditor]
    queryset = Comment.objects.select_related("author", "post")

    def get_object(self):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])

    def _respond(self, comment):
        return Response(
            CommentSerializer(
                comment,
                context={"request": self.request, "liked_comment_ids": set()},
            ).data
        )

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        comment = self.get_object()
        comment.status = Comment.Status.APPROVED
        comment.save(update_fields=["status", "updated_at"])
        return self._respond(comment)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        comment = self.get_object()
        comment.status = Comment.Status.REJECTED
        comment.save(update_fields=["status", "updated_at"])
        return self._respond(comment)

    @action(detail=True, methods=["post"], url_path="spam")
    def spam(self, request, pk=None):
        comment = self.get_object()
        comment.status = Comment.Status.SPAM
        comment.save(update_fields=["status", "updated_at"])
        return self._respond(comment)

    @action(detail=True, methods=["delete"], url_path="delete")
    def soft_delete(self, request, pk=None):
        comment = self.get_object()
        comment.soft_delete(request.user)
        return Response(status=204)
