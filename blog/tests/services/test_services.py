"""
Behavioral tests for blog.api.services.

Coverage:
- record_view: dedup across three identity branches (user,
  session_key, ip+user_agent), and side effects on views_count.
- get_similar_posts: tag-overlap ranking, category fallback,
  exclusions.
- get_author_other_posts: same-author filtering, ordering,
  exclusions.

All assertions reflect the actual observable behavior of the
current implementation. Where the behavior deserves a note, it
is called out in the test name or docstring.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from blog.api.services import (
    get_author_other_posts,
    get_similar_posts,
    record_view,
)
from blog.models import Post, PostView


# ==================================================================
# record_view
# ==================================================================
@pytest.mark.django_db
class TestRecordViewAnonymousByIp:
    def test_first_anonymous_view_creates_post_view_row(
        self, anonymous_request, test_published_post
    ):
        created = record_view(anonymous_request, test_published_post)

        assert created is True
        assert PostView.objects.filter(post=test_published_post).count() == 1

    def test_first_anonymous_view_increments_views_count(
        self, anonymous_request, test_published_post
    ):
        original = test_published_post.views_count

        record_view(anonymous_request, test_published_post)

        test_published_post.refresh_from_db()
        assert test_published_post.views_count == original + 1

    def test_duplicate_anonymous_view_within_window_is_deduplicated(
        self, anonymous_request, test_published_post
    ):
        record_view(anonymous_request, test_published_post)
        second = record_view(anonymous_request, test_published_post)

        assert second is False
        assert PostView.objects.filter(post=test_published_post).count() == 1

    def test_duplicate_anonymous_view_does_not_increment_views_count(
        self, anonymous_request, test_published_post
    ):
        record_view(anonymous_request, test_published_post)
        original = test_published_post.views_count

        record_view(anonymous_request, test_published_post)

        test_published_post.refresh_from_db()
        assert test_published_post.views_count == original

    def test_anonymous_view_with_different_user_agent_is_not_deduplicated(
        self, anonymous_request, test_published_post
    ):
        record_view(anonymous_request, test_published_post)

        # Same IP, different UA.
        anonymous_request.META["HTTP_USER_AGENT"] = "different-agent"
        second = record_view(anonymous_request, test_published_post)

        assert second is True
        assert PostView.objects.filter(post=test_published_post).count() == 2

    def test_anonymous_view_outside_window_is_not_deduplicated(
        self, anonymous_request, test_published_post
    ):
        # Pre-insert a PostView with a created_at well past the window.
        # created_at is auto_now_add, so we override it with an update().
        old_view = PostView.objects.create(
            post=test_published_post,
            ip_address="127.0.0.1",
            user_agent="pytest",
        )
        PostView.objects.filter(pk=old_view.pk).update(
            created_at=timezone.now() - timedelta(hours=3)
        )

        second = record_view(anonymous_request, test_published_post, dedup_hours=1)

        assert second is True


@pytest.mark.django_db
class TestRecordViewAuthenticated:
    def test_authenticated_view_creates_row_with_user(
        self, authed_request, test_published_post, test_user
    ):
        record_view(authed_request, test_published_post)

        view = PostView.objects.get(post=test_published_post)
        assert view.user == test_user

    def test_authenticated_dedup_is_per_user(
        self, authed_request, test_published_post, test_user
    ):
        record_view(authed_request, test_published_post)
        second = record_view(authed_request, test_published_post)

        assert second is False
        assert PostView.objects.filter(post=test_published_post).count() == 1

    def test_two_different_users_both_count(
        self,
        request_factory,
        test_published_post,
        test_user,
        test_other_author,
    ):
        req1 = request_factory.get("/")
        req1.user = test_user
        req1.META["REMOTE_ADDR"] = "10.0.0.1"
        req1.META["HTTP_USER_AGENT"] = "ua1"

        req2 = request_factory.get("/")
        req2.user = test_other_author
        req2.META["REMOTE_ADDR"] = "10.0.0.2"
        req2.META["HTTP_USER_AGENT"] = "ua2"

        first = record_view(req1, test_published_post)
        second = record_view(req2, test_published_post)

        assert first is True
        assert second is True
        assert PostView.objects.filter(post=test_published_post).count() == 2

    def test_anonymous_view_does_not_dedup_against_authenticated_view(
        self,
        anonymous_request,
        authed_request,
        test_published_post,
    ):
        # Authed view first.
        record_view(authed_request, test_published_post)

        # Anonymous view from same IP.
        second = record_view(anonymous_request, test_published_post)

        # Current behavior: anonymous request uses the ip+ua branch
        # because there is no user and no session key. It does not
        # match the authed row (which has user set, ip+ua null-ish).
        assert second is True


@pytest.mark.django_db
class TestRecordViewMultiplePosts:
    def test_dedup_is_per_post(
        self, anonymous_request, test_published_post, test_second_published_post
    ):
        first = record_view(anonymous_request, test_published_post)
        second = record_view(anonymous_request, test_second_published_post)

        assert first is True
        assert second is True
        assert PostView.objects.filter(post=test_published_post).count() == 1
        assert PostView.objects.filter(post=test_second_published_post).count() == 1


@pytest.mark.django_db
class TestRecordViewReturnsBool:
    def test_returns_true_on_new_view(self, anonymous_request, test_published_post):
        assert record_view(anonymous_request, test_published_post) is True

    def test_returns_false_on_deduplicated_view(
        self, anonymous_request, test_published_post
    ):
        record_view(anonymous_request, test_published_post)
        assert record_view(anonymous_request, test_published_post) is False


# ==================================================================
# get_similar_posts
# ==================================================================
@pytest.mark.django_db
class TestGetSimilarPostsByTag:
    def test_returns_posts_sharing_at_least_one_tag(
        self,
        test_published_post,
        test_post_with_tags,
        test_tag,
    ):
        test_published_post.tags.set([test_tag])
        test_published_post.save()

        result = list(get_similar_posts(test_published_post, limit=4))

        assert test_post_with_tags in result
        assert test_published_post not in result

    def test_excludes_the_source_post(
        self, test_published_post, test_post_with_tags, test_tag
    ):
        test_published_post.tags.set([test_tag])
        test_published_post.save()

        result = list(get_similar_posts(test_published_post, limit=4))

        assert test_published_post not in result

    def test_ranks_posts_with_more_shared_tags_first(
        self,
        test_author,
        test_category,
        test_published_post,
        test_tag,
        test_second_tag,
    ):
        # Source has both tags.
        test_published_post.tags.set([test_tag, test_second_tag])
        test_published_post.save()

        # A post with both tags.
        both = Post.objects.create(
            author=test_author,
            title="Shares Both",
            body="<p>B.</p>",
            category=test_category,
            status=Post.Status.PUBLISHED,
            published_at=timezone.now() - timedelta(hours=1),
        )
        both.tags.set([test_tag, test_second_tag])

        # A post with only one tag.
        one = Post.objects.create(
            author=test_author,
            title="Shares One",
            body="<p>B.</p>",
            category=test_category,
            status=Post.Status.PUBLISHED,
            published_at=timezone.now() - timedelta(hours=1),
        )
        one.tags.set([test_tag])

        result = list(get_similar_posts(test_published_post, limit=4))

        assert result.index(both) < result.index(one)

    def test_excludes_drafts(self, test_published_post, test_draft_post, test_tag):
        test_published_post.tags.set([test_tag])
        test_published_post.save()
        test_draft_post.tags.set([test_tag])
        test_draft_post.save()

        result = list(get_similar_posts(test_published_post, limit=4))

        assert test_draft_post not in result

    def test_respects_limit(
        self, test_author, test_category, test_published_post, test_tag
    ):
        test_published_post.tags.set([test_tag])
        test_published_post.save()

        for i in range(6):
            p = Post.objects.create(
                author=test_author,
                title=f"Extra {i}",
                body="<p>B.</p>",
                category=test_category,
                status=Post.Status.PUBLISHED,
                published_at=timezone.now() - timedelta(hours=i + 1),
            )
            p.tags.set([test_tag])

        result = list(get_similar_posts(test_published_post, limit=2))

        assert len(result) == 2


@pytest.mark.django_db
class TestGetSimilarPostsFallback:
    def test_falls_back_to_category_when_no_tag_overlap(
        self,
        test_published_post,
        test_second_published_post,
        test_category,
    ):
        # Neither post has any tags set, but they share a category.
        assert test_published_post.category == test_category
        assert test_second_published_post.category == test_category

        result = list(get_similar_posts(test_published_post, limit=4))

        assert test_second_published_post in result

    def test_returns_empty_when_no_tags_and_no_category(
        self, test_author, test_published_post
    ):
        test_published_post.category = None
        test_published_post.save(update_fields=["category"])

        result = list(get_similar_posts(test_published_post, limit=4))

        assert result == []

    def test_respects_limit_in_fallback(
        self, test_author, test_category, test_published_post
    ):
        # Source has no tags but shares a category with several posts.
        for i in range(5):
            Post.objects.create(
                author=test_author,
                title=f"Fallback {i}",
                body="<p>B.</p>",
                category=test_category,
                status=Post.Status.PUBLISHED,
                published_at=timezone.now() - timedelta(hours=i + 1),
            )

        result = list(get_similar_posts(test_published_post, limit=2))

        assert len(result) == 2


# ==================================================================
# get_author_other_posts
# ==================================================================
@pytest.mark.django_db
class TestGetAuthorOtherPosts:
    def test_returns_only_same_authors_published_posts(
        self,
        test_published_post,
        test_second_published_post,
        test_other_authors_post,
    ):
        result = list(get_author_other_posts(test_published_post, limit=3))

        assert test_second_published_post in result
        assert test_other_authors_post not in result

    def test_excludes_the_source_post(
        self, test_published_post, test_second_published_post
    ):
        result = list(get_author_other_posts(test_published_post, limit=3))

        assert test_published_post not in result

    def test_excludes_drafts(self, test_published_post, test_draft_post):
        result = list(get_author_other_posts(test_published_post, limit=3))

        assert test_draft_post not in result

    def test_orders_by_published_at_desc(
        self, test_published_post, test_second_published_post
    ):
        result = list(get_author_other_posts(test_published_post, limit=3))

        # test_second_published_post is newer.
        assert result[0] == test_second_published_post

    def test_respects_limit(self, test_author, test_category, test_published_post):
        for i in range(5):
            Post.objects.create(
                author=test_author,
                title=f"Extra {i}",
                body="<p>B.</p>",
                category=test_category,
                status=Post.Status.PUBLISHED,
                published_at=timezone.now() - timedelta(hours=i + 1),
            )

        result = list(get_author_other_posts(test_published_post, limit=2))

        assert len(result) == 2

    def test_returns_empty_when_author_has_no_other_posts(self, test_published_post):
        result = list(get_author_other_posts(test_published_post, limit=3))

        assert result == []
