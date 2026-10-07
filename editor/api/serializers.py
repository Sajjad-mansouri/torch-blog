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
