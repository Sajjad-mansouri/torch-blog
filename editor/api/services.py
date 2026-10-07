# blog/services_editorial.py
from django.db import transaction
from django.utils import timezone

from blog.models import Post

# ============================================================
# Approval
# ============================================================


@transaction.atomic
def approve_post(post, editor):
    """
    Approve a pending post and publish it.

    - Only works if the post is currently 'pending'.
    - Sets published_at on first publish.
    - Records reviewed_by and reviewed_at.
    """
    if post.status != Post.Status.PENDING:
        raise ValueError(
            f"Only pending posts can be approved. Current status: {post.status}."
        )

    post.status = Post.Status.PUBLISHED
    post.reviewed_by = editor
    post.reviewed_at = timezone.now()
    post.rejection_reason = ""
    post.changes_requested_note = ""

    if not post.published_at:
        post.published_at = timezone.now()

    post.save()
    return post


# ============================================================
# Rejection
# ============================================================


@transaction.atomic
def reject_post(post, editor, reason):
    """
    Reject a pending or changes-requested post with a reason.

    - Reason is required.
    - Post moves to 'rejected'.
    """
    if not reason or not reason.strip():
        raise ValueError("Rejection reason is required.")

    if post.status not in (
        Post.Status.PENDING,
        Post.Status.CHANGES_REQUESTED,
    ):
        raise ValueError(
            f"Only pending or changes-requested posts can be rejected. "
            f"Current status: {post.status}."
        )

    post.status = Post.Status.REJECTED
    post.reviewed_by = editor
    post.reviewed_at = timezone.now()
    post.rejection_reason = reason.strip()
    post.changes_requested_note = ""
    post.save()
    return post


# ============================================================
# Request changes
# ============================================================


@transaction.atomic
def request_changes(post, editor, note):
    """
    Ask the author to revise a pending post.

    - Note is required.
    - Post moves to 'changes_requested'.
    """
    if not note or not note.strip():
        raise ValueError("Change request note is required.")

    if post.status != Post.Status.PENDING:
        raise ValueError(
            f"Only pending posts can receive change requests. "
            f"Current status: {post.status}."
        )

    post.status = Post.Status.CHANGES_REQUESTED
    post.reviewed_by = editor
    post.reviewed_at = timezone.now()
    post.changes_requested_note = note.strip()
    post.rejection_reason = ""
    post.save()
    return post


# ============================================================
# Unpublish
# ============================================================


@transaction.atomic
def unpublish_post(post, editor, reason=""):
    """
    Take a published post offline.

    - Post moves to 'unpublished'.
    - Reason is optional.
    """
    if post.status != Post.Status.PUBLISHED:
        raise ValueError(
            f"Only published posts can be unpublished. Current status: {post.status}."
        )

    post.status = Post.Status.UNPUBLISHED
    post.reviewed_by = editor
    post.reviewed_at = timezone.now()
    post.rejection_reason = reason.strip() if reason else ""
    post.save()
    return post
