# editor/views_log.py

from rest_framework import generics
from rest_framework.exceptions import ValidationError

from blog.api.pagination import PostPagination
from blog.api.permissions import IsEditor
from core.api.serializers import ActivityLogSerializer
from core.models import ActivityLog


class EditorActivityLogView(generics.ListAPIView):
    """
    GET /api/v1/editor/activity-log/

    Query params:
    - user: username
    - action: log action code
    - target_type: model name (e.g., 'post', 'comment')
    - target_id: integer
    - date_from: YYYY-MM-DD
    - date_to: YYYY-MM-DD
    - page, page_size
    """

    permission_classes = [IsEditor]
    serializer_class = ActivityLogSerializer
    pagination_class = PostPagination

    def get_queryset(self):
        qs = ActivityLog.objects.select_related("user").order_by("-created_at")

        user = self.request.query_params.get("user")
        if user:
            qs = qs.filter(user__username=user)

        action = self.request.query_params.get("action")
        if action:
            qs = qs.filter(action=action)

        target_type = self.request.query_params.get("target_type")
        if target_type:
            qs = qs.filter(target_type=target_type)

        target_id = self.request.query_params.get("target_id")
        if target_id:
            try:
                qs = qs.filter(target_id=int(target_id))
            except ValueError:
                raise ValidationError({"target_id": "Must be an integer."}) from None

        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        return qs
