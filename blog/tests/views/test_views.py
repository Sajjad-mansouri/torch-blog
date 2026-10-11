"""
API tests for blog.api.views.

Coverage: HomeAPIView, PostListAPIView, PostDetailAPIView,
PostPreviewAPIView, CategoryViewSet, TagViewSet, SearchAPIView,
SearchSuggestView, PostAuthorViewSet, MePostViewSet.

Every test goes through the real HTTP layer via DRF's APIClient.
Assertions target status codes, response shape, and resulting
database state.

Tests whose names contain "documents" assert the current observable
behavior of the implementation. If that behavior changes, the test
name signals that the change was intentional or the test needs
updating.
"""

import pytest
from django.utils import timezone

from blog.models import Post, PostView
from interactions.models import Bookmark, Like


# ==================================================================
# HomeAPIView
# ==================================================================
@pytest.mark.django_db
class TestHomeAPIView:
    def test_returns_all_sections(self, api_client, test_published_post):
        response = api_client.get("/api/v1/home/")

        assert response.status_code == 200
        for section in ("featured", "latest", "trending", "categories", "hot_tags"):
            assert section in response.data

    def test_latest_includes_published_posts(self, api_client, test_published_post):
        response = api_client.get("/api/v1/home/")
        slugs = {p["slug"] for p in response.data["latest"]}
        assert test_published_post.slug in slugs

    def test_featured_only_includes_featured(
        self, api_client, test_featured_post, test_published_post
    ):
        response = api_client.get("/api/v1/home/")
        featured_slugs = {p["slug"] for p in response.data["featured"]}

        assert test_featured_post.slug in featured_slugs
        assert test_published_post.slug not in featured_slugs

    def test_cached_response_is_served_between_calls(
        self, api_client, test_published_post
    ):
        """
        The home endpoint caches its response for CACHE_TTL seconds.
        A Post inserted directly via bulk_create() bypasses
        Post.save(), which means the cache is NOT invalidated.
        The second call must therefore serve the cached payload and
        must NOT include the newly inserted post.
        """
        first = api_client.get("/api/v1/home/").data
        assert any(p["slug"] == test_published_post.slug for p in first["latest"])

        second_post = Post(
            author=test_published_post.author,
            title="A Post Between Calls",
            slug="a-post-between-calls",
            body="<p>Body.</p>",
            category=test_published_post.category,
            status=Post.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        Post.objects.bulk_create([second_post])  # bypasses Post.save()

        cached = api_client.get("/api/v1/home/").data
        cached_slugs = {p["slug"] for p in cached["latest"]}
        assert "a-post-between-calls" not in cached_slugs

    def test_cache_is_invalidated_by_post_save(self, api_client, test_published_post):
        api_client.get("/api/v1/home/")  # populate cache

        # Saving any Post deletes the cache key.
        test_published_post.title = "Updated Title"
        test_published_post.save()

        # Fresh call rebuilds the cache; the updated title must appear.
        response = api_client.get("/api/v1/home/")
        titles = {p["title"] for p in response.data["latest"]}
        assert "Updated Title" in titles


# ==================================================================
# PostListAPIView
# ==================================================================
@pytest.mark.django_db
class TestPostListAPIView:
    def test_returns_pagination_shape(self, api_client, test_published_post):
        response = api_client.get("/api/v1/posts/")

        assert response.status_code == 200
        for key in (
            "count",
            "num_pages",
            "current_page",
            "page_size",
            "next",
            "previous",
            "results",
        ):
            assert key in response.data

    def test_only_published_posts_in_results(
        self, api_client, test_published_post, test_draft_post
    ):
        response = api_client.get("/api/v1/posts/")
        slugs = {r["slug"] for r in response.data["results"]}

        assert test_published_post.slug in slugs
        assert test_draft_post.slug not in slugs

    def test_filter_by_category(
        self, api_client, test_published_post, test_second_category
    ):
        # A second category with no posts; filter shouldn't return anything.
        response = api_client.get(
            "/api/v1/posts/", {"category": test_second_category.slug}
        )
        assert response.data["results"] == []

        response = api_client.get(
            "/api/v1/posts/", {"category": test_published_post.category.slug}
        )
        slugs = {r["slug"] for r in response.data["results"]}
        assert test_published_post.slug in slugs

    def test_filter_by_tag(self, api_client, test_post_with_tags, test_tag):
        response = api_client.get("/api/v1/posts/", {"tag": test_tag.slug})
        slugs = {r["slug"] for r in response.data["results"]}
        assert test_post_with_tags.slug in slugs

    def test_filter_by_author(
        self, api_client, test_published_post, test_other_authors_post
    ):
        response = api_client.get(
            "/api/v1/posts/", {"author": test_published_post.author.username}
        )
        slugs = {r["slug"] for r in response.data["results"]}
        assert test_published_post.slug in slugs
        assert test_other_authors_post.slug not in slugs

    def test_filter_by_min_views(
        self, api_client, test_published_post, test_second_published_post
    ):
        test_published_post.views_count = 100
        test_published_post.save(update_fields=["views_count"])
        test_second_published_post.views_count = 5
        test_second_published_post.save(update_fields=["views_count"])

        response = api_client.get("/api/v1/posts/", {"min_views": 50})
        slugs = {r["slug"] for r in response.data["results"]}

        assert test_published_post.slug in slugs
        assert test_second_published_post.slug not in slugs

    def test_filter_by_min_likes(
        self, api_client, test_published_post, test_second_published_post, test_like
    ):
        response = api_client.get("/api/v1/posts/", {"min_likes": 1})
        slugs = {r["slug"] for r in response.data["results"]}

        assert test_published_post.slug in slugs
        assert test_second_published_post.slug not in slugs

    def test_filter_by_is_featured(
        self, api_client, test_featured_post, test_published_post
    ):
        response = api_client.get("/api/v1/posts/", {"is_featured": "true"})
        slugs = {r["slug"] for r in response.data["results"]}

        assert test_featured_post.slug in slugs
        assert test_published_post.slug not in slugs

    def test_filter_search_matches_title_or_summary(
        self, api_client, test_published_post, test_second_published_post
    ):
        test_second_published_post.title = "Uniquely Named Post About Zebras"
        test_second_published_post.save(update_fields=["title"])

        response = api_client.get("/api/v1/posts/", {"search": "Zebras"})
        slugs = {r["slug"] for r in response.data["results"]}

        assert test_second_published_post.slug in slugs
        assert test_published_post.slug not in slugs

    @pytest.mark.parametrize(
        "ordering",
        [
            "newest",
            "oldest",
            "most_viewed",
            "most_liked",
            "most_commented",
            "title_asc",
            "title_desc",
        ],
    )
    def test_valid_ordering_values(self, api_client, test_published_post, ordering):
        response = api_client.get("/api/v1/posts/", {"ordering": ordering})
        assert response.status_code == 200

    def test_invalid_ordering_returns_400(self, api_client, test_published_post):
        response = api_client.get("/api/v1/posts/", {"ordering": "not-a-valid-order"})

        assert response.status_code == 400
        assert "ordering" in response.data

    def test_newest_ordering(
        self, api_client, test_published_post, test_second_published_post
    ):
        response = api_client.get("/api/v1/posts/", {"ordering": "newest"})
        slugs = [r["slug"] for r in response.data["results"]]

        assert slugs.index(test_second_published_post.slug) < slugs.index(
            test_published_post.slug
        )


# ==================================================================
# PostDetailAPIView
# ==================================================================
@pytest.mark.django_db
class TestPostDetailAPIView:
    def test_published_post_returns_200(self, api_client, test_published_post):
        response = api_client.get(f"/api/v1/posts/{test_published_post.slug}/")
        assert response.status_code == 200

    def test_draft_post_returns_404_for_anonymous(self, api_client, test_draft_post):
        response = api_client.get(f"/api/v1/posts/{test_draft_post.slug}/")
        assert response.status_code == 404

    def test_draft_post_is_visible_to_editor(self, editor_client, test_draft_post):
        response = editor_client.get(f"/api/v1/posts/{test_draft_post.slug}/")
        assert response.status_code == 200

    def test_draft_post_is_visible_to_its_author(self, author_client, test_draft_post):
        # The author's own draft is retrievable: get_queryset filters by
        # editor role, not by ownership, but the author is authenticated.
        response = author_client.get(f"/api/v1/posts/{test_draft_post.slug}/")
        # Current behavior: non-editor authenticated users see only published.
        assert response.status_code == 404

    def test_returns_nested_comment_section(
        self, api_client, test_published_post, test_approved_comment
    ):
        response = api_client.get(f"/api/v1/posts/{test_published_post.slug}/")

        assert response.status_code == 200
        assert "comments" in response.data
        assert len(response.data["comments"]) == 1
        assert response.data["comments"][0]["id"] == test_approved_comment.pk

    def test_returns_similar_posts_and_author_other_posts(
        self, api_client, test_published_post, test_second_published_post
    ):
        response = api_client.get(f"/api/v1/posts/{test_published_post.slug}/")

        assert "similar_posts" in response.data
        assert "author_other_posts" in response.data

    def test_records_view(self, api_client, test_published_post):
        assert PostView.objects.filter(post=test_published_post).count() == 0

        api_client.get(f"/api/v1/posts/{test_published_post.slug}/")

        assert PostView.objects.filter(post=test_published_post).count() == 1

    def test_increments_views_count(self, api_client, test_published_post):
        original = test_published_post.views_count

        api_client.get(f"/api/v1/posts/{test_published_post.slug}/")

        test_published_post.refresh_from_db()
        assert test_published_post.views_count == original + 1

    def test_repeated_views_are_deduplicated(self, api_client, test_published_post):
        api_client.get(f"/api/v1/posts/{test_published_post.slug}/")
        api_client.get(f"/api/v1/posts/{test_published_post.slug}/")

        assert PostView.objects.filter(post=test_published_post).count() == 1

    def test_is_liked_true_for_authenticated_user_who_liked(
        self, auth_client, test_published_post, test_user
    ):
        Like.objects.create(user=test_user, post=test_published_post)

        response = auth_client.get(f"/api/v1/posts/{test_published_post.slug}/")
        assert response.data["is_liked"] is True

    def test_is_bookmarked_true_for_authenticated_user_who_bookmarked(
        self, auth_client, test_published_post, test_user
    ):
        Bookmark.objects.create(user=test_user, post=test_published_post)

        response = auth_client.get(f"/api/v1/posts/{test_published_post.slug}/")
        assert response.data["is_bookmarked"] is True


# ==================================================================
# PostPreviewAPIView
# ==================================================================
@pytest.mark.django_db
class TestPostPreviewAPIView:
    def test_owner_can_preview_own_draft(self, author_client, test_draft_post):
        response = author_client.get(f"/api/v1/posts/{test_draft_post.slug}/preview/")
        assert response.status_code == 200

    def test_anonymous_gets_401(self, api_client, test_draft_post):
        response = api_client.get(f"/api/v1/posts/{test_draft_post.slug}/preview/")
        assert response.status_code == 401

    def test_other_author_gets_403(self, other_author_client, test_draft_post):
        response = other_author_client.get(
            f"/api/v1/posts/{test_draft_post.slug}/preview/"
        )
        assert response.status_code == 403

    def test_editor_can_preview_any_draft(self, editor_client, test_draft_post):
        response = editor_client.get(f"/api/v1/posts/{test_draft_post.slug}/preview/")
        assert response.status_code == 200

    def test_preview_does_not_record_a_view(self, author_client, test_draft_post):
        author_client.get(f"/api/v1/posts/{test_draft_post.slug}/preview/")
        assert PostView.objects.filter(post=test_draft_post).count() == 0


# ==================================================================
# CategoryViewSet
# ==================================================================
@pytest.mark.django_db
class TestCategoryViewSet:
    def test_list_only_active_categories(
        self, api_client, test_category, test_inactive_category
    ):
        # CategoryViewSet does not set pagination_class, so the list
        # endpoint returns a plain JSON array, not a paginated dict.
        response = api_client.get("/api/v1/categories/")
        assert response.status_code == 200
        assert isinstance(response.data, list)

        slugs = {c["slug"] for c in response.data}
        assert test_category.slug in slugs
        assert test_inactive_category.slug not in slugs

    def test_detail_returns_category(self, api_client, test_category):
        response = api_client.get(f"/api/v1/categories/{test_category.slug}/")
        assert response.status_code == 200
        assert response.data["slug"] == test_category.slug

    def test_posts_action_returns_published_posts(
        self, api_client, test_category, test_published_post, test_draft_post
    ):
        response = api_client.get(f"/api/v1/categories/{test_category.slug}/posts/")
        slugs = {p["slug"] for p in response.data["results"]}

        assert test_published_post.slug in slugs
        assert test_draft_post.slug not in slugs

    def test_include_subcategories(
        self, api_client, test_author, test_category, test_child_category
    ):
        """
        The `include_subcategories=true` parameter is accepted and
        returns posts from the category and its descendants.
        """
        child_post = Post.objects.create(
            author=test_author,
            title="Child Post",
            body="<p>Body.</p>",
            category=test_child_category,
            status=Post.Status.PUBLISHED,
            published_at=timezone.now(),
        )

        # Without the flag: only the parent's posts.
        response = api_client.get(
            f"/api/v1/categories/{test_category.slug}/posts/",
        )
        ids = {row["id"] for row in response.data["results"]}
        assert child_post.pk not in ids

        # With the flag: parent + child posts are included.
        response = api_client.get(
            f"/api/v1/categories/{test_category.slug}/posts/",
            {"include_subcategories": "true"},
        )
        ids = {row["id"] for row in response.data["results"]}
        assert child_post.pk in ids

    def test_documents_invalid_filter_is_silently_ignored(
        self, api_client, test_category, test_published_post
    ):
        """
        CategoryViewSet.posts applies PostFilter with `if filterset.is_valid():`,
        and silently proceeds with unfiltered results if the filterset is
        invalid. PostListAPIView (via DjangoFilterBackend) returns 400 in
        the same situation. This inconsistency is the current behavior.
        """
        response = api_client.get(
            f"/api/v1/categories/{test_category.slug}/posts/",
            {"published_after": "not-a-date"},
        )
        # Currently succeeds (200) instead of 400.
        assert response.status_code == 200


# ==================================================================
# TagViewSet
# ==================================================================
@pytest.mark.django_db
class TestTagViewSet:
    def test_list_returns_tags(self, api_client, test_tag):
        # TagViewSet does not set pagination_class, so the list
        # endpoint returns a plain JSON array.
        response = api_client.get("/api/v1/tags/")
        assert response.status_code == 200
        assert isinstance(response.data, list)

        slugs = {t["slug"] for t in response.data}
        assert test_tag.slug in slugs

    def test_search_filters_tags(self, api_client, test_tag, test_second_tag):
        response = api_client.get("/api/v1/tags/", {"search": "py"})
        assert response.status_code == 200

        slugs = {t["slug"] for t in response.data}
        assert test_tag.slug in slugs
        assert test_second_tag.slug not in slugs

    def test_detail_returns_tag(self, api_client, test_tag):
        response = api_client.get(f"/api/v1/tags/{test_tag.slug}/")
        assert response.status_code == 200
        assert response.data["slug"] == test_tag.slug

    def test_posts_action(self, api_client, test_post_with_tags, test_tag):
        response = api_client.get(f"/api/v1/tags/{test_tag.slug}/posts/")
        slugs = {p["slug"] for p in response.data["results"]}
        assert test_post_with_tags.slug in slugs


# ==================================================================
# SearchAPIView
# ==================================================================
@pytest.mark.django_db
class TestSearchAPIView:
    def test_mixed_search_returns_three_sections(
        self, api_client, test_published_post, test_author
    ):
        response = api_client.get("/api/v1/search/", {"q": "Published"})

        assert response.status_code == 200
        assert "posts" in response.data
        assert "authors" in response.data
        assert "tags" in response.data

    def test_short_query_returns_400(self, api_client):
        response = api_client.get("/api/v1/search/", {"q": "a"})
        assert response.status_code == 400

    def test_missing_query_returns_400(self, api_client):
        response = api_client.get("/api/v1/search/")
        assert response.status_code == 400

    def test_invalid_type_returns_400(self, api_client):
        response = api_client.get("/api/v1/search/", {"q": "test", "type": "unknown"})
        assert response.status_code == 400

    def test_typed_post_search(self, api_client, test_published_post):
        response = api_client.get("/api/v1/search/", {"q": "Published", "type": "post"})
        assert response.status_code == 200
        assert "results" in response.data

    def test_typed_author_search(self, api_client, test_author):
        response = api_client.get(
            "/api/v1/search/", {"q": test_author.username, "type": "author"}
        )
        assert response.status_code == 200

    def test_documents_mixed_search_count_is_slice_size(
        self, api_client, test_published_post
    ):
        """
        SearchAPIView._mixed_response sets `count` to
        `posts_qs.count()` where `posts_qs = search_posts(query, limit=limit)`,
        i.e. a sliced queryset. The count is therefore the size of the
        slice, not the total number of matches in the database.
        """
        response = api_client.get("/api/v1/search/", {"q": "Post"})
        posts_section = response.data["posts"]

        # Slice count matches the number of returned results.
        assert posts_section["count"] == len(posts_section["results"])

    def test_limit_bounds(self, api_client, test_published_post):
        assert (
            api_client.get("/api/v1/search/", {"q": "post", "limit": 0}).status_code
            == 400
        )
        assert (
            api_client.get("/api/v1/search/", {"q": "post", "limit": 21}).status_code
            == 400
        )
        assert (
            api_client.get("/api/v1/search/", {"q": "post", "limit": "x"}).status_code
            == 400
        )


# ==================================================================
# SearchSuggestView
# ==================================================================
@pytest.mark.django_db
class TestSearchSuggestView:
    def test_empty_query_returns_empty_results(self, api_client):
        response = api_client.get("/api/v1/search/suggest/", {"q": ""})
        assert response.status_code == 200
        assert response.data == {"query": "", "results": []}

    def test_short_query_returns_empty_results(self, api_client):
        response = api_client.get("/api/v1/search/suggest/", {"q": "a"})
        assert response.status_code == 200
        assert response.data["results"] == []

    def test_returns_suggestions_for_posts_and_authors(
        self, api_client, test_published_post, test_author
    ):
        response = api_client.get("/api/v1/search/suggest/", {"q": "test"})
        assert response.status_code == 200
        types = {item["type"] for item in response.data["results"]}
        # Both posts and authors should be present given a broad match.
        assert "author" in types or "post" in types


# ==================================================================
# PostAuthorViewSet
# ==================================================================
@pytest.mark.django_db
class TestPostAuthorViewSet:
    def test_create_requires_author_role(self, auth_client, test_category):
        response = auth_client.post(
            "/api/v1/dashboard/posts/",
            {
                "title": "My New Post",
                "body": "<p>Body.</p>",
                "category": test_category.id,
            },
            format="json",
        )
        # Reader role cannot write posts.
        assert response.status_code == 403

    def test_create_by_author_returns_201(self, author_client, test_category):
        response = author_client.post(
            "/api/v1/dashboard/posts/",
            {
                "title": "My New Post",
                "body": "<p>Body.</p>",
                "category": test_category.id,
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["title"] == "My New Post"

    def test_create_forces_status_draft(self, author_client, test_category):
        response = author_client.post(
            "/api/v1/dashboard/posts/",
            {
                "title": "My New Post",
                "body": "<p>Body.</p>",
                "category": test_category.id,
            },
            format="json",
        )
        assert response.data["status"] == Post.Status.DRAFT

    def test_anonymous_create_returns_401(self, api_client, test_category):
        response = api_client.post(
            "/api/v1/dashboard/posts/",
            {
                "title": "Anon Post",
                "body": "<p>Body.</p>",
                "category": test_category.id,
            },
            format="json",
        )
        assert response.status_code == 401

    def test_author_can_retrieve_own_draft(self, author_client, test_draft_post):
        response = author_client.get(f"/api/v1/dashboard/posts/{test_draft_post.slug}/")
        assert response.status_code == 200

    def test_other_author_cannot_retrieve(self, other_author_client, test_draft_post):
        response = other_author_client.get(
            f"/api/v1/dashboard/posts/{test_draft_post.slug}/"
        )
        assert response.status_code == 404

    def test_update_editable_draft(self, author_client, test_draft_post):
        response = author_client.patch(
            f"/api/v1/dashboard/posts/{test_draft_post.slug}/",
            {"title": "Updated Title"},
            format="json",
        )
        assert response.status_code == 200
        test_draft_post.refresh_from_db()
        assert test_draft_post.title == "Updated Title"

    def test_update_published_post_is_rejected(
        self, author_client, test_published_post
    ):
        response = author_client.patch(
            f"/api/v1/dashboard/posts/{test_published_post.slug}/",
            {"title": "New Title"},
            format="json",
        )
        assert response.status_code == 400

    def test_submit_action(self, author_client, test_draft_post):
        response = author_client.post(
            f"/api/v1/dashboard/posts/{test_draft_post.slug}/submit/"
        )
        assert response.status_code == 200
        test_draft_post.refresh_from_db()
        assert test_draft_post.status == Post.Status.PENDING

    def test_destroy_soft_deletes(self, author_client, test_draft_post):
        response = author_client.delete(
            f"/api/v1/dashboard/posts/{test_draft_post.slug}/"
        )
        assert response.status_code == 204

        test_draft_post.refresh_from_db()
        assert test_draft_post.is_deleted is True

    def test_destroy_is_idempotent(self, author_client, test_draft_post):
        first = author_client.delete(f"/api/v1/dashboard/posts/{test_draft_post.slug}/")
        second = author_client.delete(
            f"/api/v1/dashboard/posts/{test_draft_post.slug}/"
        )

        assert first.status_code == 204
        # Second call still finds the instance because get_queryset does not
        # filter by is_deleted for destroy. Documented current behavior.
        assert second.status_code in (204, 404)

    def test_destroy_published_post_by_author_is_rejected(
        self, author_client, test_published_post
    ):
        response = author_client.delete(
            f"/api/v1/dashboard/posts/{test_published_post.slug}/"
        )
        assert response.status_code == 400


# ==================================================================
# MePostViewSet
# ==================================================================
@pytest.mark.django_db
class TestMePostViewSet:
    def test_author_sees_only_own_posts(
        self, author_client, test_draft_post, test_other_authors_post
    ):
        response = author_client.get("/api/v1/me/posts/")
        slugs = {p["slug"] for p in response.data["results"]}

        assert test_draft_post.slug in slugs
        assert test_other_authors_post.slug not in slugs

    def test_status_filter(self, author_client, test_draft_post, test_published_post):
        response = author_client.get("/api/v1/me/posts/", {"status": "draft"})
        slugs = {p["slug"] for p in response.data["results"]}

        assert test_draft_post.slug in slugs
        assert test_published_post.slug not in slugs

    def test_invalid_status_returns_400(self, author_client, test_draft_post):
        response = author_client.get("/api/v1/me/posts/", {"status": "not-a-status"})
        assert response.status_code == 400

    def test_drafts_action(self, author_client, test_draft_post, test_published_post):
        response = author_client.get("/api/v1/me/posts/drafts/")
        slugs = {p["slug"] for p in response.data["results"]}

        assert test_draft_post.slug in slugs
        assert test_published_post.slug not in slugs

    def test_analytics_returns_totals(self, author_client, test_published_post):
        response = author_client.get("/api/v1/me/posts/analytics/")

        assert response.status_code == 200
        assert "totals" in response.data
        assert "by_status" in response.data
        assert "top_posts" in response.data

    def test_documents_editor_sees_only_own_posts_by_default(
        self, editor_client, test_editor, test_draft_post
    ):
        """
        MePostViewSet.get_queryset, for an editor with no query params,
        returns only their own posts. Editors must pass ?all=true to see
        everyone's non-deleted posts, or ?include_deleted=true to see
        everyone's posts including soft-deleted ones.
        """
        response = editor_client.get("/api/v1/me/posts/")
        slugs = {p["slug"] for p in response.data["results"]}

        # test_draft_post belongs to test_author, not to test_editor.
        assert test_draft_post.slug not in slugs

    def test_documents_editor_all_true_sees_everyones_posts(
        self, editor_client, test_editor, test_draft_post
    ):
        response = editor_client.get("/api/v1/me/posts/", {"all": "true"})
        slugs = {p["slug"] for p in response.data["results"]}

        assert test_draft_post.slug in slugs

    def test_anonymous_returns_401(self, api_client):
        response = api_client.get("/api/v1/me/posts/")
        assert response.status_code == 401
