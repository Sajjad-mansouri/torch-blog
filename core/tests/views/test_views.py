"""
API tests for core views: LandingView and ContactView.
"""

import pytest
from django.core import mail

from core.models import (
    ContactMessage,
    SocialLink,
    TechCategory,
)


# ==================================================================
# LandingView
# ==================================================================
@pytest.mark.django_db
class TestLandingView:
    def test_anonymous_access(self, api_client):
        response = api_client.get("/api/v1/landing/")
        assert response.status_code == 200

    def test_response_has_all_sections(self, api_client):
        response = api_client.get("/api/v1/landing/")

        for key in (
            "project",
            "tech_stack",
            "features",
            "api_endpoints",
            "screenshots",
            "roadmap",
            "stats",
            "social_links",
        ):
            assert key in response.data

    def test_project_is_serialized_dict_not_model(self, api_client):
        api_client.get("/api/v1/landing/")
        response = api_client.get("/api/v1/landing/")

        assert isinstance(response.data["project"], dict)

    def test_repeated_calls_return_same_data(self, api_client):
        first = api_client.get("/api/v1/landing/").data
        second = api_client.get("/api/v1/landing/").data

        assert first["project"]["site_title"] == second["project"]["site_title"]

    def test_includes_active_tech_category(self, api_client):
        TechCategory.objects.create(name="Backend", slug="backend", is_active=True)
        response = api_client.get("/api/v1/landing/")
        slugs = [c["slug"] for c in response.data["tech_stack"]]

        assert "backend" in slugs

    def test_excludes_inactive_tech_category(self, api_client):
        TechCategory.objects.create(name="Old", slug="old", is_active=False)
        response = api_client.get("/api/v1/landing/")
        slugs = [c["slug"] for c in response.data["tech_stack"]]

        assert "old" not in slugs

    def test_includes_social_links_with_show_in_landing(self, api_client):
        SocialLink.objects.create(
            platform="github",
            url="https://github.com/x",
            is_active=True,
            show_in_landing=True,
        )
        response = api_client.get("/api/v1/landing/")
        platforms = [s["platform"] for s in response.data["social_links"]]

        assert "github" in platforms


# ==================================================================
# ContactView
# ==================================================================
@pytest.mark.django_db
class TestContactView:
    def _payload(self, **overrides):
        payload = {
            "name": "Alice",
            "email": "alice@example.com",
            "subject": "Hello",
            "message": "This is a sufficiently long message.",
        }
        payload.update(overrides)
        return payload

    def test_valid_submission_returns_201(self, api_client):
        response = api_client.post("/api/v1/contact/", self._payload(), format="json")
        assert response.status_code == 201

    def test_valid_submission_creates_contact_message(self, api_client):
        api_client.post("/api/v1/contact/", self._payload(), format="json")

        assert ContactMessage.objects.count() == 1
        m = ContactMessage.objects.get()
        assert m.name == "Alice"
        assert m.email == "alice@example.com"

    def test_valid_submission_sends_email(self, api_client):
        api_client.post("/api/v1/contact/", self._payload(), format="json")

        assert len(mail.outbox) == 1
        sent = mail.outbox[0]
        assert sent.to == ["alice@example.com"]

    def test_short_name_returns_400(self, api_client):
        response = api_client.post(
            "/api/v1/contact/", self._payload(name="A"), format="json"
        )
        assert response.status_code == 400
        assert "name" in response.data

    def test_short_message_returns_400(self, api_client):
        response = api_client.post(
            "/api/v1/contact/", self._payload(message="short"), format="json"
        )
        assert response.status_code == 400
        assert "message" in response.data

    def test_missing_email_returns_400(self, api_client):
        payload = self._payload()
        payload.pop("email")
        response = api_client.post("/api/v1/contact/", payload, format="json")
        assert response.status_code == 400
        assert "email" in response.data

    def test_honeypot_filled_returns_201_but_skips_save(self, api_client):
        response = api_client.post(
            "/api/v1/contact/",
            self._payload(website="I am a bot"),
            format="json",
        )
        assert response.status_code == 201
        assert ContactMessage.objects.count() == 0

    def test_honeypot_filled_sends_no_email(self, api_client):
        api_client.post(
            "/api/v1/contact/",
            self._payload(website="I am a bot"),
            format="json",
        )
        assert len(mail.outbox) == 0

    def test_honeypot_blank_is_treated_as_real_submission(self, api_client):
        response = api_client.post(
            "/api/v1/contact/",
            self._payload(website=""),
            format="json",
        )
        assert response.status_code == 201
        assert ContactMessage.objects.count() == 1

    def test_stores_ip_and_user_agent(self, api_client):
        api_client.post("/api/v1/contact/", self._payload(), format="json")
        m = ContactMessage.objects.get()

        assert m.ip_address is not None
        assert m.user_agent is not None
