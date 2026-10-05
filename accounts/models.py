from django.contrib.auth.models import AbstractUser
from django.db import models


def avatar_upload_path(instance, filename):
    return f"avatars/{instance.id or 'new'}/{filename}"


class User(AbstractUser):
    class Role(models.TextChoices):
        READER = "reader", "Reader"
        AUTHOR = "author", "Author"
        EDITOR = "editor", "Editor"

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.READER,
        db_index=True,
        help_text="User Role",
    )
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(
        upload_to=avatar_upload_path, blank=True, null=True, help_text="Profile Image"
    )
    website = models.URLField(blank=True, default="")

    is_email_verified = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    # ---------- Role helpers ----------
    @property
    def is_reader(self):
        return self.role == self.Role.READER

    @property
    def is_author(self):
        return self.role == self.Role.AUTHOR

    @property
    def is_editor(self):
        return self.role == self.Role.EDITOR

    # ---------- Permissions helpers ----------
    @property
    def can_write_posts(self):
        return self.role in (self.Role.AUTHOR, self.Role.EDITOR)

    @property
    def can_publish_posts(self):
        return self.role == self.Role.EDITOR

    @property
    def can_review_posts(self):
        return self.role == self.Role.EDITOR

    @property
    def can_manage_users(self):
        return self.role == self.Role.EDITOR

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    @property
    def avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return "/static/img/default-avatar.jpg"


class SocialLink(models.Model):
    class Platform(models.TextChoices):
        GITHUB = "github", "GitHub"
        TWITTER = "twitter", "Twitter / X"
        LINKEDIN = "linkedin", "LinkedIn"
        INSTAGRAM = "instagram", "Instagram"
        YOUTUBE = "youtube", "YouTube"
        FACEBOOK = "facebook", "Facebook"
        TELEGRAM = "telegram", "Telegram"
        WEBSITE = "website", "Website"
        EMAIL = "email", "Email"
        STACKOVERFLOW = "stackoverflow", "Stack Overflow"

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="social_links"
    )
    platform = models.CharField(max_length=30, choices=Platform.choices)
    url = models.URLField(max_length=300)
    username = models.CharField(
        max_length=100,
        blank=True,
    )
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "platform"], name="unique_platform_per_user"
            )
        ]
        ordering = ["order", "platform"]

    def __str__(self):
        return f"{self.user.username} - {self.get_platform_display()}"
