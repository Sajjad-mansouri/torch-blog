# blog/serializers_editor.py
from rest_framework import serializers

# ============================================================
# Decision payload serializers
# ============================================================


class RejectPostSerializer(serializers.Serializer):
    """Payload for POST /editor/posts/<slug>/reject/."""

    reason = serializers.CharField(
        max_length=2000,
        allow_blank=False,
        trim_whitespace=True,
    )


class RequestChangesSerializer(serializers.Serializer):
    """Payload for POST /editor/posts/<slug>/request-changes/."""

    note = serializers.CharField(
        max_length=2000,
        allow_blank=False,
        trim_whitespace=True,
    )


class UnpublishPostSerializer(serializers.Serializer):
    """Payload for POST /editor/posts/<slug>/unpublish/."""

    reason = serializers.CharField(
        max_length=2000,
        allow_blank=True,
        required=False,
        default="",
        trim_whitespace=True,
    )


# ============================================================
# Featured reorder
# ============================================================


class FeaturedReorderItemSerializer(serializers.Serializer):
    """One entry in the reorder payload."""

    id = serializers.IntegerField()
    order = serializers.IntegerField(min_value=0)


class FeaturedReorderSerializer(serializers.Serializer):
    """
    Payload for PATCH /editor/featured/reorder/.

    Example:
    {
        "items": [
            {"id": 42, "order": 0},
            {"id": 43, "order": 1},
            {"id": 44, "order": 2}
        ]
    }
    """

    items = FeaturedReorderItemSerializer(many=True, allow_empty=False)

    def validate_items(self, value):
        ids = [item["id"] for item in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Duplicate post IDs in payload.")
        return value
