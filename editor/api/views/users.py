# editor/views_users.py
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from accounts.api.serializers import AuthorBriefSerializer
from accounts.models import User
from blog.api.pagination import PostPagination
from blog.api.permissions import IsEditor

# ============================================================
# User list
# ============================================================


class EditorUserListView(generics.ListAPIView):
    """
    GET /api/v1/editor/users/

    Query params:
    - role: reader | author | editor
    - search: username, first_name, last_name, email
    - is_active: true | false
    - ordering: username (default), -date_joined
    """

    permission_classes = [IsEditor]
    serializer_class = AuthorBriefSerializer
    pagination_class = PostPagination

    def get_queryset(self):
        qs = (
            User.objects.select_related()
            .annotate(
                post_count=Count(
                    "posts",
                    filter=Q(
                        posts__status="published",
                        posts__is_deleted=False,
                    ),
                    distinct=True,
                ),
            )
            .order_by("username")
        )

        # Role filter
        role = self.request.query_params.get("role")
        if role:
            valid = {choice[0] for choice in User.Role.choices}
            if role not in valid:
                raise ValidationError(
                    {"role": f"Invalid. Choose from: {', '.join(valid)}"}
                )
            qs = qs.filter(role=role)

        # Active filter
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")

        # Search
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
            )

        # Ordering
        ordering = self.request.query_params.get("ordering", "username")
        allowed = {
            "username",
            "-username",
            "date_joined",
            "-date_joined",
            "post_count",
            "-post_count",
        }
        if ordering not in allowed:
            raise ValidationError(
                {"ordering": f"Invalid. Choose from: {', '.join(allowed)}"}
            )
        qs = qs.order_by(ordering)

        return qs


# ============================================================
# Role change and ban
# ============================================================


class UserRoleSerializer(serializers.Serializer):
    """Payload for role change."""

    role = serializers.ChoiceField(choices=User.Role.choices)


class UserBanSerializer(serializers.Serializer):
    """Payload for ban/unban."""

    reason = serializers.CharField(
        max_length=500,
        allow_blank=True,
        required=False,
        default="",
    )


class EditorUserDetailViewSet(viewsets.GenericViewSet):
    """
    change_role:  PATCH  /api/v1/editor/users/<id>/role/
    ban:          POST   /api/v1/editor/users/<id>/ban/
    unban:        POST   /api/v1/editor/users/<id>/unban/
    """

    permission_classes = [IsEditor]
    queryset = User.objects.all()

    def get_object(self):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])

    @action(detail=True, methods=["patch"], url_path="role")
    def change_role(self, request, pk=None):
        user = self.get_object()

        if user == request.user:
            raise ValidationError({"detail": "You cannot change your own role."})

        payload = UserRoleSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        new_role = payload.validated_data["role"]
        if user.role == new_role:
            return Response(
                {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "changed": False,
                }
            )

        old_role = user.role
        user.role = new_role
        user.save(update_fields=["role", "updated_at"])

        return Response(
            {
                "id": user.id,
                "username": user.username,
                "old_role": old_role,
                "role": new_role,
                "changed": True,
            }
        )

    @action(detail=True, methods=["post"], url_path="ban")
    def ban(self, request, pk=None):
        user = self.get_object()

        if user == request.user:
            raise ValidationError({"detail": "You cannot ban yourself."})
        if user.is_editor:
            raise ValidationError(
                {"detail": "Editors cannot be banned via this endpoint."}
            )

        payload = UserBanSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])

        return Response(
            {
                "id": user.id,
                "username": user.username,
                "is_active": False,
            }
        )

    @action(detail=True, methods=["post"], url_path="unban")
    def unban(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=["is_active", "updated_at"])
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "is_active": True,
            }
        )
