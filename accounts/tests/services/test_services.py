"""
Behavioral tests for accounts.api.services.get_author_stats.

Every test exercises the real aggregate query against real Post,
Comment, Like, and Bookmark rows. No mocking of the database.
"""

import pytest

from accounts.api.services import get_author_stats


@pytest.mark.django_db
class TestGetAuthorStatsEmpty:
    def test_author_with_no_posts_returns_zero_totals(self, test_author):
        stats = get_author_stats(test_author)

        assert stats == {
            "total_posts": 0,
            "total_views": 0,
            "total_likes": 0,
            "total_comments": 0,
            "total_bookmarks": 0,
        }

    def test_only_drafts_returns_zero_published_posts(
        self, test_author, test_draft_post
    ):
        stats = get_author_stats(test_author)

        assert stats["total_posts"] == 0


@pytest.mark.django_db
class TestGetAuthorStatsPublishedFiltering:
    def test_counts_published_posts(self, test_author, test_published_post):
        stats = get_author_stats(test_author)
        assert stats["total_posts"] == 1

    def test_counts_multiple_published_posts(
        self, test_author, test_published_post, test_second_published_post
    ):
        stats = get_author_stats(test_author)
        assert stats["total_posts"] == 2

    def test_excludes_drafts(self, test_author, test_published_post, test_draft_post):
        stats = get_author_stats(test_author)
        assert stats["total_posts"] == 1

    def test_excludes_future_scheduled_posts(
        self, test_author, test_published_post, test_scheduled_future_post
    ):
        stats = get_author_stats(test_author)
        assert stats["total_posts"] == 1

    def test_excludes_soft_deleted_posts(
        self, test_author, test_published_post, test_soft_deleted_post
    ):
        stats = get_author_stats(test_author)
        assert stats["total_posts"] == 1

    def test_excludes_other_authors_posts(
        self, test_author, test_published_post, test_other_authors_post
    ):
        stats = get_author_stats(test_author)
        assert stats["total_posts"] == 1


@pytest.mark.django_db
class TestGetAuthorStatsViews:
    def test_sums_views_count_across_published_posts(
        self, test_author, test_published_post, test_second_published_post
    ):
        test_published_post.views_count = 10
        test_published_post.save(update_fields=["views_count"])
        test_second_published_post.views_count = 5
        test_second_published_post.save(update_fields=["views_count"])

        stats = get_author_stats(test_author)
        assert stats["total_views"] == 15

    def test_views_are_zero_when_no_posts_have_views(
        self, test_author, test_published_post
    ):
        stats = get_author_stats(test_author)
        assert stats["total_views"] == 0


@pytest.mark.django_db
class TestGetAuthorStatsLikes:
    def test_counts_likes_across_published_posts(
        self, test_author, test_published_post, test_like
    ):
        stats = get_author_stats(test_author)
        assert stats["total_likes"] == 1

    def test_likes_on_other_authors_posts_are_excluded(
        self, test_author, test_published_post, test_other_authors_post, test_user
    ):
        from interactions.models import Like

        Like.objects.create(user=test_user, post=test_other_authors_post)

        stats = get_author_stats(test_author)
        assert stats["total_likes"] == 0


@pytest.mark.django_db
class TestGetAuthorStatsComments:
    def test_counts_only_approved_non_deleted_comments(
        self,
        test_author,
        test_published_post,
        test_approved_comment,
        test_pending_comment,
        test_soft_deleted_comment,
    ):
        stats = get_author_stats(test_author)
        assert stats["total_comments"] == 1

    def test_approved_comment_is_counted(
        self, test_author, test_published_post, test_approved_comment
    ):
        stats = get_author_stats(test_author)
        assert stats["total_comments"] == 1

    def test_pending_comment_is_not_counted(
        self, test_author, test_published_post, test_pending_comment
    ):
        stats = get_author_stats(test_author)
        assert stats["total_comments"] == 0

    def test_soft_deleted_comment_is_not_counted(
        self, test_author, test_published_post, test_soft_deleted_comment
    ):
        stats = get_author_stats(test_author)
        assert stats["total_comments"] == 0


@pytest.mark.django_db
class TestGetAuthorStatsBookmarks:
    def test_counts_bookmarks_on_published_posts(
        self, test_author, test_published_post, test_bookmark
    ):
        stats = get_author_stats(test_author)
        assert stats["total_bookmarks"] == 1

    def test_bookmarks_on_other_authors_posts_are_excluded(
        self,
        test_author,
        test_published_post,
        test_other_authors_post,
        test_user,
    ):
        from interactions.models import Bookmark

        Bookmark.objects.create(user=test_user, post=test_other_authors_post)

        stats = get_author_stats(test_author)
        assert stats["total_bookmarks"] == 0
