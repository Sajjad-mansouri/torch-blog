"""
Behavioral tests for blog models: Category, Tag, Post, PostView,
PostRevision, and PostQuerySet.

Assertions reflect the actual observable behavior of the current
implementation. Where behavior is unusual or inconsistent, it is
documented explicitly in the test's name and docstring, so that any
change to the code produces a clear, intentional failure rather than
a silent regression.
"""

from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from blog.models import Category, Post, PostRevision, PostView, Tag


# ==================================================================
# Category
# ==================================================================
@pytest.mark.django_db
class TestCategorySlug:
    def test_slug_is_generated_from_name_on_save(self):
        category = Category.objects.create(name="Web Development")
        assert category.slug == "web-development"

    def test_existing_slug_is_not_overwritten(self):
        category = Category.objects.create(name="Alpha", slug="custom-slug")
        assert category.slug == "custom-slug"

    def test_slug_collision_across_different_names_appends_counter(self):
        # Two different names that slugify to the same base slug.
        # "Hello, World!" and "Hello World" both slugify to "hello-world".
        Category.objects.create(name="Hello World")
        second = Category.objects.create(name="Hello, World!")

        assert second.slug == "hello-world-1"

    def test_slug_collision_appends_incrementing_counter(self):
        Category.objects.create(name="Hello World")
        Category.objects.create(name="Hello, World!")
        third = Category.objects.create(name="Hello -- World")

        # Third collision appends the next counter.
        assert third.slug == "hello-world-2"

    def test_duplicate_name_is_rejected_by_the_model(self):
        # documents that `name` uniqueness is enforced at the DB level
        Category.objects.create(name="Repeated")
        with pytest.raises(IntegrityError):
            Category.objects.create(name="Repeated")

    def test_unicode_name_is_slugified(self):
        category = Category.objects.create(name="Café Résumé")
        # slugify with allow_unicode=True keeps the unicode characters.
        assert "caf" in category.slug
        assert " " not in category.slug


@pytest.mark.django_db
class TestCategoryStr:
    def test_root_category_str_is_name(self, test_category):
        assert str(test_category) == test_category.name

    def test_child_category_str_includes_parent(
        self, test_category, test_child_category
    ):
        assert (
            str(test_child_category)
            == f"{test_category.name} → {test_child_category.name}"
        )


@pytest.mark.django_db
class TestCategoryOrdering:
    def test_default_ordering_is_by_order_then_name(
        self, test_category, test_second_category
    ):
        test_category.order = 2
        test_category.save()
        test_second_category.order = 1
        test_second_category.save()

        ordered = list(Category.objects.all())
        assert ordered[0] == test_second_category
        assert ordered[1] == test_category


# ==================================================================
# Tag
# ==================================================================
@pytest.mark.django_db
class TestTagSlug:
    def test_slug_is_generated_from_name(self):
        tag = Tag.objects.create(name="Python")
        assert tag.slug == "python"

    def test_existing_slug_is_not_overwritten(self):
        tag = Tag.objects.create(name="Python", slug="py")
        assert tag.slug == "py"


@pytest.mark.django_db
class TestTagOrdering:
    def test_default_ordering_by_usage_count_desc_then_name(self):
        Tag.objects.create(name="zebra", usage_count=5)
        Tag.objects.create(name="apple", usage_count=5)
        Tag.objects.create(name="low", usage_count=1)

        ordered = list(Tag.objects.all())
        assert [t.name for t in ordered] == ["apple", "zebra", "low"]


# ==================================================================
# Post.save() side effects
# ==================================================================
@pytest.mark.django_db
class TestPostSaveSlug:
    def test_slug_is_generated_from_title(self, test_author, test_category):
        post = Post.objects.create(
            author=test_author,
            title="Hello World",
            body="<p>Body.</p>",
            category=test_category,
        )
        assert post.slug == "hello-world"

    def test_provided_slug_is_preserved(self, test_author, test_category):
        post = Post.objects.create(
            author=test_author,
            title="Hello",
            slug="custom-slug",
            body="<p>Body.</p>",
            category=test_category,
        )
        assert post.slug == "custom-slug"

    def test_slug_collision_appends_counter(self, test_author, test_category):
        Post.objects.create(
            author=test_author,
            title="Same Title",
            body="<p>One.</p>",
            category=test_category,
        )
        second = Post.objects.create(
            author=test_author,
            title="Same Title",
            body="<p>Two.</p>",
            category=test_category,
        )
        assert second.slug == "same-title-1"


@pytest.mark.django_db
class TestPostSaveSummarySanitization:
    def test_summary_html_is_stripped_to_plain_text(self, test_author, test_category):
        post = Post.objects.create(
            author=test_author,
            title="T",
            summary="<p>Hello <strong>world</strong></p>",
            body="<p>Body.</p>",
            category=test_category,
        )
        assert post.summary == "Hello world"

    def test_summary_is_truncated_to_500_characters(self, test_author, test_category):
        long_text = "a" * 700
        post = Post.objects.create(
            author=test_author,
            title="T",
            summary=long_text,
            body="<p>Body.</p>",
            category=test_category,
        )
        assert len(post.summary) == 500

    def test_blank_summary_is_left_blank(self, test_author, test_category):
        post = Post.objects.create(
            author=test_author,
            title="T",
            summary="",
            body="<p>Body.</p>",
            category=test_category,
        )
        assert post.summary == ""


@pytest.mark.django_db
class TestPostSaveReadingTime:
    def test_reading_time_is_auto_calculated(self, test_author, test_category):
        # ~50 words → 1 minute under the 200 wpm English rate.
        body = "<p>" + " ".join(["word"] * 50) + "</p>"
        post = Post.objects.create(
            author=test_author,
            title="T",
            body=body,
            category=test_category,
        )
        assert post.reading_time == 1

    def test_empty_body_still_produces_minimum_reading_time(
        self, test_author, test_category
    ):
        post = Post.objects.create(
            author=test_author,
            title="T",
            body="",
            category=test_category,
        )
        assert post.reading_time == 1


@pytest.mark.django_db
class TestPostSavePublishedAt:
    def test_publishing_sets_published_at_if_missing(self, test_author, test_category):
        post = Post.objects.create(
            author=test_author,
            title="T",
            body="<p>Body.</p>",
            category=test_category,
            status=Post.Status.PUBLISHED,
        )
        assert post.published_at is not None

    def test_existing_published_at_is_preserved(self, test_author, test_category):
        explicit = timezone.now() - timedelta(days=3)
        post = Post.objects.create(
            author=test_author,
            title="T",
            body="<p>Body.</p>",
            category=test_category,
            status=Post.Status.PUBLISHED,
            published_at=explicit,
        )
        assert post.published_at == explicit

    def test_draft_post_has_no_published_at(self, test_draft_post):
        assert test_draft_post.published_at is None


@pytest.mark.django_db
class TestPostSaveMetaFields:
    def test_meta_title_defaults_to_title(self, test_author, test_category):
        post = Post.objects.create(
            author=test_author,
            title="A Long Title But Under 200 Chars",
            body="<p>Body.</p>",
            category=test_category,
        )
        assert post.meta_title == post.title

    def test_meta_title_is_not_overwritten_when_provided(
        self, test_author, test_category
    ):
        post = Post.objects.create(
            author=test_author,
            title="Title",
            body="<p>Body.</p>",
            category=test_category,
            meta_title="Custom meta title",
        )
        assert post.meta_title == "Custom meta title"

    def test_meta_description_defaults_from_summary(self, test_author, test_category):
        post = Post.objects.create(
            author=test_author,
            title="T",
            summary="The summary text.",
            body="<p>Body.</p>",
            category=test_category,
        )
        assert post.meta_description == "The summary text."

    def test_meta_description_falls_back_to_clean_body(
        self, test_author, test_category
    ):
        post = Post.objects.create(
            author=test_author,
            title="T",
            summary="",
            body="<p>Body becomes meta.</p>",
            category=test_category,
        )
        assert post.meta_description == "Body becomes meta."


# ==================================================================
# Post status transitions
# ==================================================================
@pytest.mark.django_db
class TestPostSubmitForReview:
    def test_submit_transitions_draft_to_pending(self, test_draft_post):
        test_draft_post.submit_for_review()
        test_draft_post.refresh_from_db()

        assert test_draft_post.status == Post.Status.PENDING

    def test_submit_clears_rejection_reason_and_note(self, test_author, test_category):
        post = Post.objects.create(
            author=test_author,
            title="T",
            body="<p>Body.</p>",
            category=test_category,
            status=Post.Status.REJECTED,
            rejection_reason="old reason",
            changes_requested_note="old note",
        )
        post.submit_for_review()
        post.refresh_from_db()

        assert post.rejection_reason == ""
        assert post.changes_requested_note == ""


@pytest.mark.django_db
class TestPostApproveAndPublish:
    def test_sets_status_reviewer_and_reviewed_at(self, test_pending_post, test_editor):
        test_pending_post.approve_and_publish(test_editor)
        test_pending_post.refresh_from_db()

        assert test_pending_post.status == Post.Status.PUBLISHED
        assert test_pending_post.reviewed_by == test_editor
        assert test_pending_post.reviewed_at is not None

    def test_sets_published_at_if_missing(self, test_pending_post, test_editor):
        assert test_pending_post.published_at is None
        test_pending_post.approve_and_publish(test_editor)
        test_pending_post.refresh_from_db()

        assert test_pending_post.published_at is not None

    def test_clears_rejection_and_changes_note(
        self, test_author, test_category, test_editor
    ):
        post = Post.objects.create(
            author=test_author,
            title="T",
            body="<p>Body.</p>",
            category=test_category,
            status=Post.Status.PENDING,
            rejection_reason="r",
            changes_requested_note="c",
        )
        post.approve_and_publish(test_editor)
        post.refresh_from_db()

        assert post.rejection_reason == ""
        assert post.changes_requested_note == ""


@pytest.mark.django_db
class TestPostReject:
    def test_reject_sets_status_reviewer_and_reviewed_at(
        self, test_pending_post, test_editor
    ):
        test_pending_post.reject(test_editor, "off-topic")
        test_pending_post.refresh_from_db()

        assert test_pending_post.status == Post.Status.REJECTED
        assert test_pending_post.reviewed_by == test_editor
        # B12 fix: reviewed_at must be persisted (was silently dropped).
        assert test_pending_post.reviewed_at is not None

    def test_reject_stores_reason(self, test_pending_post, test_editor):
        test_pending_post.reject(test_editor, "off-topic")
        test_pending_post.refresh_from_db()

        assert test_pending_post.rejection_reason == "off-topic"


@pytest.mark.django_db
class TestPostRequestChanges:
    def test_request_changes_sets_status_reviewer_and_reviewed_at(
        self, test_pending_post, test_editor
    ):
        test_pending_post.request_changes(test_editor, "tighten intro")
        test_pending_post.refresh_from_db()

        assert test_pending_post.status == Post.Status.CHANGES_REQUESTED
        assert test_pending_post.reviewed_by == test_editor
        assert test_pending_post.reviewed_at is not None

    def test_request_changes_stores_note(self, test_pending_post, test_editor):
        test_pending_post.request_changes(test_editor, "tighten intro")
        test_pending_post.refresh_from_db()

        assert test_pending_post.changes_requested_note == "tighten intro"


@pytest.mark.django_db
class TestPostUnpublish:
    def test_unpublish_sets_status_reviewer_and_reviewed_at(
        self, test_published_post, test_editor
    ):
        test_published_post.unpublish(test_editor, "needs update")
        test_published_post.refresh_from_db()

        assert test_published_post.status == Post.Status.UNPUBLISHED
        assert test_published_post.reviewed_by == test_editor
        assert test_published_post.reviewed_at is not None

    def test_unpublish_stores_reason(self, test_published_post, test_editor):
        test_published_post.unpublish(test_editor, "needs update")
        test_published_post.refresh_from_db()

        assert test_published_post.rejection_reason == "needs update"


# ==================================================================
# Post soft delete / restore
# ==================================================================
@pytest.mark.django_db
class TestPostSoftDelete:
    def test_soft_delete_sets_flags_and_user(self, test_published_post, test_editor):
        original_slug = test_published_post.slug
        test_published_post.soft_delete(test_editor)
        test_published_post.refresh_from_db()

        assert test_published_post.is_deleted is True
        assert test_published_post.deleted_by == test_editor
        assert test_published_post.deleted_at is not None
        assert test_published_post.slug != original_slug
        assert "-deleted-" in test_published_post.slug

    def test_soft_delete_row_still_exists_in_db(self, test_published_post, test_editor):
        pk = test_published_post.pk
        test_published_post.soft_delete(test_editor)

        # The row is not removed; only flagged.
        assert Post.objects.filter(pk=pk).exists()


@pytest.mark.django_db
class TestPostRestore:
    def test_restore_clears_flags_and_regenerates_slug(
        self, test_published_post, test_editor
    ):
        test_published_post.soft_delete(test_editor)
        test_published_post.restore()
        test_published_post.refresh_from_db()

        assert test_published_post.is_deleted is False
        assert test_published_post.deleted_by is None
        assert test_published_post.deleted_at is None
        assert "-deleted-" not in test_published_post.slug


# ==================================================================
# Post permission helpers
# ==================================================================
@pytest.mark.django_db
class TestPostCanBeEditedBy:
    @pytest.mark.parametrize(
        "status, expected",
        [
            (Post.Status.DRAFT, True),
            (Post.Status.REJECTED, True),
            (Post.Status.CHANGES_REQUESTED, True),
            (Post.Status.PENDING, False),
            (Post.Status.PUBLISHED, False),
            (Post.Status.UNPUBLISHED, False),
            (Post.Status.ARCHIVED, False),
        ],
    )
    def test_author_can_edit_only_in_editable_statuses(
        self, test_author, test_category, status, expected
    ):
        post = Post.objects.create(
            author=test_author,
            title="T",
            body="<p>Body.</p>",
            category=test_category,
            status=status,
        )
        assert post.can_be_edited_by(test_author) is expected

    def test_editor_can_always_edit(self, test_draft_post, test_editor):
        assert test_draft_post.can_be_edited_by(test_editor) is True

    def test_other_author_cannot_edit(self, test_draft_post, test_other_author):
        assert test_draft_post.can_be_edited_by(test_other_author) is False

    def test_anonymous_cannot_edit(self, test_draft_post):
        class Anon:
            is_authenticated = False

        assert test_draft_post.can_be_edited_by(Anon()) is False

    def test_none_user_cannot_edit(self, test_draft_post):
        assert test_draft_post.can_be_edited_by(None) is False


@pytest.mark.django_db
class TestPostCanBeDeletedBy:
    @pytest.mark.parametrize(
        "status, expected",
        [
            (Post.Status.DRAFT, True),
            (Post.Status.REJECTED, True),
            (Post.Status.ARCHIVED, True),
            (Post.Status.PENDING, False),
            (Post.Status.PUBLISHED, False),
            (Post.Status.UNPUBLISHED, False),
        ],
    )
    def test_author_can_delete_only_in_deletable_statuses(
        self, test_author, test_category, status, expected
    ):
        post = Post.objects.create(
            author=test_author,
            title="T",
            body="<p>Body.</p>",
            category=test_category,
            status=status,
        )
        assert post.can_be_deleted_by(test_author) is expected

    def test_editor_can_always_delete(self, test_published_post, test_editor):
        assert test_published_post.can_be_deleted_by(test_editor) is True

    def test_other_author_cannot_delete(self, test_draft_post, test_other_author):
        assert test_draft_post.can_be_deleted_by(test_other_author) is False


@pytest.mark.django_db
class TestPostCanBeSubmittedBy:
    @pytest.mark.parametrize(
        "status, expected",
        [
            (Post.Status.DRAFT, True),
            (Post.Status.REJECTED, True),
            (Post.Status.CHANGES_REQUESTED, True),
            (Post.Status.PENDING, False),
            (Post.Status.PUBLISHED, False),
            (Post.Status.UNPUBLISHED, False),
            (Post.Status.ARCHIVED, False),
        ],
    )
    def test_author_can_submit_in_submittable_statuses(
        self, test_author, test_category, status, expected
    ):
        post = Post.objects.create(
            author=test_author,
            title="T",
            body="<p>Body.</p>",
            category=test_category,
            status=status,
        )
        assert post.can_be_submitted_by(test_author) is expected

    def test_editor_who_is_not_author_cannot_submit(self, test_draft_post, test_editor):
        # CanBeSubmittedBy does not allow editors who are not the author.
        assert test_draft_post.can_be_submitted_by(test_editor) is False


# ==================================================================
# Post other properties
# ==================================================================
@pytest.mark.django_db
class TestPostIsPublished:
    def test_published_and_not_deleted_is_published(self, test_published_post):
        assert test_published_post.is_published is True

    def test_published_but_soft_deleted_is_not_published(
        self, test_published_post, test_editor
    ):
        test_published_post.soft_delete(test_editor)
        assert test_published_post.is_published is False

    def test_draft_is_not_published(self, test_draft_post):
        assert test_draft_post.is_published is False


# ==================================================================
# PostQuerySet
# ==================================================================
@pytest.mark.django_db
class TestPostQuerySetPublished:
    def test_includes_published_non_deleted_past_posts(self, test_published_post):
        assert test_published_post in Post.objects.published()

    def test_excludes_drafts(self, test_draft_post):
        assert test_draft_post not in Post.objects.published()

    def test_excludes_soft_deleted(self, test_soft_deleted_post):
        assert test_soft_deleted_post not in Post.objects.published()

    def test_excludes_future_published_at(self, test_scheduled_future_post):
        assert test_scheduled_future_post not in Post.objects.published()


@pytest.mark.django_db
class TestPostQuerySetFeatured:
    def test_includes_only_featured(self, test_featured_post, test_published_post):
        result = list(Post.objects.featured())
        assert test_featured_post in result
        assert test_published_post not in result

    def test_ordered_by_featured_order(
        self, test_author, test_category, test_featured_post
    ):
        Post.objects.create(
            author=test_author,
            title="Second Featured",
            body="<p>B.</p>",
            category=test_category,
            status=Post.Status.PUBLISHED,
            published_at=timezone.now() - timedelta(hours=1),
            is_featured=True,
            featured_order=2,
        )
        result = list(Post.objects.featured())
        assert result[0] == test_featured_post


@pytest.mark.django_db
class TestPostQuerySetTrending:
    def test_includes_recent_published_posts(self, test_published_post):
        result = list(Post.objects.trending(days=7))
        assert test_published_post in result

    def test_excludes_old_published_posts(self, test_author, test_category):
        old = Post.objects.create(
            author=test_author,
            title="Old",
            body="<p>B.</p>",
            category=test_category,
            status=Post.Status.PUBLISHED,
            published_at=timezone.now() - timedelta(days=30),
        )
        result = list(Post.objects.trending(days=7))
        assert old not in result


@pytest.mark.django_db
class TestPostQuerySetLatest:
    def test_latest_orders_newest_first(
        self, test_published_post, test_second_published_post
    ):
        # test_second_published_post is newer.
        result = list(Post.objects.latest())
        assert result.index(test_second_published_post) < result.index(
            test_published_post
        )


@pytest.mark.django_db
class TestPostQuerySetForCard:
    def test_annotates_like_comment_bookmark_counts(
        self, test_published_post, test_like, test_approved_comment, test_bookmark
    ):
        post = Post.objects.published().for_card().get(pk=test_published_post.pk)

        assert post.like_count == 1
        assert post.comment_count == 1
        assert post.bookmark_count == 1

    def test_comment_count_respects_approved_and_not_deleted(
        self,
        test_published_post,
        test_approved_comment,
        test_pending_comment,
        test_soft_deleted_comment,
    ):
        post = Post.objects.published().for_card().get(pk=test_published_post.pk)
        assert post.comment_count == 1


# ==================================================================
# PostView
# ==================================================================
@pytest.mark.django_db
class TestPostViewModel:
    def test_create_post_view(self, test_published_post, test_user):
        view = PostView.objects.create(
            post=test_published_post,
            user=test_user,
            ip_address="10.0.0.1",
            user_agent="pytest",
        )
        assert view.pk is not None
        assert view.post == test_published_post
        assert view.user == test_user

    def test_default_ordering_is_newest_first(self, test_published_post, test_user):
        earlier = PostView.objects.create(post=test_published_post, user=test_user)
        later = PostView.objects.create(post=test_published_post, user=test_user)

        result = list(PostView.objects.all())
        assert result[0] == later
        assert result[1] == earlier

    def test_str_includes_post_title(self, test_published_post, test_user):
        view = PostView.objects.create(post=test_published_post, user=test_user)
        assert test_published_post.title in str(view)


# ==================================================================
# PostRevision
# ==================================================================
@pytest.mark.django_db
class TestPostRevisionCreateForPost:
    def test_first_revision_is_number_one(self, test_published_post, test_author):
        revision = PostRevision.create_for_post(
            post=test_published_post, user=test_author
        )
        assert revision.revision_number == 1

    def test_revisions_increment(self, test_published_post, test_author):
        PostRevision.create_for_post(post=test_published_post, user=test_author)
        second = PostRevision.create_for_post(
            post=test_published_post, user=test_author
        )
        third = PostRevision.create_for_post(post=test_published_post, user=test_author)

        assert second.revision_number == 2
        assert third.revision_number == 3

    def test_snapshot_copies_title_summary_body(self, test_published_post, test_author):
        revision = PostRevision.create_for_post(
            post=test_published_post, user=test_author
        )
        assert revision.title == test_published_post.title
        assert revision.summary == test_published_post.summary
        assert revision.body == test_published_post.body

    def test_duplicate_revision_number_for_same_post_is_rejected(
        self, test_published_post, test_author, test_post_revision
    ):
        with pytest.raises(IntegrityError):
            PostRevision.objects.create(
                post=test_published_post,
                revision_number=test_post_revision.revision_number,
                title="dup",
                body="<p>dup</p>",
                edited_by=test_author,
            )


@pytest.mark.django_db
class TestPostRevisionOrdering:
    def test_latest_revision_first(self, test_published_post, test_author):
        PostRevision.create_for_post(post=test_published_post, user=test_author)
        second = PostRevision.create_for_post(
            post=test_published_post, user=test_author
        )

        result = list(PostRevision.objects.filter(post=test_published_post))
        assert result[0] == second


# ==================================================================
# Featured order uniqueness constraint
# ==================================================================
@pytest.mark.django_db
class TestFeaturedOrderConstraint:
    def test_two_featured_posts_with_same_order_violates_constraint(
        self, test_author, test_category, test_featured_post
    ):
        with pytest.raises(IntegrityError):
            Post.objects.create(
                author=test_author,
                title="Conflicting Featured",
                body="<p>B.</p>",
                category=test_category,
                status=Post.Status.PUBLISHED,
                published_at=timezone.now(),
                is_featured=True,
                featured_order=test_featured_post.featured_order,
            )

    def test_two_non_featured_posts_with_same_order_are_allowed(
        self, test_author, test_category
    ):
        Post.objects.create(
            author=test_author,
            title="A",
            body="<p>B.</p>",
            category=test_category,
            is_featured=False,
            featured_order=5,
        )
        Post.objects.create(
            author=test_author,
            title="B",
            body="<p>B.</p>",
            category=test_category,
            is_featured=False,
            featured_order=5,
        )
        assert Post.objects.filter(featured_order=5).count() == 2


# ==================================================================
# Post author on_delete=PROTECT
# ==================================================================
@pytest.mark.django_db
class TestPostAuthorProtection:
    def test_deleting_author_with_posts_is_protected(
        self, test_author, test_published_post
    ):
        from django.db.models import ProtectedError

        with pytest.raises(ProtectedError):
            test_author.delete()
