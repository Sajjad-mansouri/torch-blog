"""
Behavioral tests for accounts.api.serializers.

Scope: every serializer that does not require a Post/Category/Tag
instance to be meaningful. Serializers tied to blog models
(AuthorProfileSerializer) are covered in a later batch, once
Post factories are in place.

These tests exercise real validation and real database writes.
They do not assert on Django internals and do not mock the
serializer logic under test.
"""

import pytest
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.api.serializers import (
    AuthorBriefSerializer,
    AuthorDetailSerializer,
    AvatarUploadSerializer,
    ChangePasswordSerializer,
    EmailVerificationConfirmSerializer,
    EmailVerificationResendSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    SocialLinkSerializer,
    UserProfileSerializer,
)
from accounts.models import SocialLink, User


# ==================================================================
# UserProfileSerializer
# ==================================================================
@pytest.mark.django_db
class TestUserProfileSerializer:
    def test_serializes_expected_read_only_fields(self, test_user, api_request):
        data = UserProfileSerializer(test_user, context={"request": api_request}).data

        assert data["id"] == test_user.pk
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email
        assert data["role"] == User.Role.READER
        assert data["role_display"] == "Reader"
        assert data["is_email_verified"] is False

    def test_role_is_read_only(self, test_user):
        serializer = UserProfileSerializer(
            instance=test_user,
            data={"role": User.Role.EDITOR},
            partial=True,
        )
        assert serializer.is_valid()
        serializer.save()

        test_user.refresh_from_db()
        assert test_user.role == User.Role.READER

    def test_username_is_read_only(self, test_user):
        serializer = UserProfileSerializer(
            instance=test_user,
            data={"username": "hacked"},
            partial=True,
        )
        assert serializer.is_valid()
        serializer.save()

        test_user.refresh_from_db()
        assert test_user.username != "hacked"

    def test_is_email_verified_is_read_only(self, test_user):
        serializer = UserProfileSerializer(
            instance=test_user,
            data={"is_email_verified": True},
            partial=True,
        )
        assert serializer.is_valid()
        serializer.save()

        test_user.refresh_from_db()
        assert test_user.is_email_verified is False

    def test_validate_email_rejects_another_users_email(self, test_user, test_author):
        serializer = UserProfileSerializer(
            instance=test_user,
            data={"email": test_author.email},
            partial=True,
        )
        assert not serializer.is_valid()
        assert "email" in serializer.errors

    def test_validate_email_allows_own_email(self, test_user):
        serializer = UserProfileSerializer(
            instance=test_user,
            data={"email": test_user.email},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors

    def test_validate_email_lowercases_and_strips(self, test_user):
        serializer = UserProfileSerializer(
            instance=test_user,
            data={"email": "  NewAddress@Example.COM  "},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["email"] == "newaddress@example.com"

    def test_validate_bio_strips_whitespace(self, test_user):
        serializer = UserProfileSerializer(
            instance=test_user,
            data={"bio": "   Hello there   "},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["bio"] == "Hello there"

    def test_validate_website_strips_whitespace(self, test_user):
        serializer = UserProfileSerializer(
            instance=test_user,
            data={"website": "   https://example.com   "},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["website"] == "https://example.com"

    def test_avatar_url_uses_request_when_provided(self, test_user, api_request):
        data = UserProfileSerializer(test_user, context={"request": api_request}).data

        # Fallback path in the model is relative; the serializer
        # makes it absolute when a request is available.
        assert data["avatar_url"].startswith("http://testserver/")


# ==================================================================
# AvatarUploadSerializer
# ==================================================================
@pytest.mark.django_db
class TestAvatarUploadSerializer:
    def test_accepts_small_png(self, test_image):
        serializer = AvatarUploadSerializer(data={"avatar": test_image})
        assert serializer.is_valid(), serializer.errors

    def test_rejects_oversized_file(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        big = SimpleUploadedFile(
            "big.png", b"x" * (2 * 1024 * 1024 + 1), content_type="image/png"
        )
        serializer = AvatarUploadSerializer(data={"avatar": big})
        assert not serializer.is_valid()
        assert "avatar" in serializer.errors

    def test_rejects_disallowed_extension(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        gif = SimpleUploadedFile("nope.gif", b"GIF89a", content_type="image/gif")
        serializer = AvatarUploadSerializer(data={"avatar": gif})
        assert not serializer.is_valid()
        assert "avatar" in serializer.errors

    def test_accepts_real_jpeg(self, media_root):
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (10, 10), color="red").save(buf, format="JPEG")
        buf.seek(0)
        jpg = SimpleUploadedFile("photo.JPEG", buf.read(), content_type="image/jpeg")
        serializer = AvatarUploadSerializer(data={"avatar": jpg})
        assert serializer.is_valid(), serializer.errors

    def test_rejects_corrupted_content_even_with_image_extension(self, media_root):
        from django.core.files.uploadedfile import SimpleUploadedFile

        # A file named .jpg whose bytes are not a real JPEG.
        fake = SimpleUploadedFile(
            "fake.jpg", b"not-actually-a-jpeg", content_type="image/jpeg"
        )
        serializer = AvatarUploadSerializer(data={"avatar": fake})
        assert not serializer.is_valid()
        assert "avatar" in serializer.errors


# ==================================================================
# ChangePasswordSerializer
# ==================================================================
@pytest.mark.django_db
class TestChangePasswordSerializer:
    def _make_request_with_user(self, user):
        from django.test import RequestFactory

        request = RequestFactory().post("/")
        request.user = user
        return request

    def test_happy_path_changes_password(self, test_user):
        request = self._make_request_with_user(test_user)
        serializer = ChangePasswordSerializer(
            data={
                "old_password": "testpass123",
                "new_password": "newpass456!",
                "new_password_confirm": "newpass456!",
            },
            context={"request": request},
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()

        test_user.refresh_from_db()
        assert test_user.check_password("newpass456!")

    def test_wrong_old_password_rejected(self, test_user):
        request = self._make_request_with_user(test_user)
        serializer = ChangePasswordSerializer(
            data={
                "old_password": "wrong",
                "new_password": "newpass456!",
                "new_password_confirm": "newpass456!",
            },
            context={"request": request},
        )
        assert not serializer.is_valid()
        assert "old_password" in serializer.errors

    def test_mismatched_confirm_rejected(self, test_user):
        request = self._make_request_with_user(test_user)
        serializer = ChangePasswordSerializer(
            data={
                "old_password": "testpass123",
                "new_password": "newpass456!",
                "new_password_confirm": "different!",
            },
            context={"request": request},
        )
        assert not serializer.is_valid()
        assert "new_password_confirm" in serializer.errors

    def test_weak_new_password_rejected(self, test_user):
        request = self._make_request_with_user(test_user)
        serializer = ChangePasswordSerializer(
            data={
                "old_password": "testpass123",
                "new_password": "123",
                "new_password_confirm": "123",
            },
            context={"request": request},
        )
        assert not serializer.is_valid()
        assert "new_password" in serializer.errors


# ==================================================================
# LoginSerializer
# ==================================================================
@pytest.mark.django_db
class TestLoginSerializer:
    def test_login_by_username(self, test_user, api_request):
        serializer = LoginSerializer(
            data={"username": test_user.username, "password": "testpass123"},
            context={"request": api_request},
        )
        assert serializer.is_valid(), serializer.errors

        payload = serializer.to_representation(serializer)
        assert "access" in payload
        assert "refresh" in payload
        assert payload["user"]["username"] == test_user.username

    def test_login_by_email(self, test_user, api_request):
        serializer = LoginSerializer(
            data={"username": test_user.email, "password": "testpass123"},
            context={"request": api_request},
        )
        assert serializer.is_valid(), serializer.errors

    def test_invalid_credentials_rejected(self, test_user, api_request):
        serializer = LoginSerializer(
            data={"username": test_user.username, "password": "wrong"},
            context={"request": api_request},
        )
        assert not serializer.is_valid()

    def test_inactive_user_rejected(self, api_request):
        inactive = User.objects.create_user(
            username="inactive",
            email="inactive@example.com",
            password="testpass123",
            is_active=False,
        )
        serializer = LoginSerializer(
            data={"username": inactive.username, "password": "testpass123"},
            context={"request": api_request},
        )
        assert not serializer.is_valid()


# ==================================================================
# LogoutSerializer
# ==================================================================
@pytest.mark.django_db
class TestLogoutSerializer:
    def test_valid_refresh_token_is_blacklisted(self, test_user):
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(test_user)
        serializer = LogoutSerializer(data={"refresh": str(refresh)})
        assert serializer.is_valid(), serializer.errors
        serializer.save()

        # A blacklisted token can no longer be used.
        from rest_framework_simplejwt.exceptions import TokenError

        with pytest.raises(TokenError):
            RefreshToken(str(refresh)).check_blacklist()

    def test_invalid_token_does_not_raise(self):
        # LogoutSerializer swallows TokenError deliberately.
        serializer = LogoutSerializer(data={"refresh": "not-a-token"})
        assert serializer.is_valid()
        serializer.save()  # must not raise


# ==================================================================
# RegisterSerializer
# ==================================================================
@pytest.mark.django_db
class TestRegisterSerializer:
    def _payload(self, **overrides):
        payload = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "strongpass123!",
            "password_confirm": "strongpass123!",
        }
        payload.update(overrides)
        return payload

    def test_creates_reader_user_inactive_and_unverified(self, api_request):
        serializer = RegisterSerializer(
            data=self._payload(),
            context={"request": api_request},
        )
        assert serializer.is_valid(), serializer.errors
        user = serializer.save()

        assert user.role == User.Role.READER
        assert user.is_active is False
        assert user.is_email_verified is False
        assert user.check_password("strongpass123!")

    def test_sends_verification_email(self, api_request):
        serializer = RegisterSerializer(
            data=self._payload(),
            context={"request": api_request},
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()

        assert len(mail.outbox) == 1
        sent = mail.outbox[0]
        assert sent.to == ["newuser@example.com"]
        assert "verify" in sent.subject.lower()

    def test_duplicate_username_rejected(self, test_user, api_request):
        serializer = RegisterSerializer(
            data=self._payload(username=test_user.username),
            context={"request": api_request},
        )
        assert not serializer.is_valid()
        assert "username" in serializer.errors

    def test_duplicate_email_rejected(self, test_user, api_request):
        serializer = RegisterSerializer(
            data=self._payload(email=test_user.email),
            context={"request": api_request},
        )
        assert not serializer.is_valid()
        assert "email" in serializer.errors

    def test_mismatched_password_confirm_rejected(self, api_request):
        serializer = RegisterSerializer(
            data=self._payload(password_confirm="different!"),
            context={"request": api_request},
        )
        assert not serializer.is_valid()
        assert "password_confirm" in serializer.errors

    @pytest.mark.parametrize(
        "bad_username",
        ["ab", "x" * 31, "has space", "has/slash", "has@symbol"],
    )
    def test_invalid_usernames_rejected(self, bad_username, api_request):
        serializer = RegisterSerializer(
            data=self._payload(username=bad_username),
            context={"request": api_request},
        )
        assert not serializer.is_valid()
        assert "username" in serializer.errors

    def test_role_cannot_be_escalated_via_registration(self, api_request):
        serializer = RegisterSerializer(
            data=self._payload(role=User.Role.EDITOR),
            context={"request": api_request},
        )
        assert serializer.is_valid(), serializer.errors
        user = serializer.save()

        assert user.role == User.Role.READER


# ==================================================================
# PasswordResetRequestSerializer
# ==================================================================
@pytest.mark.django_db
class TestPasswordResetRequestSerializer:
    def test_sends_email_for_active_user(self, test_user, api_request):
        serializer = PasswordResetRequestSerializer(
            data={"email": test_user.email},
            context={"request": api_request},
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()

        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [test_user.email]

    def test_silently_ignores_unknown_email(self, api_request):
        serializer = PasswordResetRequestSerializer(
            data={"email": "nobody@example.com"},
            context={"request": api_request},
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()

        assert len(mail.outbox) == 0

    def test_lowercases_email_on_validation(self):
        serializer = PasswordResetRequestSerializer(
            data={"email": "  USER@Example.COM  "},
        )
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["email"] == "user@example.com"

    def test_inactive_user_does_not_receive_email(self, api_request):
        User.objects.create_user(
            username="inactive",
            email="inactive@example.com",
            password="x",
            is_active=False,
        )
        serializer = PasswordResetRequestSerializer(
            data={"email": "inactive@example.com"},
            context={"request": api_request},
        )
        assert serializer.is_valid()
        serializer.save()

        assert len(mail.outbox) == 0


# ==================================================================
# PasswordResetConfirmSerializer
# ==================================================================
@pytest.mark.django_db
class TestPasswordResetConfirmSerializer:
    def _valid_token_payload(self, user):
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        return {
            "uidb64": uidb64,
            "token": token,
            "password": "brandnewpass456!",
            "password_confirm": "brandnewpass456!",
        }

    def test_happy_path_changes_password(self, test_user):
        serializer = PasswordResetConfirmSerializer(
            data=self._valid_token_payload(test_user)
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()

        test_user.refresh_from_db()
        assert test_user.check_password("brandnewpass456!")

    def test_invalid_uidb64_rejected(self):
        serializer = PasswordResetConfirmSerializer(
            data={
                "uidb64": "not-base64-$$$",
                "token": "whatever",
                "password": "brandnewpass456!",
                "password_confirm": "brandnewpass456!",
            }
        )
        assert not serializer.is_valid()
        assert "token" in serializer.errors

    def test_invalid_token_rejected(self, test_user):
        serializer = PasswordResetConfirmSerializer(
            data={
                "uidb64": urlsafe_base64_encode(force_bytes(test_user.pk)),
                "token": "not-a-real-token",
                "password": "brandnewpass456!",
                "password_confirm": "brandnewpass456!",
            }
        )
        assert not serializer.is_valid()
        assert "token" in serializer.errors

    def test_password_mismatch_rejected(self, test_user):
        payload = self._valid_token_payload(test_user)
        payload["password_confirm"] = "different!"
        serializer = PasswordResetConfirmSerializer(data=payload)

        assert not serializer.is_valid()
        assert "password_confirm" in serializer.errors


# ==================================================================
# EmailVerificationConfirmSerializer
# ==================================================================
@pytest.mark.django_db
class TestEmailVerificationConfirmSerializer:
    def _valid_token_payload(self, user):
        return {
            "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": default_token_generator.make_token(user),
        }

    def test_happy_path_flips_both_flags(self, api_request):
        user = User.objects.create_user(
            username="unverified",
            email="unverified@example.com",
            password="x",
            is_active=False,
            is_email_verified=False,
        )
        serializer = EmailVerificationConfirmSerializer(
            data=self._valid_token_payload(user)
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()

        user.refresh_from_db()
        assert user.is_active is True
        assert user.is_email_verified is True

    def test_invalid_token_rejected(self, test_user):
        serializer = EmailVerificationConfirmSerializer(
            data={
                "uidb64": urlsafe_base64_encode(force_bytes(test_user.pk)),
                "token": "not-a-real-token",
            }
        )
        assert not serializer.is_valid()
        assert "token" in serializer.errors

    def test_valid_token_is_idempotent(self, api_request):
        user = User.objects.create_user(
            username="verifying",
            email="verifying@example.com",
            password="x",
            is_active=False,
            is_email_verified=False,
        )
        payload = self._valid_token_payload(user)

        first = EmailVerificationConfirmSerializer(data=payload)
        assert first.is_valid(), first.errors
        first.save()

        # Same valid token a second time.
        second = EmailVerificationConfirmSerializer(data=payload)
        assert second.is_valid(), second.errors
        second.save()

        user.refresh_from_db()
        assert user.is_active is True
        assert user.is_email_verified is True


# ==================================================================
# EmailVerificationResendSerializer
# ==================================================================
@pytest.mark.django_db
class TestEmailVerificationResendSerializer:
    def test_sends_email_for_unverified_inactive_user(self, api_request):
        user = User.objects.create_user(
            username="unverified",
            email="unverified@example.com",
            password="x",
            is_active=False,
            is_email_verified=False,
        )
        serializer = EmailVerificationResendSerializer(
            data={"email": user.email},
            context={"request": api_request},
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()

        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [user.email]

    def test_does_nothing_for_verified_user(self, api_request):
        user = User.objects.create_user(
            username="verified",
            email="verified@example.com",
            password="x",
            is_active=True,
            is_email_verified=True,
        )
        serializer = EmailVerificationResendSerializer(
            data={"email": user.email},
            context={"request": api_request},
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()

        assert len(mail.outbox) == 0

    def test_does_nothing_for_unknown_email(self, api_request):
        serializer = EmailVerificationResendSerializer(
            data={"email": "nobody@example.com"},
            context={"request": api_request},
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()

        assert len(mail.outbox) == 0


# ==================================================================
# AuthorBriefSerializer / AuthorDetailSerializer
# ==================================================================
@pytest.mark.django_db
class TestAuthorBriefSerializer:
    def test_fields_present_and_correct(self, test_author, api_request):
        data = AuthorBriefSerializer(test_author, context={"request": api_request}).data

        assert data["id"] == test_author.pk
        assert data["username"] == test_author.username
        assert data["display_name"] == test_author.display_name
        assert data["avatar_url"].startswith("http://testserver/")

    def test_avatar_url_without_request_is_relative(self, test_author):
        data = AuthorBriefSerializer(test_author).data

        assert data["avatar_url"] == "/static/img/default-avatar.jpg"


@pytest.mark.django_db
class TestAuthorDetailSerializer:
    def test_includes_bio_website_and_social_links(self, test_author, api_request):
        SocialLink.objects.create(
            user=test_author,
            platform=SocialLink.Platform.GITHUB,
            url="https://github.com/example",
        )
        data = AuthorDetailSerializer(
            test_author, context={"request": api_request}
        ).data

        assert "bio" in data
        assert "website" in data
        assert len(data["social_links"]) == 1
        assert data["social_links"][0]["platform"] == "github"
        assert data["social_links"][0]["platform_display"] == "GitHub"


# ==================================================================
# SocialLinkSerializer
# ==================================================================
@pytest.mark.django_db
class TestSocialLinkSerializer:
    def test_serializes_platform_and_display(self, test_user):
        link = SocialLink.objects.create(
            user=test_user,
            platform=SocialLink.Platform.STACKOVERFLOW,
            url="https://stackoverflow.com/users/1",
            username="test_user",
            order=3,
        )
        data = SocialLinkSerializer(link).data

        assert data["id"] == link.pk
        assert data["platform"] == "stackoverflow"
        assert data["platform_display"] == "Stack Overflow"
        assert data["url"] == "https://stackoverflow.com/users/1"
        assert data["username"] == "test_user"
        assert data["order"] == 3
