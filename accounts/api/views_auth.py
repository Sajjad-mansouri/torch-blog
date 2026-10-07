from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .serializers import (
    LoginSerializer,
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
