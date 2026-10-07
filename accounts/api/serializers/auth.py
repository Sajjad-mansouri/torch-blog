from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

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
