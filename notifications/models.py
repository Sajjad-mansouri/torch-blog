from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

User = get_user_model()


class Notification(models.Model):
    class Verb(models.TextChoices):
        NEW_COMMENT = "new_comment", "New Comment"
        REPLY = "reply", "Reply"
        POST_LIKE = "post_like", "Post Like"
        COMMENT_LIKE = "comment_like", "Comment Like"
        POST_APPROVED = "post_approved", "Post Approved"
        POST_REJECTED = "post_rejected", "Post Rejected"
        POST_CHANGES_REQUESTED = "post_changes_requested", "Changes Requested"
        POST_PUBLISHED = "post_published", "Post Published"
        NEW_FOLLOWER = "new_follower", "New Follower"

    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_notifications",
    )
    verb = models.CharField(max_length=40, choices=Verb.choices, db_index=True)

    # Generic target: Post, Comment, User
    target_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True
    )
    target_id = models.PositiveIntegerField(null=True, blank=True)
    target = GenericForeignKey("target_type", "target_id")

    message = models.CharField(max_length=300, blank=True, default="")
    url = models.CharField(max_length=500, blank=True, default="")

    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"]),
            models.Index(fields=["recipient", "-created_at"]),
            models.Index(fields=["target_type", "target_id"]),
        ]

    def __str__(self):
        return f"→ {self.recipient.username}: {self.verb}"

    def mark_as_read(self):
        from django.utils import timezone

        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])
