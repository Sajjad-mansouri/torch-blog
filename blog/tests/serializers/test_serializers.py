"""
Behavioral tests for blog.api.serializers.

Covers output shape, read-only enforcement, validation rules, and
context-dependent methods (allowed_actions, is_liked, is_bookmarked,
comments, replies). No serializer logic is mocked.

Where the current behavior is unusual or worth documenting, that
is called out in the test's name or docstring.
"""

import pytest

from blog.api.serializers import (
    CategoryBriefSerializer,
    CategoryParentSerializer,
    CategorySerializer,
    CommentAuthorSerializer,
    CommentSerializer,
    EditorPostCardSerializer,
    HomeSerializer,
    PostCardSerializer,
    PostDetailSerializer,
    PostWriteSerializer,
    SearchResultSerializer,
    SearchSuggestItemSerializer,
    TagSerializer,
)
from blog.models import Category, Post
from interactions.models import Comment


# ==================================================================
# PostCardSerializer
# ==================================================================
@pytest.mark.django_db
class TestPostCardSerializerShape:
    def test_contains_expected_fields(self, test_published_post, api_request):
        post = Post.objects.published().for_card().get(pk=test_published_post.pk)
        data = PostCardSerializer(post, context={"request": api_request}).data

        for field in (
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
        ):
            assert field in data, f"missing field: {field}"

    def test_author_is_nested_brief(self, test_published_post, api_request):
        post = Post.objects.published().for_card().get(pk=test_published_post.pk)
        data = PostCardSerializer(post, context={"request": api_request}).data

        assert data["author"]["username"] == test_published_post.author.username
        assert "display_name" in data["author"]
        assert "avatar_url" in data["author"]

    def test_category_is_nested_brief(self, test_published_post, api_request):
        post = Post.objects.published().for_card().get(pk=test_published_post.pk)
        data = PostCardSerializer(post, context={"request": api_request}).data

        assert data["category"]["id"] == test_published_post.category.pk
        assert data["category"]["slug"] == test_published_post.category.slug

    def test_counts_come_from_annotations(
        self,
        test_published_post,
        test_like,
        test_approved_comment,
        test_bookmark,
        api_request,
    ):
        post = Post.objects.published().for_card().get(pk=test_published_post.pk)
        data = PostCardSerializer(post, context={"request": api_request}).data

        assert data["like_count"] == 1
        assert data["comment_count"] == 1
        assert data["bookmark_count"] == 1


@pytest.mark.django_db
class TestPostCardAllowedActions:
    def test_anonymous_sees_public_flag_true(self, test_published_post, api_request):
        """
        Anonymous callers get the other flags False, but can_view_public
        is True for a published, non-deleted post.
        """
        post = Post.objects.published().for_card().get(pk=test_published_post.pk)
        data = PostCardSerializer(post, context={"request": api_request}).data

        assert data["allowed_actions"] == {
            "can_edit": False,
            "can_delete": False,
            "can_submit": False,
            "can_preview": False,
            "can_view_public": True,
        }

    def test_owner_of_draft_can_edit_delete_submit_preview(
        self, test_draft_post, api_request
    ):
        api_request.user = test_draft_post.author

        post = Post.objects.for_card().get(pk=test_draft_post.pk)
        data = PostCardSerializer(post, context={"request": api_request}).data
        actions = data["allowed_actions"]

        assert actions["can_edit"] is True
        assert actions["can_delete"] is True
        assert actions["can_submit"] is True
        assert actions["can_preview"] is True
        assert actions["can_view_public"] is False

    def test_owner_of_published_post_can_preview_but_not_edit(
        self, test_published_post, api_request
    ):
        api_request.user = test_published_post.author

        post = Post.objects.published().for_card().get(pk=test_published_post.pk)
        data = PostCardSerializer(post, context={"request": api_request}).data
        actions = data["allowed_actions"]

        assert actions["can_preview"] is True
        assert actions["can_view_public"] is True
        assert actions["can_edit"] is False
        assert actions["can_delete"] is False

    def test_editor_can_edit_and_delete_any_post(
        self, test_published_post, test_editor, api_request
    ):
        api_request.user = test_editor

        post = Post.objects.published().for_card().get(pk=test_published_post.pk)
        data = PostCardSerializer(post, context={"request": api_request}).data
        actions = data["allowed_actions"]

        assert actions["can_edit"] is True
        assert actions["can_delete"] is True
        assert actions["can_preview"] is True

    def test_other_author_gets_all_false(
        self, test_draft_post, test_other_author, api_request
    ):
        api_request.user = test_other_author

        post = Post.objects.for_card().get(pk=test_draft_post.pk)
        data = PostCardSerializer(post, context={"request": api_request}).data
        actions = data["allowed_actions"]

        assert actions["can_edit"] is False
        assert actions["can_delete"] is False
        assert actions["can_submit"] is False
        assert actions["can_preview"] is False


# ==================================================================
# EditorPostCardSerializer
# ==================================================================
@pytest.mark.django_db
class TestEditorPostCardSerializer:
    def test_extends_post_card_with_editor_fields(self, test_pending_post, api_request):
        post = Post.objects.for_card().get(pk=test_pending_post.pk)
        data = EditorPostCardSerializer(post, context={"request": api_request}).data

        for field in (
            "rejection_reason",
            "changes_requested_note",
            "reviewed_by",
            "reviewed_at",
        ):
            assert field in data

    def test_includes_inherited_post_card_fields(self, test_pending_post, api_request):
        post = Post.objects.for_card().get(pk=test_pending_post.pk)
        data = EditorPostCardSerializer(post, context={"request": api_request}).data

        assert "title" in data
        assert "allowed_actions" in data

    def test_reviewed_by_is_nested_brief(
        self, test_pending_post, test_editor, api_request
    ):
        test_pending_post.approve_and_publish(test_editor)

        post = Post.objects.published().for_card().get(pk=test_pending_post.pk)
        data = EditorPostCardSerializer(post, context={"request": api_request}).data

        assert data["reviewed_by"]["username"] == test_editor.username


# ==================================================================
# Category serializers
# ==================================================================
@pytest.mark.django_db
class TestCategoryBriefSerializer:
    def test_fields(self, test_category):
        data = CategoryBriefSerializer(test_category).data

        assert data == {
            "id": test_category.pk,
            "name": test_category.name,
            "slug": test_category.slug,
        }


@pytest.mark.django_db
class TestCategoryParentSerializer:
    def test_fields(self, test_category):
        data = CategoryParentSerializer(test_category).data

        assert data == {
            "id": test_category.pk,
            "name": test_category.name,
            "slug": test_category.slug,
        }


@pytest.mark.django_db
class TestCategorySerializer:
    def test_includes_post_count(self, test_category, test_published_post):
        from django.db.models import Count, Q

        category = (
            Category.objects.filter(pk=test_category.pk)
            .annotate(
                post_count=Count(
                    "posts",
                    filter=Q(posts__status="published", posts__is_deleted=False),
                    distinct=True,
                )
            )
            .get()
        )
        data = CategorySerializer(category).data

        assert data["post_count"] == 1

    def test_parent_is_nested(self, test_category, test_child_category):
        data = CategorySerializer(test_child_category).data

        assert data["parent"]["id"] == test_category.pk

    def test_parent_is_null_for_root(self, test_category):
        data = CategorySerializer(test_category).data
        assert data["parent"] is None


# ==================================================================
# TagSerializer
# ==================================================================
@pytest.mark.django_db
class TestTagSerializer:
    def test_fields(self, test_tag):
        data = TagSerializer(test_tag).data

        assert data == {
            "id": test_tag.pk,
            "name": test_tag.name,
            "slug": test_tag.slug,
            "usage_count": test_tag.usage_count,
        }


# ==================================================================
# HomeSerializer — container
# ==================================================================
@pytest.mark.django_db
class TestHomeSerializer:
    def test_serializes_empty_sections(self):
        data = HomeSerializer(
            {
                "featured": [],
                "latest": [],
                "trending": [],
                "categories": [],
                "hot_tags": [],
            }
        ).data

        assert data == {
            "featured": [],
            "latest": [],
            "trending": [],
            "categories": [],
            "hot_tags": [],
        }


# ==================================================================
# CommentAuthorSerializer / CommentSerializer
# ==================================================================
@pytest.mark.django_db
class TestCommentAuthorSerializer:
    def test_fields(self, test_user):
        data = CommentAuthorSerializer(test_user).data

        assert data["id"] == test_user.pk
        assert data["username"] == test_user.username
        assert data["display_name"] == test_user.display_name
        assert data["avatar_url"] == "/static/img/default-avatar.jpg"


@pytest.mark.django_db
class TestCommentSerializerAuthor:
    def test_present_author_is_serialized(self, test_approved_comment, api_request):
        # Do not annotate like_count on a Comment: Comment.like_count is a
        # Python property with no setter, so Django cannot attach an
        # annotation with the same name. The serializer falls back to the
        # property, which is fine for a single comment.
        data = CommentSerializer(
            test_approved_comment, context={"request": api_request}
        ).data

        assert data["author"]["username"] == test_approved_comment.author.username

    def test_deleted_author_gets_placeholder(self, test_approved_comment, api_request):
        # Comment.author is on_delete=SET_NULL. Null it directly to
        # exercise the placeholder branch.
        comment = Comment.objects.get(pk=test_approved_comment.pk)
        comment.author = None
        comment.save(update_fields=["author"])

        data = CommentSerializer(comment, context={"request": api_request}).data

        assert data["author"]["username"] is None
        assert data["author"]["display_name"] == "[deleted]"
        assert data["author"]["avatar_url"] is None


@pytest.mark.django_db
class TestCommentSerializerIsLiked:
    def test_false_when_no_request(self, test_approved_comment):
        data = CommentSerializer(test_approved_comment).data
        assert data["is_liked"] is False

    def test_false_for_anonymous(self, test_approved_comment, api_request):
        data = CommentSerializer(
            test_approved_comment, context={"request": api_request}
        ).data
        assert data["is_liked"] is False

    def test_true_when_in_liked_comment_ids(
        self, test_approved_comment, test_user, api_request
    ):
        api_request.user = test_user
        data = CommentSerializer(
            test_approved_comment,
            context={
                "request": api_request,
                "liked_comment_ids": {test_approved_comment.id},
            },
        ).data

        assert data["is_liked"] is True

    def test_false_when_not_in_liked_comment_ids(
        self, test_approved_comment, test_user, api_request
    ):
        api_request.user = test_user
        data = CommentSerializer(
            test_approved_comment,
            context={
                "request": api_request,
                "liked_comment_ids": set(),
            },
        ).data

        assert data["is_liked"] is False


@pytest.mark.django_db
class TestCommentSerializerReplies:
    def test_replies_only_include_approved_non_deleted(
        self, test_approved_comment, test_user, api_request
    ):
        Comment.objects.create(
            post=test_approved_comment.post,
            author=test_user,
            parent=test_approved_comment,
            body="approved reply",
            status=Comment.Status.APPROVED,
            is_deleted=False,
        )
        Comment.objects.create(
            post=test_approved_comment.post,
            author=test_user,
            parent=test_approved_comment,
            body="pending reply",
            status=Comment.Status.PENDING,
            is_deleted=False,
        )
        Comment.objects.create(
            post=test_approved_comment.post,
            author=test_user,
            parent=test_approved_comment,
            body="deleted reply",
            status=Comment.Status.APPROVED,
            is_deleted=True,
        )

        data = CommentSerializer(
            test_approved_comment, context={"request": api_request}
        ).data

        assert len(data["replies"]) == 1
        assert data["replies"][0]["body"] == "approved reply"


# ==================================================================
# PostDetailSerializer
# ==================================================================
@pytest.mark.django_db
class TestPostDetailSerializerShape:
    def test_contains_expected_fields(self, test_published_post, api_request):
        post = Post.objects.published().for_card().get(pk=test_published_post.pk)
        data = PostDetailSerializer(post, context={"request": api_request}).data

        for field in (
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
        ):
            assert field in data

    def test_tags_serialized(self, test_post_with_tags, api_request):
        post = (
            Post.objects.published()
            .for_card()
            .prefetch_related("tags")
            .get(pk=test_post_with_tags.pk)
        )
        data = PostDetailSerializer(post, context={"request": api_request}).data

        assert len(data["tags"]) == 2


@pytest.mark.django_db
class TestPostDetailSerializerUserFlags:
    def test_is_liked_false_for_anonymous(self, test_published_post, api_request):
        post = Post.objects.published().for_card().get(pk=test_published_post.pk)
        data = PostDetailSerializer(post, context={"request": api_request}).data

        assert data["is_liked"] is False
        assert data["is_bookmarked"] is False

    def test_is_liked_true_when_in_context(
        self, test_published_post, test_user, api_request
    ):
        api_request.user = test_user
        post = Post.objects.published().for_card().get(pk=test_published_post.pk)
        data = PostDetailSerializer(
            post,
            context={
                "request": api_request,
                "liked_post_ids": {post.id},
            },
        ).data

        assert data["is_liked"] is True

    def test_is_bookmarked_true_when_in_context(
        self, test_published_post, test_user, api_request
    ):
        api_request.user = test_user
        post = Post.objects.published().for_card().get(pk=test_published_post.pk)
        data = PostDetailSerializer(
            post,
            context={
                "request": api_request,
                "bookmarked_post_ids": {post.id},
            },
        ).data

        assert data["is_bookmarked"] is True


@pytest.mark.django_db
class TestPostDetailSerializerComments:
    def test_comments_from_context(
        self, test_published_post, test_approved_comment, api_request
    ):
        post = Post.objects.published().for_card().get(pk=test_published_post.pk)
        data = PostDetailSerializer(
            post,
            context={
                "request": api_request,
                "top_level_comments": [test_approved_comment],
            },
        ).data

        assert len(data["comments"]) == 1
        assert data["comments"][0]["id"] == test_approved_comment.pk

    def test_comments_default_query_when_context_missing(
        self,
        test_published_post,
        test_approved_comment,
        test_pending_comment,
        test_soft_deleted_comment,
        api_request,
    ):
        post = Post.objects.published().for_card().get(pk=test_published_post.pk)
        data = PostDetailSerializer(post, context={"request": api_request}).data

        ids = [c["id"] for c in data["comments"]]
        assert test_approved_comment.id in ids
        assert test_pending_comment.id not in ids
        assert test_soft_deleted_comment.id not in ids


@pytest.mark.django_db
class TestPostDetailSerializerRelated:
    def test_similar_posts_from_context(
        self, test_published_post, test_second_published_post, api_request
    ):
        post = Post.objects.published().for_card().get(pk=test_published_post.pk)
        data = PostDetailSerializer(
            post,
            context={
                "request": api_request,
                "similar_posts": [test_second_published_post],
            },
        ).data

        assert len(data["similar_posts"]) == 1
        assert data["similar_posts"][0]["id"] == test_second_published_post.pk

    def test_author_other_posts_from_context(
        self, test_published_post, test_second_published_post, api_request
    ):
        post = Post.objects.published().for_card().get(pk=test_published_post.pk)
        data = PostDetailSerializer(
            post,
            context={
                "request": api_request,
                "author_other_posts": [test_second_published_post],
            },
        ).data

        assert len(data["author_other_posts"]) == 1

    def test_similar_posts_empty_list_when_missing(
        self, test_published_post, api_request
    ):
        post = Post.objects.published().for_card().get(pk=test_published_post.pk)
        data = PostDetailSerializer(post, context={"request": api_request}).data

        assert data["similar_posts"] == []
        assert data["author_other_posts"] == []


# ==================================================================
# SearchResultSerializer / SearchSuggestItemSerializer
# ==================================================================
class TestSearchResultSerializer:
    def test_fields(self):
        data = SearchResultSerializer(
            {"type": "post", "count": 3, "results": [{"id": 1}]}
        ).data

        assert data["type"] == "post"
        assert data["count"] == 3
        assert data["results"] == [{"id": 1}]


class TestSearchSuggestItemSerializer:
    def test_valid_item(self):
        data = SearchSuggestItemSerializer(
            {
                "type": "post",
                "id": 1,
                "label": "Hello",
                "slug": "hello",
                "url": "/posts/hello/",
            }
        ).data

        assert data["type"] == "post"

    def test_invalid_type_rejected(self):
        serializer = SearchSuggestItemSerializer(
            data={
                "type": "unknown",
                "id": 1,
                "label": "x",
                "slug": "x",
                "url": "/x/",
            }
        )
        assert not serializer.is_valid()
        assert "type" in serializer.errors


# ==================================================================
# PostWriteSerializer
# ==================================================================
@pytest.mark.django_db
class TestPostWriteSerializerHappyPath:
    def test_creates_draft_post(self, test_author, test_category):
        serializer = PostWriteSerializer(
            data={
                "title": "My New Post",
                "body": "<p>Body of the post.</p>",
                "category": test_category.id,
            }
        )
        assert serializer.is_valid(), serializer.errors
        post = serializer.save(author=test_author, status=Post.Status.DRAFT)

        assert post.pk is not None
        assert post.author == test_author
        assert post.status == Post.Status.DRAFT
        assert post.slug

    def test_sanitizes_body(self, test_author, test_category):
        serializer = PostWriteSerializer(
            data={
                "title": "My New Post",
                "body": '<p>Hello</p><script>alert("x")</script>',
                "category": test_category.id,
            }
        )
        assert serializer.is_valid(), serializer.errors
        post = serializer.save(author=test_author)

        assert "<script" not in post.body.lower()
        assert "Hello" in post.body

    def test_accepts_slug_blank(self, test_author, test_category):
        serializer = PostWriteSerializer(
            data={
                "title": "My New Post",
                "body": "<p>Body.</p>",
                "slug": "",
                "category": test_category.id,
            }
        )
        assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
class TestPostWriteSerializerValidation:
    def test_title_too_short_is_rejected(self, test_category):
        serializer = PostWriteSerializer(
            data={"title": "ab", "body": "<p>Body.</p>", "category": test_category.id}
        )
        assert not serializer.is_valid()
        assert "title" in serializer.errors

    def test_title_whitespace_stripped(self, test_category):
        serializer = PostWriteSerializer(
            data={
                "title": "  Valid Title  ",
                "body": "<p>Body.</p>",
                "category": test_category.id,
            }
        )
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["title"] == "Valid Title"

    def test_blank_body_is_rejected(self, test_category):
        serializer = PostWriteSerializer(
            data={"title": "Valid Title", "body": "   ", "category": test_category.id}
        )
        assert not serializer.is_valid()
        assert "body" in serializer.errors

    def test_body_with_only_a_script_tag_is_currently_accepted(self, test_category):
        """
        Documents current behavior.

        bleach.clean(strip=True) removes the <script> tag but keeps
        its text content, so the sanitized body is not empty. The
        serializer's "body cannot be empty after sanitization" check
        therefore does not fire for input that is exclusively a
        script tag.

        If the intended contract is to reject such input, the check
        needs to inspect the tag structure, not just the cleaned
        text. This test would then need to flip.
        """
        serializer = PostWriteSerializer(
            data={
                "title": "Valid Title",
                "body": "<script>alert(1)</script>",
                "category": test_category.id,
            }
        )
        assert serializer.is_valid(), serializer.errors
        # The sanitized body is the script's text content.
        assert "<script" not in serializer.validated_data["body"].lower()

    def test_summary_html_under_500_is_cleaned_and_accepted(self, test_category):
        # Under DRF's max_length=500 raw-char limit after the tags
        # are removed by the field's own validation? No — DRF counts
        # raw characters. Keep it small enough to pass, and check
        # the sanitized value.
        serializer = PostWriteSerializer(
            data={
                "title": "Valid Title",
                "body": "<p>Body.</p>",
                "summary": "<p>" + "a" * 100 + "</p>",
                "category": test_category.id,
            }
        )
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["summary"] == "a" * 100

    def test_summary_over_500_is_rejected(self, test_category):
        """
        DRF's CharField(max_length=500) checks the raw length before
        validate_summary runs, so input over 500 chars is rejected
        regardless of HTML stripping.
        """
        serializer = PostWriteSerializer(
            data={
                "title": "Valid Title",
                "body": "<p>Body.</p>",
                "summary": "a" * 700,
                "category": test_category.id,
            }
        )
        assert not serializer.is_valid()
        assert "summary" in serializer.errors

    def test_category_in_extra_categories_is_rejected(
        self, test_category, test_second_category
    ):
        serializer = PostWriteSerializer(
            data={
                "title": "Valid Title",
                "body": "<p>Body.</p>",
                "category": test_category.id,
                "extra_categories": [test_category.id],
            }
        )
        assert not serializer.is_valid()
        assert "extra_categories" in serializer.errors

    def test_meta_title_whitespace_stripped(self, test_category):
        serializer = PostWriteSerializer(
            data={
                "title": "Valid Title",
                "body": "<p>Body.</p>",
                "category": test_category.id,
                "meta_title": "  Custom Meta  ",
            }
        )
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["meta_title"] == "Custom Meta"

    def test_meta_description_whitespace_stripped(self, test_category):
        serializer = PostWriteSerializer(
            data={
                "title": "Valid Title",
                "body": "<p>Body.</p>",
                "category": test_category.id,
                "meta_description": "  Meta desc  ",
            }
        )
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["meta_description"] == "Meta desc"


@pytest.mark.django_db
class TestPostWriteSerializerMultipart:
    def test_tags_and_extra_categories_lists(
        self, test_author, test_category, test_tag
    ):
        from django.http import QueryDict

        data = QueryDict(mutable=True)
        data.setlist("tags", [str(test_tag.id)])
        data.setlist("extra_categories", [""])
        data["title"] = "Multipart Title"
        data["body"] = "<p>Body.</p>"
        data["category"] = str(test_category.id)

        serializer = PostWriteSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data.get("extra_categories", []) == []
        assert list(serializer.validated_data["tags"]) == [test_tag]
