# blog/serializers.py
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

# Import author serializers from accounts
from accounts.api.serializers import (
    AuthorBriefSerializer,
    AuthorDetailSerializer,
)
from blog.models import Category, Post, Tag
from blog.utils import clean_text, sanitize_html
from interactions.models import Comment

# ============================================================
# Brief serializers (nested inside post cards)
# ============================================================


class CategoryBriefSerializer(serializers.Serializer):
    """Minimal category info shown inside a post card."""

    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    slug = serializers.SlugField(read_only=True)


# ============================================================
# Post card — used in Home, List, Category, Tag, Search, Author
# ============================================================


class PostCardSerializer(serializers.ModelSerializer):
    """
    Lightweight post representation for lists.

    IMPORTANT: the queryset must be built with `.for_card()`
    so that like_count, comment_count, and bookmark_count are
    annotated. Otherwise DRF falls back to model properties
    and triggers N+1 queries.
    """

    author = AuthorBriefSerializer(read_only=True)
    category = CategoryBriefSerializer(read_only=True)

    like_count = serializers.IntegerField(read_only=True)
    comment_count = serializers.IntegerField(read_only=True)
    bookmark_count = serializers.IntegerField(read_only=True)

    allowed_actions = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "title",
            "slug",
            "summary",
            "featured_image",
            "author",
            "category",
            "published_at",
            "views_count",
            "reading_time",
            "like_count",
            "comment_count",
            "bookmark_count",
            "status",
            "updated_at",
            "allowed_actions",
        ]

    def get_allowed_actions(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            return {
                "can_edit": False,
                "can_delete": False,
                "can_submit": False,
                "can_preview": False,
                "can_view_public": True,
            }

        # Preview: authors/editors on their own posts, in any status.
        # A dedicated preview page shows the post as it would appear
        # without exposing it publicly.
        can_preview = user.is_editor or user == obj.author

        return {
            "can_edit": obj.can_be_edited_by(user),
            "can_delete": obj.can_be_deleted_by(user),
            "can_submit": obj.can_be_submitted_by(user),
            "can_preview": can_preview,
            "can_view_public": bool(obj.published_at) and not obj.is_deleted,
        }


class EditorPostCardSerializer(PostCardSerializer):
    """
    Extends PostCardSerializer with fields only editors should see.

    Used by:
      - editor.api.views.ReviewQueueView
      - editor.api.views.EditorPostListView

    Never use this on a public-facing endpoint.
    """

    rejection_reason = serializers.CharField(read_only=True)
    changes_requested_note = serializers.CharField(read_only=True)
    reviewed_by = AuthorBriefSerializer(read_only=True)
    reviewed_at = serializers.DateTimeField(read_only=True)

    class Meta(PostCardSerializer.Meta):
        fields = PostCardSerializer.Meta.fields + [
            "rejection_reason",
            "changes_requested_note",
            "reviewed_by",
            "reviewed_at",
        ]


# ============================================================
# Sidebar serializers
# ============================================================


class CategoryParentSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    slug = serializers.SlugField(read_only=True)


class CategorySerializer(serializers.ModelSerializer):
    """
    Category with post count.
    The queryset must annotate `post_count`.
    """

    post_count = serializers.IntegerField(read_only=True)
    parent = CategoryParentSerializer(read_only=True)

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
            "post_count",
        ]


class TagSerializer(serializers.ModelSerializer):
    """Tag with usage count."""

    class Meta:
        model = Tag
        fields = [
            "id",
            "name",
            "slug",
            "usage_count",
        ]


# ============================================================
# Home — aggregate response
# ============================================================


class HomeSerializer(serializers.Serializer):
    """
    Container serializer for the home page response.
    Not tied to a model — just groups the sections.
    """

    featured = PostCardSerializer(many=True, read_only=True)
    latest = PostCardSerializer(many=True, read_only=True)
    trending = PostCardSerializer(many=True, read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    hot_tags = TagSerializer(many=True, read_only=True)


# ============================================================
# Comments
# ============================================================


class CommentAuthorSerializer(serializers.Serializer):
    """
    Author of a comment. Kept minimal — comments are small.
    """

    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True, allow_null=True)
    avatar_url = serializers.CharField(read_only=True, allow_null=True)


class CommentSerializer(serializers.ModelSerializer):
    """
    A single comment with its nested replies.

    - Only approved, non-deleted comments are serialized.
    - Replies are nested one level deep; deeper nesting is flattened
      by the queryset (see views.get_serializer_context).
    """

    author = serializers.SerializerMethodField()
    like_count = serializers.IntegerField(read_only=True)
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
        ]

    def get_author(self, obj):
        if obj.author is None:
            return {
                "id": None,
                "username": None,
                "display_name": "[deleted]",
                "avatar_url": None,
            }
        return CommentAuthorSerializer(obj.author).data

    def get_is_liked(self, obj):
        """
        Whether the current user has liked this comment.
        Requires 'request' in serializer context.
        """
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        # Assume the view prefetches comment likes for the current user
        # via a helper set on the serializer context.
        liked_ids = self.context.get("liked_comment_ids", set())
        return obj.id in liked_ids

    def get_replies(self, obj):
        """
        Return replies. Only include approved, non-deleted replies.
        Depth is limited to one level — deeper replies are attached
        to their top-level parent instead.
        """
        replies = obj.replies.filter(
            status="approved",
            is_deleted=False,
        ).order_by("created_at")
        return CommentSerializer(
            replies,
            many=True,
            context=self.context,
        ).data

    def get_like_count(self, obj):
        # Annotated value if present, property otherwise.
        if hasattr(obj, "_like_count"):
            return obj._like_count
        return obj.likes.count()


class PostDetailSerializer(serializers.ModelSerializer):
    """
    Full post detail.

    Includes:
    - The body (HTML)
    - Author, category, tags, extra_categories
    - Stats: views, reading time, like/comment/bookmark counts
    - User-specific: is_liked, is_bookmarked
    - Nested comments (top-level; replies nested inside each)
    - Similar posts (PostCard)
    - Author's other posts (PostCard)
    """

    author = AuthorDetailSerializer(read_only=True)
    category = CategoryBriefSerializer(read_only=True)
    extra_categories = CategoryBriefSerializer(read_only=True, many=True)
    tags = TagSerializer(many=True, read_only=True)

    like_count = serializers.IntegerField(read_only=True)
    comment_count = serializers.IntegerField(read_only=True)
    bookmark_count = serializers.IntegerField(read_only=True)

    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()

    comments = serializers.SerializerMethodField()
    similar_posts = serializers.SerializerMethodField()
    author_other_posts = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "title",
            "slug",
            "summary",
            "body",
            "featured_image",
            "author",
            "category",
            "extra_categories",
            "tags",
            "status",
            "published_at",
            "created_at",
            "updated_at",
            "views_count",
            "reading_time",
            "like_count",
            "comment_count",
            "bookmark_count",
            "is_liked",
            "is_bookmarked",
            "meta_title",
            "meta_description",
            "comments",
            "similar_posts",
            "author_other_posts",
        ]

    @extend_schema_field(serializers.BooleanField)
    def get_is_liked(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False

        liked_post_ids = self.context.get("liked_post_ids", set())
        return obj.id in liked_post_ids

    @extend_schema_field(serializers.BooleanField)
    def get_is_bookmarked(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        bookmarked_post_ids = self.context.get("bookmarked_post_ids", set())
        return obj.id in bookmarked_post_ids

    @extend_schema_field(CommentSerializer(many=True))
    def get_comments(self, obj):
        """
        Top-level comments with their replies.
        The view preloads these on the instance (see views.py),
        so this method does not hit the database.
        """

        top_level = self.context.get("top_level_comments")
        if top_level is None:
            # query directly .use only if the view didn't
            top_level = obj.comments.filter(
                status="approved", is_deleted=False, parent__isnull=True
            ).order_by("created_at")

        return CommentSerializer(top_level, many=True, context=self.context).data

    @extend_schema_field(PostCardSerializer(many=True))
    def get_similar_posts(self, obj):
        similar = self.context.get("similar_posts", [])
        return PostCardSerializer(similar, many=True).data

    @extend_schema_field(PostCardSerializer(many=True))
    def get_author_other_posts(self, obj):
        others = self.context.get("author_other_posts", [])
        return PostCardSerializer(others, many=True).data


class SearchResultSerializer(serializers.Serializer):
    """
    Wraps search results for a single type.
    Used by the mixed search endpoint.
    """

    type = serializers.CharField()
    count = serializers.IntegerField()
    results = serializers.ListField()


class SearchSuggestItemSerializer(serializers.Serializer):
    """
    A single suggestion item for the autocomplete endpoint.
    Kept intentionally minimal so the payload stays small.
    """

    type = serializers.ChoiceField(choices=["post", "tag", "author"])
    id = serializers.IntegerField()
    label = serializers.CharField()
    slug = serializers.CharField()
    url = serializers.CharField()


# ============================================================
# Post write serializer
# ============================================================


class PostWriteSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating posts.

    - Accepts only writable fields (no status, no counts, no SEO auto).
    - Sanitizes `body` and cleans `summary`.
    - Auto-generates `slug` if not provided.
    - Rejects duplicate titles per author (optional — see below).
    """

    class Meta:
        model = Post
        fields = [
            "title",
            "slug",
            "summary",
            "body",
            "featured_image",
            "category",
            "extra_categories",
            "tags",
            "meta_title",
            "meta_description",
            "og_image",
            "no_index",
        ]
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
            "summary": {"required": False, "allow_blank": True},
            "category": {"required": False, "allow_null": True},
            "meta_title": {"required": False, "allow_blank": True},
            "meta_description": {"required": False, "allow_blank": True},
        }

    # ------------------------------------------------------------
    # Field-level validation and cleaning
    # ------------------------------------------------------------
    def to_internal_value(self, data):
        # multipart FormData: getlist/setlist available
        data = data.copy()
        if hasattr(data, "getlist") and hasattr(data, "setlist"):
            for field in ("tags", "extra_categories"):
                values = [v for v in data.getlist(field) if v not in ("", None)]
                data.setlist(field, values)
        return super().to_internal_value(data)

    def validate_title(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters.")
        return value

    def validate_summary(self, value):
        if not value:
            return value
        # Strip any HTML the client might have sent
        return clean_text(value)[:500]

    def validate_body(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Body cannot be empty.")
        # Sanitize HTML — remove scripts, event handlers, etc.
        cleaned = sanitize_html(value)
        if not cleaned.strip():
            raise serializers.ValidationError(
                "Body cannot be empty after sanitization."
            )
        return cleaned

    def validate_meta_title(self, value):
        return value.strip() if value else value

    def validate_meta_description(self, value):
        return value.strip() if value else value

    # ------------------------------------------------------------
    # Object-level validation
    # ------------------------------------------------------------

    def validate(self, attrs):
        # Prevent category = extra_categories duplication
        category = attrs.get("category")
        extra_categories = attrs.get("extra_categories")
        if category and extra_categories:
            if category in extra_categories:
                raise serializers.ValidationError(
                    {
                        "extra_categories": (
                            "The primary category cannot also appear "
                            "in extra_categories."
                        )
                    }
                )
        return attrs
