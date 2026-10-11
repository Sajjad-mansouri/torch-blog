"""
API tests for EditorSiteSettingsView and EditorActivityLogView.
"""

import pytest

from core.models import ActivityLog, SiteSettings


# ==================================================================
# EditorSiteSettingsView
# ==================================================================
@pytest.mark.django_db
class TestEditorSiteSettingsView:
    def test_requires_editor(self, auth_client):
        response = auth_client.get("/api/v1/editor/settings/")
        assert response.status_code == 403

    def test_get_returns_settings(self, editor_client):
        response = editor_client.get("/api/v1/editor/settings/")
        assert response.status_code == 200
        assert "site_title" in response.data

    def test_patch_updates_settings(self, editor_client):
        response = editor_client.patch(
            "/api/v1/editor/settings/",
            {"site_title": "Updated Title"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["site_title"] == "Updated Title"

        # Settings are a singleton (pk=1).
        settings = SiteSettings.objects.get(pk=1)
        assert settings.site_title == "Updated Title"

    def test_patch_persists_across_requests(self, editor_client):
        editor_client.patch(
            "/api/v1/editor/settings/",
            {"tagline": "A tagline"},
            format="json",
        )
        response = editor_client.get("/api/v1/editor/settings/")
        assert response.data["tagline"] == "A tagline"


# ==================================================================
# EditorActivityLogView
# ==================================================================
@pytest.mark.django_db
class TestEditorActivityLogView:
    def test_requires_editor(self, auth_client):
        response = auth_client.get("/api/v1/editor/activity-log/")
        assert response.status_code == 403

    def test_lists_activity_log(self, editor_client, test_user):
        log = ActivityLog.objects.create(
            user=test_user,
            action=ActivityLog.Action.POST_CREATED,
            description="created a post",
        )

        response = editor_client.get("/api/v1/editor/activity-log/")
        ids = [entry["id"] for entry in response.data["results"]]
        assert log.pk in ids

    def test_filter_by_action(self, editor_client, test_user):
        log1 = ActivityLog.objects.create(
            user=test_user,
            action=ActivityLog.Action.POST_CREATED,
        )
        log2 = ActivityLog.objects.create(
            user=test_user,
            action=ActivityLog.Action.POST_DELETED,
        )

        response = editor_client.get(
            "/api/v1/editor/activity-log/",
            {"action": "post_created"},
        )
        ids = [entry["id"] for entry in response.data["results"]]
        assert log1.pk in ids
        assert log2.pk not in ids

    def test_filter_by_user(self, editor_client, test_user, test_author):
        log1 = ActivityLog.objects.create(
            user=test_user,
            action=ActivityLog.Action.POST_CREATED,
        )
        log2 = ActivityLog.objects.create(
            user=test_author,
            action=ActivityLog.Action.POST_CREATED,
        )

        response = editor_client.get(
            "/api/v1/editor/activity-log/",
            {"user": test_user.username},
        )
        ids = [entry["id"] for entry in response.data["results"]]
        assert log1.pk in ids
        assert log2.pk not in ids

    def test_filter_by_target_id(self, editor_client, test_user):
        log1 = ActivityLog.objects.create(
            user=test_user,
            action=ActivityLog.Action.POST_CREATED,
            target_type="post",
            target_id=42,
        )
        ActivityLog.objects.create(
            user=test_user,
            action=ActivityLog.Action.POST_CREATED,
            target_type="post",
            target_id=99,
        )

        response = editor_client.get(
            "/api/v1/editor/activity-log/",
            {"target_id": "42"},
        )
        ids = [entry["id"] for entry in response.data["results"]]
        assert log1.pk in ids

    def test_invalid_target_id_returns_400(self, editor_client):
        response = editor_client.get(
            "/api/v1/editor/activity-log/",
            {"target_id": "not-a-number"},
        )
        assert response.status_code == 400

    def test_null_user_serializes_as_none(self, editor_client):
        """
        ActivityLog.user is nullable (on_delete=SET_NULL). When it is
        None, the nested ActivityLogUserSerializer is called with
        instance=None, and DRF serializes it as None (not {}).
        """
        log = ActivityLog.objects.create(
            user=None,
            action=ActivityLog.Action.POST_CREATED,
        )

        response = editor_client.get("/api/v1/editor/activity-log/")
        entry = next(e for e in response.data["results"] if e["id"] == log.pk)
        assert entry["user"] is None
