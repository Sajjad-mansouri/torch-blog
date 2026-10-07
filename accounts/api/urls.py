# accounts/auth_urls.py
from django.urls import path

from .views_auth import (
    LoginView,
)

app_name = "auth"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
]
