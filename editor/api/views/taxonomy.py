# editor/views_taxonomy.py
from django.db import transaction
from django.db.models import Count, Q
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from blog.api.permissions import IsEditor
from blog.api.serializers import CategorySerializer, TagSerializer
from blog.models import Category, Tag
from editor.api.serializers import TagMergeSerializer

# ============================================================
# Category CRUD
# ============================================================


class CategoryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "image",
            "parent",
            "order",
            "is_active",
        ]
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
        }


class EditorCategoryViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for categories.
    list:    GET    /api/v1/editor/categories/
    create:  POST   /api/v1/editor/categories/
    update:  PATCH  /api/v1/editor/categories/<slug>/
    destroy: DELETE /api/v1/editor/categories/<slug>/
    """

    permission_classes = [IsEditor]
    lookup_field = "slug"

    def get_queryset(self):
        return (
            Category.objects.select_related("parent")
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
            .order_by("order", "name")
        )

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return CategoryWriteSerializer
        return CategorySerializer

    def perform_destroy(self, instance):
        # Prevent deleting a category with posts
        if instance.posts.exists():
            raise ValidationError(
                {
                    "detail": (
                        f'Cannot delete category "{instance.name}" '
                        f"because it has {instance.posts.count()} posts."
                    )
                }
            )
        instance.delete()


# ============================================================
# Tag CRUD
# ============================================================


class TagWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
        }


class EditorTagViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for tags.
    list:    GET    /api/v1/editor/tags/
    create:  POST   /api/v1/editor/tags/
    update:  PATCH  /api/v1/editor/tags/<slug>/
    destroy: DELETE /api/v1/editor/tags/<slug>/
    merge:   POST   /api/v1/editor/tags/merge/
    """

    permission_classes = [IsEditor]
    lookup_field = "slug"

    def get_queryset(self):
        return Tag.objects.all().order_by("-usage_count", "name")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return TagWriteSerializer
        return TagSerializer

    def perform_destroy(self, instance):
        if instance.usage_count > 0:
            raise ValidationError(
                {
                    "detail": (
                        f'Cannot delete tag "{instance.name}" '
                        f"because it is used by {instance.usage_count} posts."
                    )
                }
            )
        instance.delete()

    @action(detail=False, methods=["post"], url_path="merge")
    def merge(self, request):
        payload = TagMergeSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        source_ids = payload.validated_data["source_ids"]
        target_id = payload.validated_data["target_id"]

        source_tags = Tag.objects.filter(pk__in=source_ids)
        if source_tags.count() != len(source_ids):
            raise ValidationError({"source_ids": "Some tag IDs do not exist."})

        try:
            target = Tag.objects.get(pk=target_id)
        except Tag.DoesNotExist:
            raise ValidationError({"target_id": "Target tag does not exist."}) from None

        with transaction.atomic():
            for tag in source_tags:
                # Move posts from source tag to target tag
                for post in tag.posts.all():
                    post.tags.add(target)
                    post.tags.remove(tag)
                tag.delete()

            target.update_usage_count()

        return Response(TagSerializer(target).data)
