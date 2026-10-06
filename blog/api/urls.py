# blog/urls.py
from django.urls import path

from . import views

app_name = "blog_api"

urlpatterns = [
    path("home/", views.HomeAPIView.as_view(), name="home"),
    path("posts/", views.PostListAPIView.as_view(), name="post_list"),
]
