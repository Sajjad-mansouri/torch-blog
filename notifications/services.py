# notifications/services.py
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from .models import Notification


def create_notification(*, recipient, actor, verb, target=None, url="", message=""):
    """
    Create a single notification, applying universal rules:

    - Never notify the actor about their own action.
    - Do not create duplicates within a short window for the
      same (recipient, actor, verb, target).
    """
    # Rule 1: no self-notifications
    if recipient == actor:
        return None

    # Rule 2: deduplicate within a 5-minute window
    if target is not None:
        target_ct = ContentType.objects.get_for_model(target)
        exists = Notification.objects.filter(
            recipient=recipient,
            actor=actor,
            verb=verb,
            target_type=target_ct,
            target_id=target.pk,
            created_at__gte=timezone.now() - timezone.timedelta(minutes=5),
        ).exists()
        if exists:
            return None

    # Create
    target_ct = ContentType.objects.get_for_model(target) if target else None
    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        verb=verb,
        target_type=target_ct,
        target_id=target.pk if target else None,
        url=url,
        message=message,
    )


def notify_new_comment(comment):
    """
    Bob comments on Alice's post → notify Alice.

    Skip if Bob is Alice (self-comment).
    """
    return create_notification(
        recipient=comment.post.author,
        actor=comment.author,
        verb=Notification.Verb.NEW_COMMENT,
        target=comment,
        url=f"{comment.post.get_absolute_url()}#comment-{comment.id}",
        message=f"{comment.author.display_name} commented on your post",
    )


def notify_reply(reply):
    """
    Carol replies to Bob's comment on Alice's post:
    - Notify Bob (parent comment's author)
    - Notify Alice (post's author)
    - Skip the actor (Carol)
    - Deduplicate if Bob == Alice
    """
    recipients = set()
    if reply.parent and reply.parent.author:
        recipients.add(reply.parent.author)
    if reply.post.author:
        recipients.add(reply.post.author)

    recipients.discard(reply.author)

    for recipient in recipients:
        create_notification(
            recipient=recipient,
            actor=reply.author,
            verb=Notification.Verb.REPLY,
            target=reply,
            url=f"{reply.post.get_absolute_url()}#comment-{reply.id}",
            message=f"{reply.author.display_name} replied to a comment",
        )


def notify_post_like(like):
    """
    Bob likes Alice's post → notify Alice.
    Skip if Bob is the post author (self-like).
    """
    return create_notification(
        recipient=like.post.author,
        actor=like.user,
        verb=Notification.Verb.POST_LIKE,
        target=like.post,
        url=like.post.get_absolute_url(),
        message=f"{like.user.display_name} liked your post",
    )


def notify_comment_like(comment_like):
    """
    Alice likes Bob's comment → notify Bob.
    Skip if Alice is the comment author.
    """
    return create_notification(
        recipient=comment_like.comment.author,
        actor=comment_like.user,
        verb=Notification.Verb.COMMENT_LIKE,
        target=comment_like.comment,
        url=(
            f"{comment_like.comment.post.get_absolute_url()}"
            f"#comment-{comment_like.comment.id}"
        ),
        message=f"{comment_like.user.display_name} liked your comment",
    )


def notify_post_approved(post, editor):
    return create_notification(
        recipient=post.author,
        actor=editor,
        verb=Notification.Verb.POST_APPROVED,
        target=post,
        url=post.get_absolute_url(),
        message=f'Your post "{post.title}" was approved and published',
    )


def notify_post_rejected(post, editor, reason):
    return create_notification(
        recipient=post.author,
        actor=editor,
        verb=Notification.Verb.POST_REJECTED,
        target=post,
        url=f"/dashboard/posts/{post.id}/",
        message=f'Your post "{post.title}" was rejected: {reason}',
    )


def notify_post_changes_requested(post, editor, note):
    return create_notification(
        recipient=post.author,
        actor=editor,
        verb=Notification.Verb.POST_CHANGES_REQUESTED,
        target=post,
        url=f"/dashboard/posts/{post.id}/edit/",
        message=f'Changes requested for "{post.title}": {note}',
    )
