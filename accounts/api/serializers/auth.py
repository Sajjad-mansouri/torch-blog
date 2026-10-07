from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import _unicode_ci_compare
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.tasks import send_email

User = get_user_model()


# ============================================================
# Profile (current user)
# ============================================================
class UserProfileSerializer(serializers.ModelSerializer):
    """
    Read/write serializer for the current user's profile.
    Password is not editable here.
    """

    avatar_url = serializers.SerializerMethodField()
    role_display = serializers.CharField(
        source="get_role_display",
        read_only=True,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "display_name",
            "role",
            "role_display",
            "bio",
            "avatar",
            "avatar_url",
            "website",
            "is_email_verified",
            "date_joined",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "username",
            "role",
            "is_email_verified",
            "date_joined",
            "updated_at",
            "display_name",
            "role_display",
        ]
        extra_kwargs = {
            "email": {"required": False},
            "bio": {"required": False, "allow_blank": True},
            "website": {"required": False, "allow_blank": True},
        }

    def get_avatar_url(self, obj):
        request = self.context.get("request")
        url = obj.avatar_url
        if request is not None:
            return request.build_absolute_uri(url)
        return url

    def validate_email(self, value):
        if not value:
            return value
        value = value.strip().lower()
        qs = User.objects.filter(email__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Email is already in use by another account."
            )
        return value

    def validate_bio(self, value):
        return value.strip() if value else value

    def validate_website(self, value):
        return value.strip() if value else value


class AvatarUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["avatar"]

    def validate_avatar(self, value):
        # Size check
        if value and value.size > 2 * 1024 * 1024:
            raise serializers.ValidationError("Avatar must be smaller than 2 MB.")
        # Extension check
        if value:
            ext = value.name.rsplit(".", 1)[-1].lower()
            if ext not in ("jpg", "jpeg", "png", "webp"):
                raise serializers.ValidationError("Avatar must be JPG, PNG, or WebP.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate_new_password(self, value):
        try:
            validate_password(value, self.context["request"].user)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages)) from None
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match."}
            )
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])


# ============================================================
# Login
# ============================================================


class LoginSerializer(serializers.Serializer):
    """
    Authenticate a user and return JWT access + refresh tokens.
    """

    username = serializers.CharField()
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    def validate(self, attrs):
        request = self.context.get("request")
        username = attrs.get("username", "").strip()
        password = attrs.get("password")

        if not username or not password:
            raise serializers.ValidationError("Username and password are required.")

        user = authenticate(request=request, username=username, password=password)
        if user is None:
            raise serializers.ValidationError("Invalid username or password.")
        if not user.is_active:
            raise serializers.ValidationError("This account has been deactivated.")

        attrs["user"] = user
        return attrs

    def to_representation(self, instance):
        user = self.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserProfileSerializer(user, context=self.context).data,
        }


# ============================================================
# Logout
# ============================================================


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def save(self, **kwargs):
        try:
            RefreshToken(self.validated_data["refresh"]).blacklist()
        except TokenError:
            pass


# ============================================================
# Password reset — request
# ============================================================


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Request a password reset. Always returns 200, even if the
    email doesn't exist, to prevent user enumeration.
    """

    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()

    def save(self, **kwargs):
        request = self.context.get("request")
        current_site = get_current_site(request)
        email = self.validated_data["email"]
        protocol = "https" if request and request.is_secure() else "http"
        for user in self.get_users(email):
            context = {
                "email": user.email,
                "protocol": protocol,
                "domain": current_site.domain,
                "site_name": current_site.name,
                "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                "token": default_token_generator.make_token(user),
            }
            text_template = "accounts/password_reset/password_reset_confirm_email.txt"
            html_template = "accounts/password_reset/password_reset_confirm_email.html"
            email_kwargs = {
                "recipient": user.email,
                "subject": f"Password reset on {current_site.name}",
                "text_template": text_template,
                "html_template": html_template,
                "context": context,
            }

            if settings.HOST_ASYNC_ABILITY:
                send_email.delay(**email_kwargs)
            else:
                send_email(**email_kwargs)

    def get_users(self, email):
        active_users = User.objects.filter(
            email__iexact=self.validated_data["email"],
            is_active=True,
        )
        return (
            u
            for u in active_users
            if u.has_usable_password() and _unicode_ci_compare(email, u.email)
        )


# ============================================================
# Password reset — confirm
# ============================================================


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Set a new password using the uidb64 + token from the email link.

    Mirrors Django's PasswordResetConfirmView but for JSON.
    """

    uidb64 = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages)) from None
        return value

    def validate(self, attrs):
        # ------------------------------------------------------
        # 1. Decode uidb64 → user
        # ------------------------------------------------------
        try:
            uid = urlsafe_base64_decode(attrs["uidb64"]).decode()
            user = User.objects.get(pk=uid)
        except (
            TypeError,
            ValueError,
            OverflowError,
            User.DoesNotExist,
        ):
            # Same message for all failures, to prevent enumeration.
            raise serializers.ValidationError(
                {"token": "The reset link is invalid or has expired."}
            ) from None

        # ------------------------------------------------------
        # 2. Check the token
        # ------------------------------------------------------
        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError(
                {"token": "The reset link is invalid or has expired."}
            )

        # ------------------------------------------------------
        # 3. Check password confirmation
        # ------------------------------------------------------
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )

        # Attach user for save()
        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["password"])
        user.save(update_fields=["password"])

        # Blacklist every outstanding refresh token for this user.
        for token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=token)
