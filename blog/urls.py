from django.urls import path

from . import views

app_name = "blog"
urlpatterns = [
    path("posts/", views.PostsTemplateView.as_view(), name="posts"),
    path("posts/<slug>/", views.PostDetailView.as_view(), name="post-detail"),
]
