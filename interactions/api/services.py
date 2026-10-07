# interactions/services.py
from django.db import IntegrityError, transaction

from interactions.models import Bookmark, Comment, CommentLike, Like

# ============================================================
# Toggle helpers
# ============================================================


def toggle_like(user, post):
    """
    Toggle a like on a post.

    Returns a tuple: (liked: bool, like_count: int)
    - liked = True if the user now has a like
    - liked = False if the like was removed
    """
    try:
        with transaction.atomic():
            like = Like.objects.get(user=user, post=post)
            like.delete()
            liked = False
    except Like.DoesNotExist:
        try:
            Like.objects.create(user=user, post=post)
            liked = True
        except IntegrityError:
            # Race condition: another request created the like first.
            # Treat it as already liked.
            liked = True

    # Recompute count from the DB
    like_count = Like.objects.filter(post=post).count()
    return liked, like_count


def toggle_comment_like(user, comment):
    """
    Toggle a like on a comment.
    Returns (liked: bool, like_count: int).
    """
    try:
        with transaction.atomic():
            like = CommentLike.objects.get(user=user, comment=comment)
            like.delete()
            liked = False
    except CommentLike.DoesNotExist:
        try:
            CommentLike.objects.create(user=user, comment=comment)
            liked = True
        except IntegrityError:
            liked = True

    like_count = CommentLike.objects.filter(comment=comment).count()
    return liked, like_count


def toggle_bookmark(user, post):
    """
    Toggle a bookmark on a post.
    Returns (bookmarked: bool, bookmark_count: int).
    """
    try:
        with transaction.atomic():
            bookmark = Bookmark.objects.get(user=user, post=post)
            bookmark.delete()
            bookmarked = False
    except Bookmark.DoesNotExist:
        try:
            Bookmark.objects.create(user=user, post=post)
            bookmarked = True
        except IntegrityError:
            bookmarked = True

    bookmark_count = Bookmark.objects.filter(post=post).count()
    return bookmarked, bookmark_count


# ============================================================
# Comment creation
# ============================================================


def create_comment(user, post, body, parent_id=None):
    """
    Create a comment or reply.

    - Validates parent belongs to the same post.
    - Defaults status to 'approved' (change to 'pending' if you
      want pre-moderation).
    """
    parent = None
    if parent_id:
        try:
            parent = Comment.objects.get(pk=parent_id, post=post)
        except Comment.DoesNotExist:
            raise ValueError("Parent comment not found on this post.") from None

    return Comment.objects.create(
        post=post,
        author=user,
        parent=parent,
        body=body,
        status=Comment.Status.APPROVED,
    )
