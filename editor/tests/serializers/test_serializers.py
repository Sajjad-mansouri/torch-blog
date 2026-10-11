"""
Behavioral tests for editor serializers.

Coverage:
- RejectPostSerializer / RequestChangesSerializer /
  UnpublishPostSerializer — decision payload validation.
- FeaturedReorderItemSerializer / FeaturedReorderSerializer —
  reorder payload validation and duplicate-ID rejection.
- TagMergeSerializer — merge payload validation and
  target-in-sources rejection.
- CategoryWriteSerializer / TagWriteSerializer — write serializers
  for taxonomy, including slug handling.

Assertions reflect the actual observable behavior of the current
implementation. Where the behavior is unusual or has a non-obvious
contract, it is called out in the test name or docstring.
"""

import pytest

from editor.api.serializers import (
    FeaturedReorderItemSerializer,
    FeaturedReorderSerializer,
    RejectPostSerializer,
    RequestChangesSerializer,
    TagMergeSerializer,
    UnpublishPostSerializer,
)
from editor.api.views.taxonomy import (
    CategoryWriteSerializer,
    TagWriteSerializer,
)


# ==================================================================
# RejectPostSerializer
# ==================================================================
class TestRejectPostSerializer:
    def test_valid_reason(self):
        serializer = RejectPostSerializer(data={"reason": "off-topic"})
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["reason"] == "off-topic"

    def test_reason_is_trimmed(self):
        serializer = RejectPostSerializer(data={"reason": "  off-topic  "})
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["reason"] == "off-topic"

    def test_missing_reason_is_rejected(self):
        serializer = RejectPostSerializer(data={})
        assert not serializer.is_valid()
        assert "reason" in serializer.errors

    def test_empty_reason_is_rejected(self):
        serializer = RejectPostSerializer(data={"reason": ""})
        assert not serializer.is_valid()
        assert "reason" in serializer.errors

    def test_whitespace_only_reason_is_rejected(self):
        serializer = RejectPostSerializer(data={"reason": "   \t\n"})
        assert not serializer.is_valid()
        assert "reason" in serializer.errors

    def test_reason_over_2000_is_rejected(self):
        serializer = RejectPostSerializer(data={"reason": "a" * 2001})
        assert not serializer.is_valid()
        assert "reason" in serializer.errors

    def test_reason_at_2000_is_accepted(self):
        serializer = RejectPostSerializer(data={"reason": "a" * 2000})
        assert serializer.is_valid(), serializer.errors


# ==================================================================
# RequestChangesSerializer
# ==================================================================
class TestRequestChangesSerializer:
    def test_valid_note(self):
        serializer = RequestChangesSerializer(data={"note": "tighten intro"})
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["note"] == "tighten intro"

    def test_note_is_trimmed(self):
        serializer = RequestChangesSerializer(data={"note": "  tighten  "})
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["note"] == "tighten"

    def test_missing_note_is_rejected(self):
        serializer = RequestChangesSerializer(data={})
        assert not serializer.is_valid()
        assert "note" in serializer.errors

    def test_empty_note_is_rejected(self):
        serializer = RequestChangesSerializer(data={"note": ""})
        assert not serializer.is_valid()
        assert "note" in serializer.errors

    def test_whitespace_only_note_is_rejected(self):
        serializer = RequestChangesSerializer(data={"note": "   "})
        assert not serializer.is_valid()
        assert "note" in serializer.errors

    def test_note_over_2000_is_rejected(self):
        serializer = RequestChangesSerializer(data={"note": "a" * 2001})
        assert not serializer.is_valid()
        assert "note" in serializer.errors


# ==================================================================
# UnpublishPostSerializer
# ==================================================================
class TestUnpublishPostSerializer:
    def test_reason_is_optional(self):
        serializer = UnpublishPostSerializer(data={})
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["reason"] == ""

    def test_explicit_empty_reason_is_accepted(self):
        serializer = UnpublishPostSerializer(data={"reason": ""})
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["reason"] == ""

    def test_reason_is_trimmed(self):
        serializer = UnpublishPostSerializer(data={"reason": "  reason  "})
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["reason"] == "reason"

    def test_reason_over_2000_is_rejected(self):
        serializer = UnpublishPostSerializer(data={"reason": "a" * 2001})
        assert not serializer.is_valid()
        assert "reason" in serializer.errors


# ==================================================================
# FeaturedReorderItemSerializer
# ==================================================================
class TestFeaturedReorderItemSerializer:
    def test_valid_item(self):
        serializer = FeaturedReorderItemSerializer(data={"id": 1, "order": 0})
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data == {"id": 1, "order": 0}

    def test_order_must_be_non_negative(self):
        serializer = FeaturedReorderItemSerializer(data={"id": 1, "order": -1})
        assert not serializer.is_valid()
        assert "order" in serializer.errors

    def test_missing_id_is_rejected(self):
        serializer = FeaturedReorderItemSerializer(data={"order": 0})
        assert not serializer.is_valid()
        assert "id" in serializer.errors

    def test_missing_order_is_rejected(self):
        serializer = FeaturedReorderItemSerializer(data={"id": 1})
        assert not serializer.is_valid()
        assert "order" in serializer.errors


# ==================================================================
# FeaturedReorderSerializer
# ==================================================================
class TestFeaturedReorderSerializer:
    def test_valid_payload(self):
        serializer = FeaturedReorderSerializer(
            data={
                "items": [
                    {"id": 1, "order": 0},
                    {"id": 2, "order": 1},
                ]
            }
        )
        assert serializer.is_valid(), serializer.errors
        assert len(serializer.validated_data["items"]) == 2

    def test_empty_items_is_rejected(self):
        serializer = FeaturedReorderSerializer(data={"items": []})
        assert not serializer.is_valid()
        assert "items" in serializer.errors

    def test_missing_items_is_rejected(self):
        serializer = FeaturedReorderSerializer(data={})
        assert not serializer.is_valid()
        assert "items" in serializer.errors

    def test_duplicate_ids_are_rejected(self):
        serializer = FeaturedReorderSerializer(
            data={
                "items": [
                    {"id": 1, "order": 0},
                    {"id": 1, "order": 1},
                ]
            }
        )
        assert not serializer.is_valid()
        assert "items" in serializer.errors

    def test_nested_item_errors_are_reported(self):
        serializer = FeaturedReorderSerializer(data={"items": [{"id": 1, "order": -5}]})
        assert not serializer.is_valid()
        assert "items" in serializer.errors


# ==================================================================
# TagMergeSerializer
# ==================================================================
class TestTagMergeSerializer:
    def test_valid_payload(self):
        serializer = TagMergeSerializer(data={"source_ids": [1, 2], "target_id": 3})
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["source_ids"] == [1, 2]
        assert serializer.validated_data["target_id"] == 3

    def test_empty_source_ids_is_rejected(self):
        serializer = TagMergeSerializer(data={"source_ids": [], "target_id": 3})
        assert not serializer.is_valid()
        assert "source_ids" in serializer.errors

    def test_missing_source_ids_is_rejected(self):
        serializer = TagMergeSerializer(data={"target_id": 3})
        assert not serializer.is_valid()
        assert "source_ids" in serializer.errors

    def test_missing_target_id_is_rejected(self):
        serializer = TagMergeSerializer(data={"source_ids": [1]})
        assert not serializer.is_valid()
        assert "target_id" in serializer.errors

    def test_target_in_sources_is_rejected(self):
        serializer = TagMergeSerializer(data={"source_ids": [1, 2, 3], "target_id": 3})
        assert not serializer.is_valid()

    def test_non_integer_source_id_is_rejected(self):
        serializer = TagMergeSerializer(data={"source_ids": [1, "abc"], "target_id": 3})
        assert not serializer.is_valid()
        assert "source_ids" in serializer.errors


# ==================================================================
# CategoryWriteSerializer
# ==================================================================
@pytest.mark.django_db
class TestCategoryWriteSerializer:
    def test_creates_category_with_name_only(self):
        serializer = CategoryWriteSerializer(data={"name": "Testing"})
        assert serializer.is_valid(), serializer.errors
        category = serializer.save()

        assert category.name == "Testing"
        # Model save() regenerates the slug when blank.
        assert category.slug == "testing"

    def test_blank_slug_is_regenerated_by_model(self):
        serializer = CategoryWriteSerializer(
            data={"name": "Another Category", "slug": ""}
        )
        assert serializer.is_valid(), serializer.errors
        category = serializer.save()

        assert category.slug == "another-category"

    def test_explicit_slug_is_preserved(self):
        serializer = CategoryWriteSerializer(
            data={"name": "Named", "slug": "custom-slug"}
        )
        assert serializer.is_valid(), serializer.errors
        category = serializer.save()

        assert category.slug == "custom-slug"

    def test_name_is_required(self):
        serializer = CategoryWriteSerializer(data={})
        assert not serializer.is_valid()
        assert "name" in serializer.errors

    def test_updates_existing_category(self, test_category):
        serializer = CategoryWriteSerializer(
            instance=test_category,
            data={"name": "Updated Name"},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        category = serializer.save()

        assert category.name == "Updated Name"
        # Existing slug is preserved because it is not blank.
        assert category.slug == test_category.slug


# ==================================================================
# TagWriteSerializer
# ==================================================================
@pytest.mark.django_db
class TestTagWriteSerializer:
    def test_creates_tag_with_name_only(self):
        serializer = TagWriteSerializer(data={"name": "New Tag"})
        assert serializer.is_valid(), serializer.errors
        tag = serializer.save()

        assert tag.name == "New Tag"
        assert tag.slug == "new-tag"

    def test_blank_slug_is_regenerated_by_model(self):
        serializer = TagWriteSerializer(data={"name": "Another Tag", "slug": ""})
        assert serializer.is_valid(), serializer.errors
        tag = serializer.save()

        assert tag.slug == "another-tag"

    def test_explicit_slug_is_preserved(self):
        serializer = TagWriteSerializer(data={"name": "Named", "slug": "custom"})
        assert serializer.is_valid(), serializer.errors
        tag = serializer.save()

        assert tag.slug == "custom"

    def test_name_is_required(self):
        serializer = TagWriteSerializer(data={})
        assert not serializer.is_valid()
        assert "name" in serializer.errors

    def test_updates_existing_tag(self, test_tag):
        serializer = TagWriteSerializer(
            instance=test_tag,
            data={"name": "Updated"},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        tag = serializer.save()

        assert tag.name == "Updated"
