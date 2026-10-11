"""
Behavioral tests for blog.api.service_search.

Covers:
- normalize_query — trim, collapse whitespace, length limits.
- search_posts — matches title, summary, body; only published posts.
- search_authors — matches username, first/last name, bio; only
  authors and editors; ordered by username.
- search_tags — matches by name; only tags with usage_count > 0;
  ordered by usage_count desc, name asc.
- The `limit` parameter truncates results.
"""

import pytest

from blog.api.service_search import (
    MAX_QUERY_LENGTH,
    normalize_query,
    search_authors,
    search_posts,
    search_tags,
)
from blog.models import Post, Tag


# ==================================================================
# normalize_query
# ==================================================================
class TestNormalizeQuery:
    def test_none_returns_none(self):
        assert normalize_query(None) is None

    def test_empty_string_returns_none(self):
        assert normalize_query("") is None

    def test_whitespace_only_returns_none(self):
        assert normalize_query("   \t\n  ") is None

    def test_too_short_returns_none(self):
        assert normalize_query("a") is None

    def test_minimum_length_passes(self):
        result = normalize_query("ab")
        assert result == "ab"

    def test_collapses_internal_whitespace(self):
        result = normalize_query("  hello   world  ")
        assert result == "hello world"

    def test_truncates_to_max_length(self):
        long = "x" * (MAX_QUERY_LENGTH + 50)
        result = normalize_query(long)
        assert len(result) == MAX_QUERY_LENGTH

    def test_strips_leading_and_trailing_whitespace(self):
        assert normalize_query("  spam  ") == "spam"


# ==================================================================
# search_posts
# ==================================================================
@pytest.mark.django_db
class TestSearchPosts:
    def test_matches_title(self, test_published_post):
        test_published_post.title = "Uniquely Named Post About Quokkas"
        test_published_post.save(update_fields=["title"])

        result = list(search_posts("Quokkas"))

        assert test_published_post in result

    def test_matches_summary(self, test_published_post):
        test_published_post.summary = "A summary mentioning Pangolins."
        test_published_post.save(update_fields=["summary"])

        result = list(search_posts("Pangolins"))

        assert test_published_post in result

    def test_matches_body(self, test_published_post):
        test_published_post.body = "<p>Body mentioning Narwhals.</p>"
        test_published_post.save(update_fields=["body"])

        result = list(search_posts("Narwhals"))

        assert test_published_post in result

    def test_excludes_drafts(self, test_draft_post):
        test_draft_post.title = "A Draft About Okapis"
        test_draft_post.save(update_fields=["title"])

        result = list(search_posts("Okapis"))

        assert test_draft_post not in result

    def test_excludes_soft_deleted(self, test_soft_deleted_post):
        test_soft_deleted_post.title = "A Deleted Post About Tapirs"
        test_soft_deleted_post.save(update_fields=["title"])

        result = list(search_posts("Tapirs"))

        assert test_soft_deleted_post not in result

    def test_case_insensitive(self, test_published_post):
        test_published_post.title = "A Post About Elephants"
        test_published_post.save(update_fields=["title"])

        assert test_published_post in list(search_posts("elephants"))
        assert test_published_post in list(search_posts("ELEPHANTS"))

    def test_no_match_returns_empty(self):
        assert list(search_posts("AStringThatCannotMatchAnything")) == []

    def test_limit_truncates_results(
        self, test_author, test_category, test_published_post
    ):
        # Give several posts a matching word.
        for i in range(5):
            Post.objects.create(
                author=test_author,
                title=f"UniqueWord Post {i}",
                body="<p>Body.</p>",
                category=test_category,
                status=Post.Status.PUBLISHED,
                published_at=test_published_post.published_at,
            )

        result = list(search_posts("UniqueWord", limit=2))

        assert len(result) == 2

    def test_results_have_card_annotations(self, test_published_post):
        result = search_posts(test_published_post.title).first()

        # The service uses `.for_card()`, so these annotations exist.
        assert hasattr(result, "like_count")
        assert hasattr(result, "comment_count")
        assert hasattr(result, "bookmark_count")


# ==================================================================
# search_authors
# ==================================================================
@pytest.mark.django_db
class TestSearchAuthors:
    def test_matches_username(self, test_author):
        result = list(search_authors("test_author"))
        assert test_author in result

    def test_matches_first_name(self, test_author):
        test_author.first_name = "Zebediah"
        test_author.save(update_fields=["first_name"])

        result = list(search_authors("Zebediah"))
        assert test_author in result

    def test_matches_last_name(self, test_author):
        test_author.last_name = "Quintilius"
        test_author.save(update_fields=["last_name"])

        result = list(search_authors("Quintilius"))
        assert test_author in result

    def test_matches_bio(self, test_author):
        test_author.bio = "Writes about Xylophones."
        test_author.save(update_fields=["bio"])

        result = list(search_authors("Xylophones"))
        assert test_author in result

    def test_excludes_readers(self, test_user):
        test_user.first_name = "Zebediah"
        test_user.save(update_fields=["first_name"])

        result = list(search_authors("Zebediah"))
        assert test_user not in result

    def test_ordered_by_username(self, test_author, test_editor):
        # Both are matches for the empty-ish query "e" — but use a
        # shared token so both appear. Fall back to searching on a
        # common substring in their usernames ("t").
        results = list(search_authors("test"))

        usernames = [u.username for u in results]
        assert usernames == sorted(usernames)

    def test_limit_truncates_results(self, test_author, test_other_author, test_editor):
        result = list(search_authors("test", limit=1))
        assert len(result) == 1


# ==================================================================
# search_tags
# ==================================================================
@pytest.mark.django_db
class TestSearchTags:
    def test_matches_by_name(self, test_tag):
        test_tag.usage_count = 1
        test_tag.save(update_fields=["usage_count"])

        result = list(search_tags(test_tag.name))

        assert test_tag in result

    def test_case_insensitive(self, test_tag):
        test_tag.usage_count = 1
        test_tag.save(update_fields=["usage_count"])

        assert test_tag in list(search_tags(test_tag.name.upper()))

    def test_excludes_tags_with_zero_usage(self, test_tag):
        # test_tag defaults to usage_count=0.
        result = list(search_tags(test_tag.name))
        assert test_tag not in result

    def test_ordered_by_usage_count_desc_then_name(self):
        # Three tags with distinct usage counts to check ordering.
        Tag.objects.create(name="high", usage_count=10)
        Tag.objects.create(name="low", usage_count=1)
        Tag.objects.create(name="zero", usage_count=0)

        # Use a query that matches all three by using a common prefix,
        # or just call without a limit and check relative order.
        results = list(search_tags(""))

        # "zero" is excluded. "high" before "low".
        names = [t.name for t in results]
        assert names.index("high") < names.index("low")
        assert "zero" not in names

    def test_limit_truncates(self):
        for i in range(5):
            Tag.objects.create(name=f"tag{i}", usage_count=i + 1)

        result = list(search_tags("tag", limit=2))
        assert len(result) == 2
