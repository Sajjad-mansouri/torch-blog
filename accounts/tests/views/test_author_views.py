"""
API tests for accounts.api.views.AuthorViewSet.

Registered in blog/api/urls.py as:
    router.register("authors", AuthorViewSet, basename="author")

Route names (no namespace, because config/urls.py includes
blog.api.urls without namespace=):
    author-list    -> GET /api/v1/authors/
    author-detail  -> GET /api/v1/authors/<username>/
    author-posts   -> GET /api/v1/authors/<username>/posts/
"""

import pytest
from rest_framework import status


# ==================================================================
# List — GET /api/v1/authors/
# ==================================================================
@pytest.mark.django_db
class TestAuthorList:
    def test_lists_only_authors_and_editors(
        self, api_client, test_user, test_author, test_editor
    ):
        response = api_client.get("/api/v1/authors/")

        assert response.status_code == status.HTTP_200_OK
        usernames = {row["username"] for row in response.data["results"]}
        assert test_author.username in usernames
        assert test_editor.username in usernames
        assert test_user.username not in usernames

    def test_anonymous_access_allowed(self, api_client, test_author):
        response = api_client.get("/api/v1/authors/")
        assert response.status_code == status.HTTP_200_OK

    def test_uses_brief_serializer(self, api_client, test_author):
        response = api_client.get("/api/v1/authors/")
        row = response.data["results"][0]

        # Brief serializer fields
        assert "id" in row
        assert "username" in row
        assert "display_name" in row
        assert "avatar_url" in row
        # Detail-only fields are not present
        assert "bio" not in row
        assert "social_links" not in row

    def test_list_is_ordered_by_username(self, api_client, test_editor, test_author):
        response = api_client.get("/api/v1/authors/")
        usernames = [row["username"] for row in response.data["results"]]
        assert usernames == sorted(usernames)

    def test_pagination_is_stable_across_calls(
        self, api_client, test_author, test_editor
    ):
        first = api_client.get("/api/v1/authors/").data["results"]
        second = api_client.get("/api/v1/authors/").data["results"]
        assert [r["id"] for r in first] == [r["id"] for r in second]


# ==================================================================
# Retrieve — GET /api/v1/authors/<username>/
# ==================================================================
@pytest.mark.django_db
class TestAuthorRetrieve:
    def test_returns_full_profile(self, api_client, test_author, test_published_post):
        response = api_client.get(f"/api/v1/authors/{test_author.username}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == test_author.username
        assert "bio" in response.data
        assert "social_links" in response.data
        assert "stats" in response.data
        assert "recent_posts" in response.data

    def test_stats_reflect_published_posts(
        self, api_client, test_author, test_published_post
    ):
        """
        Regression test for B1: get_stats used to read the wrong
        context key, so stats was always {}.
        """
        response = api_client.get(f"/api/v1/authors/{test_author.username}/")

        assert response.data["stats"]["total_posts"] == 1

    def test_recent_posts_include_only_published(
        self, api_client, test_author, test_published_post, test_draft_post
    ):
        response = api_client.get(f"/api/v1/authors/{test_author.username}/")

        slugs = [p["slug"] for p in response.data["recent_posts"]]
        assert test_published_post.slug in slugs
        assert test_draft_post.slug not in slugs

    def test_reader_username_returns_404(self, api_client, test_user):
        response = api_client.get(f"/api/v1/authors/{test_user.username}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unknown_username_returns_404(self, api_client):
        response = api_client.get("/api/v1/authors/does-not-exist/")
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================================================================
# Nested posts action — GET /api/v1/authors/<username>/posts/
# ==================================================================
@pytest.mark.django_db
class TestAuthorPostsAction:
    def test_returns_only_published_posts_by_that_author(
        self, api_client, test_author, test_published_post, test_draft_post
    ):
        response = api_client.get(f"/api/v1/authors/{test_author.username}/posts/")

        assert response.status_code == status.HTTP_200_OK
        slugs = {row["slug"] for row in response.data["results"]}
        assert test_published_post.slug in slugs
        assert test_draft_post.slug not in slugs

    def test_excludes_other_authors_posts(
        self, api_client, test_author, test_published_post, test_other_authors_post
    ):
        response = api_client.get(f"/api/v1/authors/{test_author.username}/posts/")

        slugs = {row["slug"] for row in response.data["results"]}
        assert test_other_authors_post.slug not in slugs

    def test_invalid_ordering_returns_400(self, api_client, test_author):
        response = api_client.get(
            f"/api/v1/authors/{test_author.username}/posts/",
            {"ordering": "not-a-valid-order"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "ordering" in response.data

    def test_valid_ordering_is_respected(
        self, api_client, test_author, test_published_post, test_second_published_post
    ):
        response = api_client.get(
            f"/api/v1/authors/{test_author.username}/posts/",
            {"ordering": "oldest"},
        )

        assert response.status_code == status.HTTP_200_OK
        slugs = [row["slug"] for row in response.data["results"]]
        # test_published_post is older than test_second_published_post.
        assert slugs.index(test_published_post.slug) < slugs.index(
            test_second_published_post.slug
        )
