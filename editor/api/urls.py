# editor/urls.py
from django.urls import path

from . import views

urlpatterns = [
    # Posts
    path("review-queue/", views.ReviewQueueView.as_view(), name="review-queue"),
    path("posts-list/", views.EditorPostListView.as_view(), name="editor-post-list"),
]
