from rest_framework import serializers

from accounts.models import SocialLink


# Social link (nested inside author profile)
class SocialLinkSerializer(serializers.ModelSerializer):
    platform_display = serializers.CharField(
        source="get_platform_display", read_only=True
    )

    class Meta:
        model = SocialLink
        fields = ["id", "platform", "platform_display", "url", "username", "order"]


# Author — brief (nested inside post cards)
class AuthorBriefSerializer(serializers.Serializer):
    """
    Minimal author info shown inside a post card.
    Uses User model properties display_name and avatar_url.
    """

    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    avatar_url = serializers.SerializerMethodField()

    def get_avatar_url(self, obj):
        request = self.context.get("request")
        url = obj.avatar_url
        if request is not None:
            return request.build_absolute_uri(url)
        return url


# Author — detail (post detail page)
# Inherits from brief, adds bio, website, and social links.


class AuthorDetailSerializer(AuthorBriefSerializer):
    bio = serializers.CharField(read_only=True)
    website = serializers.CharField(read_only=True)
    social_links = SocialLinkSerializer(many=True, read_only=True)


# Author — profile (author page)
# Extends detail with aggregate stats and a preview of posts.
class AuthorProfileSerializer(AuthorDetailSerializer):
    """
    Full author profile for /api/v1/authors/<username>/.

    - Inherits: id, username, display_name, avatar_url,
      bio, website, social_links
    - Adds: stats (aggregate counts) and recent_posts (PostCard[])
    """

    stats = serializers.SerializerMethodField()
    recent_posts = serializers.SerializerMethodField()

    def get_stats(self, obj):
        # The view precomputes stats and passes them via context
        # to avoid running the aggregate query once per author.
        return self.context.get("stat", {})

    def get_recent_posts(self, obj):
        from blog.api.serializers import PostCardSerializer

        recent = self.context.get("recent_posts", [])
        return PostCardSerializer(recent, many=True, context=self.context).data
