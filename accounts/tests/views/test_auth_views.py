"""
API tests for accounts.api.views_auth.

Every test goes through the real HTTP layer via DRF's APIClient.
Tests assert on status codes, response shape, and — most
importantly — the resulting database state. Emails are verified
through mail.outbox, which is what Django's locmem backend collects
when HOST_ASYNC_ABILITY=False (which is the case in this project).
"""

import pytest
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User


# ==================================================================
# Login
# ==================================================================
@pytest.mark.django_db
class TestLoginView:
    def test_login_with_username_returns_tokens_and_profile(
        self, api_client, test_user
    ):
        response = api_client.post(
            "/api/v1/auth/login/",
            {"username": test_user.username, "password": "testpass123"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        assert response.data["user"]["username"] == test_user.username

    def test_login_with_email_returns_tokens(self, api_client, test_user):
        response = api_client.post(
            "/api/v1/auth/login/",
            {"username": test_user.email, "password": "testpass123"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_login_with_wrong_password_returns_400(self, api_client, test_user):
        response = api_client.post(
            "/api/v1/auth/login/",
            {"username": test_user.username, "password": "wrong"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_with_inactive_user_returns_400(self, api_client):
        inactive = User.objects.create_user(
            username="inactive",
            email="inactive@example.com",
            password="testpass123",
            is_active=False,
        )
        response = api_client.post(
            "/api/v1/auth/login/",
            {"username": inactive.username, "password": "testpass123"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ==================================================================
# Logout
# ==================================================================
@pytest.mark.django_db
class TestLogoutView:
    def test_logout_blacklists_refresh(self, auth_client, test_user):
        refresh = RefreshToken.for_user(test_user)

        response = auth_client.post(
            "/api/v1/auth/logout/",
            {"refresh": str(refresh)},
            format="json",
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        from rest_framework_simplejwt.exceptions import TokenError

        with pytest.raises(TokenError):
            RefreshToken(str(refresh)).check_blacklist()

    def test_logout_with_invalid_refresh_still_returns_204(self, auth_client):
        response = auth_client.post(
            "/api/v1/auth/logout/",
            {"refresh": "not-a-real-token"},
            format="json",
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_logout_requires_authentication(self, api_client):
        response = api_client.post(
            "/api/v1/auth/logout/",
            {"refresh": "anything"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ==================================================================
# Me
# ==================================================================
@pytest.mark.django_db
class TestMeView:
    def test_get_me_returns_profile(self, auth_client, test_user):
        response = auth_client.get("/api/v1/auth/me/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == test_user.username
        assert response.data["role"] == User.Role.READER

    def test_get_me_requires_authentication(self, api_client):
        response = api_client.get("/api/v1/auth/me/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_patch_me_updates_bio_and_website(self, auth_client, test_user):
        response = auth_client.patch(
            "/api/v1/auth/me/",
            {"bio": "  New bio  ", "website": "https://example.com"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        test_user.refresh_from_db()
        assert test_user.bio == "New bio"
        assert test_user.website == "https://example.com"

    def test_patch_me_cannot_change_role(self, auth_client, test_user):
        response = auth_client.patch(
            "/api/v1/auth/me/",
            {"role": User.Role.EDITOR},
            format="json",
        )

        # role is read-only; DRF accepts the request but ignores the field.
        assert response.status_code == status.HTTP_200_OK
        test_user.refresh_from_db()
        assert test_user.role == User.Role.READER

    def test_patch_me_cannot_change_username(self, auth_client, test_user):
        response = auth_client.patch(
            "/api/v1/auth/me/",
            {"username": "hacker"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        test_user.refresh_from_db()
        assert test_user.username != "hacker"

    def test_patch_me_cannot_set_is_email_verified(self, auth_client, test_user):
        response = auth_client.patch(
            "/api/v1/auth/me/",
            {"is_email_verified": True},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        test_user.refresh_from_db()
        assert test_user.is_email_verified is False

    def test_patch_me_rejects_another_users_email(
        self, auth_client, test_user, test_author
    ):
        response = auth_client.patch(
            "/api/v1/auth/me/",
            {"email": test_author.email},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data


# ==================================================================
# Avatar upload (dedicated endpoint)
# ==================================================================
@pytest.mark.django_db
class TestAvatarUploadView:
    def test_upload_valid_avatar_saves_and_returns_profile(
        self, auth_client, test_user, test_image, media_root
    ):
        response = auth_client.post(
            "/api/v1/auth/me/avatar/",
            {"avatar": test_image},
            format="multipart",
        )

        assert response.status_code == status.HTTP_200_OK
        test_user.refresh_from_db()
        assert test_user.avatar  # truthy file reference
        # File landed in the temporary MEDIA_ROOT
        assert (media_root / test_user.avatar.name).exists()

    def test_upload_rejects_oversized_file(self, auth_client, media_root):
        from django.core.files.uploadedfile import SimpleUploadedFile

        big = SimpleUploadedFile(
            "big.png",
            b"x" * (2 * 1024 * 1024 + 1),
            content_type="image/png",
        )
        response = auth_client.post(
            "/api/v1/auth/me/avatar/",
            {"avatar": big},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "avatar" in response.data

    def test_upload_rejects_disallowed_extension(self, auth_client, media_root):
        from django.core.files.uploadedfile import SimpleUploadedFile

        gif = SimpleUploadedFile("nope.gif", b"GIF89a", content_type="image/gif")
        response = auth_client.post(
            "/api/v1/auth/me/avatar/",
            {"avatar": gif},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "avatar" in response.data

    def test_upload_rejects_corrupted_content(self, auth_client, media_root):
        from django.core.files.uploadedfile import SimpleUploadedFile

        fake = SimpleUploadedFile(
            "fake.png",
            b"not-an-image",
            content_type="image/png",
        )
        response = auth_client.post(
            "/api/v1/auth/me/avatar/",
            {"avatar": fake},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_requires_authentication(self, api_client, media_root):
        from django.core.files.uploadedfile import SimpleUploadedFile

        png = SimpleUploadedFile("x.png", b"\x89PNG", content_type="image/png")
        response = api_client.post(
            "/api/v1/auth/me/avatar/",
            {"avatar": png},
            format="multipart",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ==================================================================
# Change password
# ==================================================================
@pytest.mark.django_db
class TestChangePasswordView:
    def test_change_password_succeeds(self, auth_client, test_user):
        response = auth_client.post(
            "/api/v1/auth/me/change-password/",
            {
                "old_password": "testpass123",
                "new_password": "brandnewpass456!",
                "new_password_confirm": "brandnewpass456!",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        test_user.refresh_from_db()
        assert test_user.check_password("brandnewpass456!")

    def test_wrong_old_password_returns_400(self, auth_client):
        response = auth_client.post(
            "/api/v1/auth/me/change-password/",
            {
                "old_password": "wrong",
                "new_password": "brandnewpass456!",
                "new_password_confirm": "brandnewpass456!",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_mismatched_confirm_returns_400(self, auth_client):
        response = auth_client.post(
            "/api/v1/auth/me/change-password/",
            {
                "old_password": "testpass123",
                "new_password": "brandnewpass456!",
                "new_password_confirm": "different!",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_requires_authentication(self, api_client):
        response = api_client.post(
            "/api/v1/auth/me/change-password/",
            {
                "old_password": "x",
                "new_password": "y",
                "new_password_confirm": "y",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ==================================================================
# Password reset — request
# ==================================================================
@pytest.mark.django_db
class TestPasswordResetRequestView:
    def test_valid_email_returns_200_and_sends_mail(self, api_client, test_user):
        response = api_client.post(
            "/api/v1/auth/password-reset/",
            {"email": test_user.email},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [test_user.email]

    def test_unknown_email_returns_200_without_mail(self, api_client):
        response = api_client.post(
            "/api/v1/auth/password-reset/",
            {"email": "nobody@example.com"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(mail.outbox) == 0


# ==================================================================
# Password reset — confirm
# ==================================================================
@pytest.mark.django_db
class TestPasswordResetConfirmView:
    def _payload(self, user):
        return {
            "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": default_token_generator.make_token(user),
            "password": "brandnewpass456!",
            "password_confirm": "brandnewpass456!",
        }

    def test_valid_token_changes_password(self, api_client, test_user):
        response = api_client.post(
            "/api/v1/auth/password-reset/confirm/",
            self._payload(test_user),
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        test_user.refresh_from_db()
        assert test_user.check_password("brandnewpass456!")

    def test_invalid_token_returns_400(self, api_client, test_user):
        payload = self._payload(test_user)
        payload["token"] = "not-a-real-token"

        response = api_client.post(
            "/api/v1/auth/password-reset/confirm/",
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ==================================================================
# Register
# ==================================================================
@pytest.mark.django_db
class TestRegisterView:
    def _payload(self, **overrides):
        payload = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "strongpass123!",
            "password_confirm": "strongpass123!",
        }
        payload.update(overrides)
        return payload

    def test_register_creates_inactive_unverified_reader(self, api_client):
        response = api_client.post(
            "/api/v1/auth/register/",
            self._payload(),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(username="newuser")
        assert user.role == User.Role.READER
        assert user.is_active is False
        assert user.is_email_verified is False

    def test_register_sends_verification_email(self, api_client):
        api_client.post(
            "/api/v1/auth/register/",
            self._payload(),
            format="json",
        )

        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["newuser@example.com"]

    def test_register_duplicate_email_returns_400(self, api_client, test_user):
        response = api_client.post(
            "/api/v1/auth/register/",
            self._payload(email=test_user.email),
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data

    def test_register_ignores_role_escalation(self, api_client):
        api_client.post(
            "/api/v1/auth/register/",
            self._payload(role=User.Role.EDITOR),
            format="json",
        )

        user = User.objects.get(username="newuser")
        assert user.role == User.Role.READER


# ==================================================================
# Verify email — confirm
# ==================================================================
@pytest.mark.django_db
class TestVerifyEmailConfirmView:
    def _payload(self, user):
        return {
            "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": default_token_generator.make_token(user),
        }

    def test_valid_token_flips_both_flags(self, api_client):
        user = User.objects.create_user(
            username="unverified",
            email="unverified@example.com",
            password="x",
            is_active=False,
            is_email_verified=False,
        )
        response = api_client.post(
            "/api/v1/auth/verify-email/confirm/",
            self._payload(user),
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.is_active is True
        assert user.is_email_verified is True

    def test_invalid_token_returns_400(self, api_client, test_user):
        response = api_client.post(
            "/api/v1/auth/verify-email/confirm/",
            {
                "uidb64": urlsafe_base64_encode(force_bytes(test_user.pk)),
                "token": "not-a-real-token",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ==================================================================
# Verify email — resend
# ==================================================================
@pytest.mark.django_db
class TestResendVerificationView:
    def test_unverified_inactive_user_receives_email(self, api_client):
        user = User.objects.create_user(
            username="unverified",
            email="unverified@example.com",
            password="x",
            is_active=False,
            is_email_verified=False,
        )
        response = api_client.post(
            "/api/v1/auth/verify-email/resend/",
            {"email": user.email},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [user.email]

    def test_verified_user_receives_no_email(self, api_client):
        user = User.objects.create_user(
            username="verified",
            email="verified@example.com",
            password="x",
            is_active=True,
            is_email_verified=True,
        )
        response = api_client.post(
            "/api/v1/auth/verify-email/resend/",
            {"email": user.email},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(mail.outbox) == 0

    def test_unknown_email_returns_200_without_mail(self, api_client):
        response = api_client.post(
            "/api/v1/auth/verify-email/resend/",
            {"email": "nobody@example.com"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(mail.outbox) == 0


# ==================================================================
# Resend verification — throttling
# ==================================================================
class TestResendVerificationThrottle:
    """
    Separate class so the throttle can be exercised with settings
    restored. The class-level override restores a dedicated scope
    for the resend view's own throttle.

    Not marked with django_db because we do not need the database
    for this test: the request is rejected by the throttle before
    reaching the serializer. If that changes, add @pytest.mark.django_db.
    """

    def test_exceeds_rate_limit_returns_429(self, api_client, settings):
        # Re-enable throttling for this test only.
        settings.REST_FRAMEWORK = {
            "DEFAULT_AUTHENTICATION_CLASSES": [
                "rest_framework_simplejwt.authentication.JWTAuthentication",
            ],
            "DEFAULT_THROTTLE_CLASSES": [],
            "DEFAULT_THROTTLE_RATES": {
                "resend_verification": "3/hour",
            },
            "DEFAULT_FILTER_BACKENDS": [],
            "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
        }

        # Clear the cache so throttle history doesn't leak between runs.
        from django.core.cache import cache

        cache.clear()

        url = "/api/v1/auth/verify-email/resend/"
        payload = {"email": "nobody@example.com"}

        # First 3 requests hit the throttle budget.
        for _ in range(3):
            response = api_client.post(url, payload, format="json")
            assert response.status_code == status.HTTP_200_OK

        # Fourth request trips the throttle.
        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

        cache.clear()
