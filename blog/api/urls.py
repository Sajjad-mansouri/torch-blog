# blog/urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.api import views as account_views

from . import views

app_name = "blog_api"

router = DefaultRouter()
router.register("categories", views.CategoryViewSet, basename="category")
router.register("tags", views.TagViewSet, basename="tag")
router.register("authors", account_views.AuthorViewSet, basename="author")
router.register("me/posts", views.MePostViewSet, basename="me-post")
router.register("dashboard/posts", views.PostAuthorViewSet, basename="post-write")
urlpatterns = [
    path("home/", views.HomeAPIView.as_view(), name="home"),
    path("posts/", views.PostListAPIView.as_view(), name="post_list"),
    path("posts/<slug:slug>/", views.PostDetailAPIView.as_view(), name="post-detail"),
    path(
        "posts/<slug:slug>/preview/",
        views.PostPreviewAPIView.as_view(),
        name="post-preview",
    ),
    path("search/", views.SearchAPIView.as_view(), name="search"),
    path("search/suggest/", views.SearchSuggestView.as_view(), name="search-suggest"),
    # ViewSet-generated endpoints
    path("", include(router.urls)),
]
