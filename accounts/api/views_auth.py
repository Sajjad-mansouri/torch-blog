from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .serializers import (
    AvatarUploadSerializer,
    ChangePasswordSerializer,
    EmailVerificationConfirmSerializer,
    EmailVerificationResendSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserProfileSerializer,
)

# ============================================================
# Login
# ============================================================


class LoginView(generics.GenericAPIView):
    """
    POST /api/v1/auth/login/
    Returns access + refresh tokens and the user's profile.
    """

    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ============================================================
# Logout
# ============================================================


class LogoutView(generics.GenericAPIView):
    """
    POST /api/v1/auth/logout/
    Blacklist the provided refresh token.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================================
# Me — profile
# ============================================================


class MeView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/v1/auth/me/
    PATCH /api/v1/auth/me/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user


class AvatarUploadView(generics.GenericAPIView):
    """
    POST /api/v1/auth/me/avatar/
    Upload a new avatar.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = AvatarUploadSerializer
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = self.get_serializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            UserProfileSerializer(
                request.user,
                context={"request": request},
            ).data
        )


class ChangePasswordView(generics.GenericAPIView):
    """
    POST /api/v1/auth/me/change-password/
    Change the authenticated user's password.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password changed."})


class PasswordResetRequestView(generics.GenericAPIView):
    """
    POST /api/v1/auth/password-reset/
    Request a password reset link.

    Always returns 200 with the same message, even if the email
    doesn't exist. This prevents user enumeration.
    """

    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "detail": (
                    "If an account with that email exists, a reset link has been sent."
                )
            }
        )


class PasswordResetConfirmView(generics.GenericAPIView):
    """
    POST /api/v1/auth/password-reset/confirm/
    Body: {
        "uidb64": "MQ",
        "token": "abc-123-def",
        "password": "newpassword789",
        "password_confirm": "newpassword789"
    }

    The uidb64 and token come from the email link's query string.
    The frontend extracts them and posts them here along with the
    new password.
    """

    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Password has been reset. You can now log in."},
            status=status.HTTP_200_OK,
        )


# ============================================================
# Register
# ============================================================


class RegisterView(generics.CreateAPIView):
    """
    POST /api/v1/auth/register/
    Create a new account (role=reader).
    """

    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "message": (
                    "Account created. Check your email to verify your address."
                ),
            },
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# Confirm email verification
# ============================================================


class VerifyEmailConfirmView(generics.GenericAPIView):
    """
    POST /api/v1/auth/verify-email/confirm/
    Body: {"uidb64": "<base64-id>", "token": "<token>"}

    The uidb64 and token come from the query string of the
    verification email link. The frontend extracts them and
    posts them here.

    On success:
    - is_active becomes True
    - is_email_verified becomes True

    Idempotent: calling this multiple times with the same valid
    token succeeds every time. Invalid or expired tokens return
    a 400 with a generic message (no enumeration).
    """

    permission_classes = [AllowAny]
    serializer_class = EmailVerificationConfirmSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"detail": "Email verified. You can now log in."},
            status=status.HTTP_200_OK,
        )


# ============================================================
# Resend verification email
# ============================================================


class ResendVerificationThrottle(AnonRateThrottle):
    """
    Rate limit: 3 resend requests per hour per IP.
    Prevents an attacker from spamming a user's inbox.
    """

    scope = "resend_verification"
    rate = "3/hour"


class ResendVerificationView(generics.GenericAPIView):
    """
    POST /api/v1/auth/verify-email/resend/
    Body: {"email": "user@example.com"}

    Sends a new verification email if:
    - The user exists
    - The user is not yet verified
    - The user has an email address
    - The user has a usable password

    Always returns 200, even if the email doesn't exist, to
    prevent user enumeration.
    """

    permission_classes = [AllowAny]
    serializer_class = EmailVerificationResendSerializer
    throttle_classes = [ResendVerificationThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "detail": (
                    "If an unverified account with that email exists, "
                    "a new verification link has been sent."
                )
            },
            status=status.HTTP_200_OK,
        )
