from django.contrib.auth import authenticate, get_user_model
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
