# accounts/auth_urls.py
from django.urls import path

from .views_auth import (
    AvatarUploadView,
    ChangePasswordView,
    LoginView,
    LogoutView,
    MeView,
    PasswordResetRequestView,
)

app_name = "auth"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path(
        "me/avatar/",
        AvatarUploadView.as_view(),
        name="avatar-upload",
    ),
    path(
        "me/change-password/",
        ChangePasswordView.as_view(),
        name="change-password",
    ),
    path(
        "password-reset/",
        PasswordResetRequestView.as_view(),
        name="password-reset",
    ),
]
