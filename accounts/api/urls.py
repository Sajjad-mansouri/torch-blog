# accounts/auth_urls.py
from django.urls import path

from .views_auth import AvatarUploadView, LoginView, LogoutView, MeView

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
]
