from django.contrib import admin

from .models import Category, Post, Tag


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "status", "published_at", "views_count")
    list_filter = ("status", "is_featured", "is_deleted", "category")
    search_fields = ("title", "summary", "body")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("views_count", "reading_time", "created_at", "updated_at")
    filter_horizontal = ("tags", "extra_categories")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "order", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "usage_count")
    prepopulated_fields = {"slug": ("name",)}
