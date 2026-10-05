# core/models.py
from django.conf import settings
from django.core.cache import cache
from django.db import models


class SiteSettings(models.Model):
    # General
    site_title = models.CharField(max_length=100, default="Torch")
    tagline = models.CharField(max_length=200, blank=True)
    logo = models.ImageField(upload_to="site/", blank=True, null=True)
    favicon = models.ImageField(upload_to="site/", blank=True, null=True)

    # Home
    hero_text = models.CharField(max_length=300, blank=True)
    hero_cta_text = models.CharField(max_length=50, blank=True)
    hero_cta_link = models.CharField(max_length=200, blank=True)
    posts_per_page = models.PositiveIntegerField(default=12)
    featured_count = models.PositiveIntegerField(default=5)

    # Landing page (/project/)
    project_name = models.CharField(max_length=100, default="Torch")
    project_tagline = models.CharField(max_length=300, blank=True)
    project_description = models.TextField(
        blank=True, help_text="description (Markdown)"
    )
    project_goal = models.TextField(blank=True, help_text="goal (Markdown)")
    project_repo_url = models.URLField(blank=True)
    project_demo_url = models.URLField(blank=True)

    # Footer
    footer_text = models.CharField(max_length=300, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return self.site_title

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete("site_settings")

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def get(cls):
        cached = cache.get("site_settings")
        if cached:
            return cached
        obj, _ = cls.objects.get_or_create(pk=1)
        cache.set("site_settings", obj, 300)
        return obj


# ============================================================
# Tech Stack
# ============================================================
class TechCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    icon = models.CharField(max_length=100, blank=True, help_text="CSS class")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tech Category"
        verbose_name_plural = "Tech Categories"
        ordering = ["order", "name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["order"]),
        ]

    def __str__(self):
        return self.name


class TechItem(models.Model):
    category = models.ForeignKey(
        TechCategory, on_delete=models.CASCADE, related_name="items"
    )
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=250, blank=True)
    icon = models.CharField(max_length=200, blank=True, help_text="logo")
    icon_image = models.ImageField(upload_to="landing/tech/", blank=True, null=True)
    url = models.URLField(blank=True)
    version = models.CharField(max_length=50, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tech Item"
        verbose_name_plural = "Tech Items"
        ordering = ["category", "order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "name"], name="unique_tech_per_category"
            )
        ]
        indexes = [
            models.Index(fields=["category", "order"]),
        ]

    def __str__(self):
        return f"{self.category.name} → {self.name}"


# ============================================================
# Features
# ============================================================
class FeatureGroup(models.Model):
    title = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True)
    description = models.CharField(max_length=300, blank=True)
    icon = models.CharField(max_length=100, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Feature Group"
        verbose_name_plural = "Feature Groups"
        ordering = ["order", "title"]
        indexes = [models.Index(fields=["slug"])]

    def __str__(self):
        return self.title


class FeatureItem(models.Model):
    group = models.ForeignKey(
        FeatureGroup, on_delete=models.CASCADE, related_name="items"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=1000)
    icon = models.CharField(max_length=100, blank=True, help_text="CSS class  emoji")
    icon_image = models.ImageField(upload_to="landing/features/", blank=True, null=True)
    color = models.CharField(max_length=20, blank=True, help_text="#3b82f6")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Feature Item"
        verbose_name_plural = "Feature Items"
        ordering = ["group", "order", "title"]
        indexes = [
            models.Index(fields=["group", "order"]),
        ]

    def __str__(self):
        return f"{self.group.title} → {self.title}"


# ============================================================
# API Endpoints
# ============================================================
class ApiEndpoint(models.Model):
    class Method(models.TextChoices):
        GET = "GET", "GET"
        POST = "POST", "POST"
        PUT = "PUT", "PUT"
        PATCH = "PATCH", "PATCH"
        DELETE = "DELETE", "DELETE"

    method = models.CharField(max_length=10, choices=Method.choices, default=Method.GET)
    path = models.CharField(max_length=250)
    description = models.CharField(max_length=300, blank=True)
    auth_required = models.BooleanField(default=False)
    group = models.CharField(
        max_length=100, blank=True, help_text="Posts / Comments / Auth / ..."
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "API Endpoint"
        verbose_name_plural = "API Endpoints"
        ordering = ["group", "order", "path"]
        indexes = [
            models.Index(fields=["group", "order"]),
        ]

    def __str__(self):
        return f"{self.method} {self.path}"


# ============================================================
# Screenshots
# ============================================================
class Screenshot(models.Model):
    title = models.CharField(max_length=200)
    caption = models.CharField(max_length=300, blank=True)
    image = models.ImageField(upload_to="landing/screenshots/")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Screenshot"
        verbose_name_plural = "Screenshots"
        ordering = ["order", "title"]

    def __str__(self):
        return self.title


# ============================================================
# Roadmap
# ============================================================
class RoadmapPhase(models.Model):
    class Status(models.TextChoices):
        DONE = "done", "Done"
        IN_PROGRESS = "in_progress", "In Progress"
        PLANNED = "planned", "Planned"

    title = models.CharField(max_length=150)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PLANNED
    )
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Roadmap Phase"
        verbose_name_plural = "Roadmap Phases"
        ordering = ["order"]

    def __str__(self):
        return f"{self.title} ({self.status})"


class RoadmapItem(models.Model):
    phase = models.ForeignKey(
        RoadmapPhase, on_delete=models.CASCADE, related_name="items"
    )
    text = models.CharField(max_length=300)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Roadmap Item"
        verbose_name_plural = "Roadmap Items"
        ordering = ["order"]

    def __str__(self):
        return self.text


# ============================================================
# Statistics
# ============================================================
class Statistic(models.Model):
    label = models.CharField(max_length=100)
    value = models.CharField(max_length=50)
    icon = models.CharField(max_length=100, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Statistic"
        verbose_name_plural = "Statistics"
        ordering = ["order", "label"]

    def __str__(self):
        return f"{self.label}: {self.value}"


# ============================================================
# Contact & Social
# ============================================================
class SocialLink(models.Model):
    platform = models.CharField(
        max_length=50, help_text="github / twitter / linkedin / ..."
    )
    url = models.URLField()
    icon = models.CharField(max_length=100, blank=True, help_text="CSS class")
    username = models.CharField(max_length=100, blank=True)
    show_in_landing = models.BooleanField(default=True)
    show_in_footer = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Social Link"
        verbose_name_plural = "Social Links"
        ordering = ["order", "platform"]
        constraints = [
            models.UniqueConstraint(fields=["platform"], name="unique_social_platform")
        ]

    def __str__(self):
        return f"{self.platform}: {self.username or self.url}"


# ============================================================
# Contact Messages
# ============================================================
class ContactMessage(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField(max_length=150)
    subject = models.CharField(max_length=250, blank=True)
    message = models.TextField(max_length=3000)

    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    replied = models.BooleanField(default=False)
    replied_at = models.DateTimeField(null=True, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Contact Message"
        verbose_name_plural = "Contact Messages"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_read", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.name} <{self.email}>"

    def mark_read(self):
        from django.utils import timezone

        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])


# ============================================================
# Activity Log
# ============================================================
class ActivityLog(models.Model):
    class Action(models.TextChoices):
        POST_CREATED = "post_created", "Post Created"
        POST_EDITED = "post_edited", "Post Edited"
        POST_SUBMITTED = "post_submitted", "Post Submitted"
        POST_PUBLISHED = "post_published", "Post Published"
        POST_REJECTED = "post_rejected", "Post Rejected"
        POST_UNPUBLISHED = "post_unpublished", "Post Unpublished"
        POST_DELETED = "post_deleted", "Post Deleted"
        POST_RESTORED = "post_restored", "Post Restored"
        COMMENT_DELETED = "comment_deleted", "Comment Deleted"
        USER_ROLE_CHANGED = "user_role_changed", "User Role Changed"
        USER_BANNED = "user_banned", "User Banned"
        SETTINGS_UPDATED = "settings_updated", "Settings Updated"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="activity_logs",
    )
    action = models.CharField(max_length=50, choices=Action.choices, db_index=True)
    target_type = models.CharField(max_length=50, blank=True)
    target_id = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    description = models.CharField(max_length=500, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Activity Log"
        verbose_name_plural = "Activity Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["action", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.action}"
