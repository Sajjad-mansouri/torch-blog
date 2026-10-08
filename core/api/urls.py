# core/urls_landing.py
from django.urls import path

from .views import ContactView, LandingView

app_name = "landing"

urlpatterns = [
    path("landing/", LandingView.as_view(), name="landing"),
    path("contact/", ContactView.as_view(), name="contact"),
]
