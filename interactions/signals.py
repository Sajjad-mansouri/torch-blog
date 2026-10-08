# interactions/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

from notifications.services import (
    notify_comment_like,
    notify_new_comment,
    notify_post_like,
    notify_reply,
)

from .models import Comment, CommentLike, Like


@receiver(post_save, sender=Comment)
def on_comment_created(sender, instance, created, **kwargs):
    if not created:
        return
    if instance.status != Comment.Status.APPROVED:
        return

    if instance.parent_id:
        notify_reply(instance)
    else:
        notify_new_comment(instance)


@receiver(post_save, sender=Like)
def on_post_like_created(sender, instance, created, **kwargs):
    if created:
        notify_post_like(instance)


@receiver(post_save, sender=CommentLike)
def on_comment_like_created(sender, instance, created, **kwargs):
    if created:
        notify_comment_like(instance)
