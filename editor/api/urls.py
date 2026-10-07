# editor/urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "editor"
router = DefaultRouter()
router.register("posts", views.PostDecisionViewSet, basename="editor-post-decisions")
router.register("featured", views.FeaturedPostsViewSet, basename="editor-featured")
urlpatterns = [
    # Posts
    path("review-queue/", views.ReviewQueueView.as_view(), name="review-queue"),
    path("posts-list/", views.EditorPostListView.as_view(), name="editor-post-list"),
    # Router (actions on resources)
    path("", include(router.urls)),
]
