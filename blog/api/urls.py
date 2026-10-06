# blog/urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "blog_api"

router = DefaultRouter()
router.register("categories", views.CategoryViewSet, basename="category")
urlpatterns = [
    path("home/", views.HomeAPIView.as_view(), name="home"),
    path("posts/", views.PostListAPIView.as_view(), name="post_list"),
    path("posts/<slug:slug>/", views.PostDetailView.as_view(), name="post-detail"),
    # ViewSet-generated endpoints
    path("", include(router.urls)),
]
