# editor/urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "editor"
router = DefaultRouter()
router.register("posts", views.PostDecisionViewSet, basename="editor-post-decisions")
router.register("featured", views.FeaturedPostsViewSet, basename="editor-featured")
router.register(
    "comments", views.CommentModerationViewSet, basename="editor-comment-actions"
)
router.register("users", views.EditorUserDetailViewSet, basename="editor-user-actions")
router.register("categories", views.EditorCategoryViewSet, basename="editor-category")
router.register("tags", views.EditorTagViewSet, basename="editor-tag")

urlpatterns = [
    # Posts
    path("review-queue/", views.ReviewQueueView.as_view(), name="review-queue"),
    path("posts-list/", views.EditorPostListView.as_view(), name="editor-post-list"),
    # Comments
    path(
        "comments-list/",
        views.EditorCommentListView.as_view(),
        name="editor-comment-list",
    ),
    # Users
    path("users-list/", views.EditorUserListView.as_view(), name="editor-user-list"),
    # Settings
    path("settings/", views.EditorSiteSettingsView.as_view(), name="editor-settings"),
    # Router (actions on resources)
    path("", include(router.urls)),
]
