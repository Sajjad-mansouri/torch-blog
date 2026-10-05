from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class Comment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SPAM = "spam", "Spam"

    post = models.ForeignKey(
        "blog.Post", on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="comments"
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )
    body = models.TextField(max_length=2000)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.APPROVED, db_index=True
    )

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_comments",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    edited_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Comment"
        verbose_name_plural = "Comments"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["post", "status", "created_at"]),
            models.Index(fields=["parent"]),
            models.Index(fields=["author"]),
        ]

    def __str__(self):
        return f"Comment by {self.author or 'deleted'} on {self.post_id}"

    @property
    def is_reply(self):
        return self.parent is not None

    @property
    def is_edited(self):
        return self.edited_at is not None

    @property
    def like_count(self):
        return self.likes.count()

    @property
    def is_visible(self):
        return (
            self.status == self.Status.APPROVED
            and not self.is_deleted
            and self.post.status == "published"
            and not self.post.is_deleted
        )

    def soft_delete(self, user):
        self.is_deleted = True
        self.deleted_by = user
        self.deleted_at = timezone.now()
        self.body = "[deleted]"
        self.save(update_fields=["is_deleted", "deleted_by", "deleted_at", "body"])

    def mark_edited(self):
        self.edited_at = timezone.now()
        self.save(update_fields=["edited_at"])
