"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

simple_pages = {
    "": "landing",  # /              → landing
    "home": "home",  # /home/         → home
    "posts": "posts",  # /posts/        → post list
    "categories": "categories",
    "tags": "tags",
    "search": "search",
    "login": "login",  # /login/
    "register": "register",  # /register/
    "password-reset-request": "password-reset-request",
    "password-reset-confirm": "password-reset-confirm",
    "verify-email-confirm": "verify-email-confirm",
    "verify-email-resend": "verify-email-resend",
    "dashboard": "dashboard",
    "editor": "editor",
    "notifications": "notifications",
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    path("api/v1/", include("core.api.urls")),
    path("api/v1/", include("blog.api.urls")),
    path("api/v1/", include("interactions.api.urls")),
    path("api/v1/editor/", include("editor.api.urls")),
    path("api/v1/auth/", include("accounts.api.urls")),
    path("api/v1/notifications/", include("notifications.api.urls")),
    # API documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # --------------------------------------------------------
    # Frontend — pages with path parameters
    # --------------------------------------------------------
    path(
        "posts/<slug:slug>/",
        TemplateView.as_view(template_name="post.html"),
        name="post-detail-page",
    ),
    path(
        "author/<str:username>/",
        TemplateView.as_view(template_name="author.html"),
        name="author-page",
    ),
    path(
        "categories/<slug:slug>/",
        TemplateView.as_view(template_name="category.html"),
        name="category-page",
    ),
    path(
        "tags/<slug:slug>/",
        TemplateView.as_view(template_name="tag.html"),
        name="tag-page",
    ),
    path(
        "dashboard/posts/",
        TemplateView.as_view(template_name="dashboard-posts.html"),
        name="dashboard-posts",
    ),
    path(
        "dashboard/posts/new/",
        TemplateView.as_view(template_name="dashboard-post-edit.html"),
        name="dashboard-post-new",
    ),
    path(
        "dashboard/posts/<slug:slug>/edit/",
        TemplateView.as_view(template_name="dashboard-post-edit.html"),
        name="dashboard-post-edit",
    ),
    path(
        "editor/review/",
        TemplateView.as_view(template_name="editor-review.html"),
        name="editor-review",
    ),
]

# ------------------------------------------------------------
# Simple pages (no parameters)
# ------------------------------------------------------------
for url_path, template in simple_pages.items():
    urlpatterns.append(
        path(
            f"{url_path}/" if url_path else "",
            TemplateView.as_view(template_name=f"{template}.html"),
            name=template,
        )
    )

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
