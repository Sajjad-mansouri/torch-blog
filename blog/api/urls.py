# blog/urls.py
from account.api import views as account_views
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "blog_api"

router = DefaultRouter()
router.register("categories", views.CategoryViewSet, basename="category")
router.register("tags", views.TagViewSet, basename="tag")
router.register("authors", account_views.AuthorViewSet, basename="author")
router.register("me/posts", views.MePostViewSet, basename="me-post")
router.register("posts", views.PostAuthorViewSet, basename="post-write")
urlpatterns = [
    path("home/", views.HomeAPIView.as_view(), name="home"),
    path("posts/", views.PostListAPIView.as_view(), name="post_list"),
    path("posts/<slug:slug>/", views.PostDetailView.as_view(), name="post-detail"),
    path("search/", views.SearchView.as_view(), name="search"),
    path("search/suggest/", views.SearchSuggestView.as_view(), name="search-suggest"),
    # ViewSet-generated endpoints
    path("", include(router.urls)),
]
