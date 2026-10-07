# interactions/urls.py
from django.urls import path

from .views import (
    CommentDetailView,
    CommentLikeToggleView,
    MeBookmarkListView,
    MeLikeListView,
    PostBookmarkToggleView,
    PostCommentsView,
    PostLikeToggleView,
)

app_name = "interactions"

urlpatterns = [
    # Post interactions
    path(
        "posts/<slug:slug>/like/",
        PostLikeToggleView.as_view(),
        name="post-like",
    ),
    path(
        "posts/<slug:slug>/bookmark/",
        PostBookmarkToggleView.as_view(),
        name="post-bookmark",
    ),
    path(
        "posts/<slug:slug>/comments/",
        PostCommentsView.as_view(),
        name="post-comments",
    ),
    # Comment interactions
    path(
        "comments/<int:pk>/",
        CommentDetailView.as_view(),
        name="comment-detail",
    ),
    path(
        "comments/<int:pk>/like/",
        CommentLikeToggleView.as_view(),
        name="comment-like",
    ),
    # Me
    path("me/likes/", MeLikeListView.as_view(), name="me-likes"),
    path("me/bookmarks/", MeBookmarkListView.as_view(), name="me-bookmarks"),
]
