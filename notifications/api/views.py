# notifications/views.py
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from blog.api.pagination import PostPagination
from notifications.models import Notification

from .serializers import NotificationSerializer


class NotificationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    list:      GET    /api/v1/notifications/
    retrieve:  GET    /api/v1/notifications/<id>/
    destroy:   DELETE /api/v1/notifications/<id>/
    mark_read: POST   /api/v1/notifications/<id>/read/
    read_all:  POST   /api/v1/notifications/read-all/
    unread_count: GET /api/v1/notifications/unread-count/
    clear:     DELETE /api/v1/notifications/clear/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    pagination_class = PostPagination

    def get_queryset(self):
        """
        Every user only sees their own notifications.
        Never expose notifications for other users.
        """
        return Notification.objects.filter(recipient=self.request.user).select_related(
            "actor", "target_type"
        )

    # ------------------------------------------------------------
    # List with filters
    # ------------------------------------------------------------

    def list(self, request, *args, **kwargs):
        """
        Query params:
        - is_read: true | false (default: all)
        - verb: filter by verb
        """
        qs = self.get_queryset()

        is_read = request.query_params.get("is_read")
        if is_read is not None:
            qs = qs.filter(is_read=is_read.lower() == "true")

        verb = request.query_params.get("verb")
        if verb:
            valid = {choice[0] for choice in Notification.Verb.choices}
            if verb not in valid:
                return Response(
                    {"verb": f"Invalid. Choose from: {', '.join(valid)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            qs = qs.filter(verb=verb)

        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(
            page if page is not None else qs,
            many=True,
            context={"request": request},
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    # ------------------------------------------------------------
    # Mark one as read
    # ------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_as_read()

        serializer = self.get_serializer(notification, context={"request": request})
        return Response(serializer.data)

    # ------------------------------------------------------------
    # Mark all as read
    # ------------------------------------------------------------

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        """
        Mark every unread notification for the current user as read.
        Returns the number of notifications affected.
        """
        now = timezone.now()
        updated = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True, read_at=now)
        return Response({"updated": updated})

    # ------------------------------------------------------------
    # Unread count
    # ------------------------------------------------------------

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        """
        Return the number of unread notifications. Used for the
        badge in the UI. Fast: hits an index.
        """
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        return Response({"unread": count})

    # ------------------------------------------------------------
    # Clear all notifications
    # ------------------------------------------------------------

    @action(detail=False, methods=["delete"], url_path="clear")
    def clear(self, request):
        """
        Delete every notification for the current user.
        The user can't delete other users' notifications.
        """
        deleted, _ = Notification.objects.filter(recipient=request.user).delete()
        return Response({"deleted": deleted})
