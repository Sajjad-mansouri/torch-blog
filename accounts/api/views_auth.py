from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    AvatarUploadSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordResetRequestSerializer,
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
