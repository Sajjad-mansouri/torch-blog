from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field

from .utils import calculate_reading_time, clean_text

User = get_user_model()


def category_image_upload_path(instance, filename):
    return f"categories/{filename}"


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, db_index=True)
    description = models.TextField(max_length=500, blank=True)
    image = models.ImageField(
        upload_to=category_image_upload_path, blank=True, null=True
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["order", "name"]
        indexes = [
            models.Index(fields=["slug", "is_active"]),
            models.Index(fields=["parent", "order"]),
        ]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} → {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name, allow_unicode=True)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        super().save(*args, **kwargs)


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    usage_count = models.PositiveIntegerField(
        default=0, help_text="Count of published post with this tag"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ["-usage_count", "name"]

        indexes = [models.Index(fields=["slug"]), models.Index(fields=["-usage_count"])]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


def post_image_upload_path(instance, filename):
    today = timezone.now()
    return f"posts/{today.year}/{today.month:02d}/{filename}"


class PostQuerySet(models.QuerySet):
    def published(self):
        return self.filter(
            status=Post.Status.PUBLISHED,
            is_deleted=False,
            published_at__lte=timezone.now(),
        )

    def featured(self):
        return (
            self.published()
            .filter(is_featured=True)
            .order_by("feature_order", "-published_at")
        )

    def trending(self, days=7):
        cutoff = timezone.now() - timezone.timedelta(days=days)
        return self.published().filter(published__gte=cutoff).order_by("-views_count")

    def latest(self):
        return self.published().order_by("-published_at")


def create_post_slug(title, post_pk):
    base_slug = slugify(title, allow_unicode=True)[:250]
    slug = base_slug
    counter = 1
    while Post.objects.filter(slug=slug).exclude(pk=post_pk).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending"
        CHANGES_REQUESTED = "changes_requested", "Changes Requested"
        APPROVED = "approved", "Approved"
        SCHEDULED = "scheduled", "Scheduled"
        PUBLISHED = "published", "Published"
        REJECTED = "rejected", "Rejected"
        UNPUBLISHED = "unpublished", "Unpublished"
        ARCHIVED = "archived", "Archived"

    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name="posts")
    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=280, unique=True, db_index=True)
    summary = models.TextField(max_length=500, blank=True)
    body = CKEditor5Field(
        config_name="default",
        help_text="Main post content (rich text)",
    )

    featured_image = models.ImageField(
        upload_to=post_image_upload_path, blank=True, null=True
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
        help_text="Primary category",
    )

    extra_categories = models.ManyToManyField(
        Category,
        blank=True,
        related_name="extra_posts",
        help_text="Secondary categories",
    )

    tags = models.ManyToManyField(Tag, blank=True, related_name="posts")

    status = models.CharField(
        max_length=25, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    is_featured = models.BooleanField(default=False, db_index=True)

    featured_order = models.PositiveIntegerField(
        null=True, blank=True, help_text="Display order in Hero (lower = earlier)"
    )

    # ---------- Timestamps ----------
    scheduled_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ---------- Stats ----------
    views_count = models.PositiveIntegerField(default=0)
    reading_time = models.PositiveIntegerField(
        default=0,
        help_text="Estimated reading time in minutes (auto-calculated)",
    )

    # ---------- Review ----------
    rejection_reason = models.TextField(blank=True)
    changes_requested_note = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_posts",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # ---------- SEO ----------
    meta_title = models.CharField(max_length=200, blank=True, default="")
    meta_description = models.CharField(max_length=300, blank=True, default="")
    og_image = models.ImageField(upload_to="og/", blank=True, null=True)
    no_index = models.BooleanField(default=False)

    # ---------- Soft delete ----------
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_posts",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = PostQuerySet.as_manager()

    class Meta:
        verbose_name = "Post"
        verbose_name_plural = "Posts"
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "-published_at"]),
            models.Index(fields=["status", "is_deleted", "-published_at"]),
            models.Index(fields=["is_featured", "featured_order"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["author", "status"]),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["featured_order"],
                condition=models.Q(is_featured=True, featured_order__isnull=False),
                name="unique_featured_order",
            )
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = create_post_slug(self.title, self.pk)

        # Sanitize HTML (strip dangerous tags/attributes)
        if self.summary:
            self.summary = clean_text(self.summary)[:500]

        self.reading_time = calculate_reading_time(self.body or "")

        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()

        if not self.meta_title:
            self.meta_title = self.title[:200]

        if not self.meta_description:
            source = self.summary or clean_text(self.body or "")
            self.meta_description = source[:300]

        super().save(*args, **kwargs)

    def can_be_deleted_by(self, user):
        if not user or not user.is_authenticated:
            return False

        if user.is_editor:
            return True

        if user != self.author:
            return False

        return self.status in [
            self.Status.DRAFT,
            self.Status.REJECTED,
            self.Status.ARCHIVED,
        ]

    def can_be_submitted_by(self, user):
        if not user or not user.is_authenticated:
            return False

        return user == self.author and self.status in [
            self.Status.DRAFT,
            self.Status.REJECTED,
            self.Status.CHANGES_REQUESTED,
        ]

    def submit_for_review(self):
        self.status = self.Status.PENDING
        self.rejection_reason = ""
        self.changes_requested_note = ""
        self.save(
            update_fields=[
                "status",
                "rejection_reason",
                "changes_requested_note",
                "updated_at",
            ]
        )

    def approve_and_publish(self, editor):
        self.status = self.Status.PUBLISHED
        self.reviewed_by = editor
        self.reviewd_at = timezone.now()
        self.rejection_reason = ""
        self.changes_requested_note = ""
        if not self.published_at:
            self.published_at = timezone.now()
        self.save()

    def reject(self, editor, reason):
        self.status = self.Status.REJECTED
        self.reviewed_by = editor
        self.reviewd_at = timezone.now()
        self.rejection_reason = reason
        self.save()

    def request_changes(self, editor, note):
        self.status = self.Status.CHANGES_REQUESTED
        self.reviewed_by = editor
        self.reviewd_at = timezone.now()
        self.changes_requested_note = note
        self.save()

    def unpublish(self, editor, reason=""):
        self.status = self.Status.UNPUBLISHED
        self.reviewed_by = editor
        self.reviewd_at = timezone.now()
        self.rejection_reason = reason
        self.save()

    def soft_delete(self, user):
        self.is_deleted = True
        self.deleted_by = user
        self.deleted_at = timezone.now()
        # Free up the slug so a new post can reuse it
        timestamp = int(timezone.now().timestamp())
        self.slug = f"{self.slug}-deleted-{timestamp}"[:200]
        self.save(update_fields=["is_deleted", "deleted_by", "deleted_at", "slug"])

    def restore(self):
        self.is_deleted = False
        self.deleted_by = None
        self.deleted_at = None
        self.slug = create_post_slug(self.title, self.pk)
        self.save(update_fields=["slug", "is_deleted", "deleted_by", "deleted_at"])

    @property
    def like_count(self):
        return self.likes.count()

    @property
    def comment_count(self):
        return self.comments.filter(
            status="approved",
            is_deleted=False,
        ).count()

    @property
    def bookmark_count(self):
        return self.bookmarks.count()

    @property
    def is_published(self):
        return self.status == self.Status.PUBLISHED and not self.is_deleted


class PostView(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="views")

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="post_views",
    )

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    session_key = models.CharField(max_length=70, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Post View"
        verbose_name_plural = "Post Views"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["post", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.post.title} - {self.created_at}"
