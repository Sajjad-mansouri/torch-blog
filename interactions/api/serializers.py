# interactions/serializers.py
from rest_framework import serializers

from blog.utils import clean_text
from interactions.models import Comment

# ============================================================
# Comment author (minimal, nested)
# ============================================================


class CommentAuthorSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True, allow_null=True)
    username = serializers.CharField(read_only=True, allow_null=True)
    display_name = serializers.CharField(read_only=True, allow_null=True)
    avatar_url = serializers.SerializerMethodField()

    def get_avatar_url(self, obj):
        if obj is None:
            return None
        request = self.context.get("request")
        url = obj.avatar_url
        if request is not None:
            return request.build_absolute_uri(url)
        return url


# ============================================================
# Comment read
# ============================================================


class CommentSerializer(serializers.ModelSerializer):
    """
    Comment with nested replies.

    Expects the following in serializer context:
    - request
    - liked_comment_ids: set of comment IDs the current user liked
    """

    author = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField(read_only=True)
    is_liked = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "body",
            "author",
            "parent",
            "created_at",
            "edited_at",
            "is_deleted",
            "like_count",
            "is_liked",
            "replies",
            "status",
        ]

    def get_author(self, obj):
        if obj.author is None:
            return {
                "id": None,
                "username": None,
                "display_name": "[deleted]",
                "avatar_url": None,
            }
        return CommentAuthorSerializer(obj.author, context=self.context).data

    def get_is_liked(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.id in self.context.get("liked_comment_ids", set())

    def get_replies(self, obj):
        # Only include approved, non-deleted replies
        replies = obj.replies.filter(
            status=Comment.Status.APPROVED,
            is_deleted=False,
        ).order_by("created_at")
        return CommentSerializer(
            replies,
            many=True,
            context=self.context,
        ).data

    def get_like_count(self, obj):
        if hasattr(obj, "_like_count"):
            return obj._like_count
        return obj.likes.count()


# ============================================================
# Comment write
# ============================================================


class CommentWriteSerializer(serializers.ModelSerializer):
    """
    Create or update a comment.
    Handles sanitization and length validation.
    """

    parent = serializers.IntegerField(
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = Comment
        fields = ["body", "parent"]

    def validate_body(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Comment cannot be empty.")

        # Comments are plain text — strip any HTML
        cleaned = clean_text(value)[:2000]
        if not cleaned:
            raise serializers.ValidationError(
                "Comment cannot be empty after sanitization."
            )
        return cleaned

    def validate_parent(self, value):
        if value is None:
            return value

        # On create, parent must belong to the same post
        post = self.context.get("post")
        if post is None:
            return value

        exists = Comment.objects.filter(
            pk=value,
            post=post,
            is_deleted=False,
        ).exists()
        if not exists:
            raise serializers.ValidationError("Parent comment not found on this post.")
        return value

    def update(self, instance, validated_data):
        # Parent is not changeable via PATCH.
        validated_data.pop("parent", None)
        return super().update(instance, validated_data)


# ============================================================
# Toggle response
# ============================================================


class ToggleResponseSerializer(serializers.Serializer):
    """
    Standard response for like/bookmark toggles.
    `active` = whether the resource is now liked/bookmarked.
    """

    active = serializers.BooleanField()
    count = serializers.IntegerField()
