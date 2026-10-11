"""
Behavioral tests for accounts.api.serializers.AuthorProfileSerializer.

Covers:
- Field inheritance from AuthorBriefSerializer / AuthorDetailSerializer.
- get_recent_posts: presence and shape when context supplies posts.
- get_recent_posts: fallback to an empty list when context is missing.
- get_recent_posts: `request` is propagated so allowed_actions is correct.
- get_stats: BUG — see TestGetStats for details.
"""

import pytest

from accounts.api.serializers import AuthorProfileSerializer
from accounts.models import SocialLink
from blog.models import Post


@pytest.mark.django_db
class TestAuthorProfileSerializerFields:
    def test_inherits_brief_and_detail_fields(self, test_author, api_request):
        SocialLink.objects.create(
            user=test_author,
            platform=SocialLink.Platform.GITHUB,
            url="https://github.com/example",
        )
        data = AuthorProfileSerializer(
            test_author, context={"request": api_request}
        ).data

        # From AuthorBriefSerializer
        assert data["id"] == test_author.pk
        assert data["username"] == test_author.username
        assert data["display_name"] == test_author.display_name
        assert "avatar_url" in data

        # From AuthorDetailSerializer
        assert "bio" in data
        assert "website" in data
        assert len(data["social_links"]) == 1

        # Added by AuthorProfileSerializer
        assert "stats" in data
        assert "recent_posts" in data


@pytest.mark.django_db
class TestGetRecentPosts:
    def test_returns_post_card_data_when_context_supplies_posts(
        self, test_author, test_published_post, api_request
    ):
        posts = list(Post.objects.published().filter(author=test_author).for_card())
        serializer = AuthorProfileSerializer(
            test_author,
            context={
                "request": api_request,
                "recent_posts": posts,
            },
        )
        data = serializer.data

        assert len(data["recent_posts"]) == 1
        first = data["recent_posts"][0]
        # PostCardSerializer fields
        assert first["id"] == test_published_post.pk
        assert first["title"] == test_published_post.title
        assert "allowed_actions" in first

    def test_returns_empty_list_when_context_has_no_recent_posts(
        self, test_author, api_request
    ):
        serializer = AuthorProfileSerializer(
            test_author, context={"request": api_request}
        )
        data = serializer.data

        assert data["recent_posts"] == []

    def test_allowed_actions_see_the_requesting_user(
        self, test_author, test_published_post, api_request
    ):
        """
        PostCardSerializer.get_allowed_actions uses request.user.
        If AuthorProfileSerializer fails to propagate context, the
        viewer would be treated as anonymous and allowed_actions
        would be all False.
        """
        api_request.user = test_author

        posts = list(Post.objects.published().filter(author=test_author).for_card())
        data = AuthorProfileSerializer(
            test_author,
            context={
                "request": api_request,
                "recent_posts": posts,
            },
        ).data

        actions = data["recent_posts"][0]["allowed_actions"]
        # test_author owns the post; can_preview must be True for the owner.
        assert actions["can_preview"] is True


@pytest.mark.django_db
class TestGetStats:
    """
    BUG (B1): AuthorViewSet.retrieve sets context["stats"], but
    AuthorProfileSerializer.get_stats reads context["stat"].

    Because the key names differ, `stats` in the serialized output
    is always `{}` regardless of the view's work.

    The tests below assert the CORRECT behavior and are expected to
    FAIL until the serializer is fixed. They are intentionally red.
    Do not weaken them to match the current broken behavior.
    """

    def test_stats_are_serialized_when_context_supplies_them(
        self, test_author, api_request
    ):
        expected = {
            "total_posts": 7,
            "total_views": 100,
            "total_likes": 20,
            "total_comments": 3,
            "total_bookmarks": 5,
        }
        serializer = AuthorProfileSerializer(
            test_author,
            context={
                "request": api_request,
                # Key matches what AuthorViewSet actually sets.
                "stats": expected,
            },
        )
        data = serializer.data

        # Currently fails: get_stats reads context["stat"].
        assert data["stats"] == expected

    def test_stats_default_to_empty_dict_when_context_is_missing(
        self, test_author, api_request
    ):
        """This test currently passes and must keep passing."""
        serializer = AuthorProfileSerializer(
            test_author, context={"request": api_request}
        )
        data = serializer.data

        assert data["stats"] == {}
