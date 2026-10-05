# blog/serializers.py
from rest_framework import serializers

from .models import Category, Post, Tag

# ============================================================
# Brief serializers (nested inside post cards)
# ============================================================


class AuthorBriefSerializer(serializers.Serializer):
    """
    Minimal author info shown inside a post card.
    Uses properties from the User model — no direct DB access.
    """

    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    avatar_url = serializers.CharField(read_only=True)


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
        ]


# ============================================================
# Sidebar serializers
# ============================================================


class CategorySerializer(serializers.ModelSerializer):
    """
    Category with post count.
    The queryset must annotate `post_count`.
    """

    post_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "image",
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
