"""
Fixtures specific to the notifications app tests.
"""

import pytest

from notifications.models import Notification


@pytest.fixture
def test_notification(db, test_user, test_author):
    """A baseline notification: test_author did something, test_user receives."""
    return Notification.objects.create(
        recipient=test_user,
        actor=test_author,
        verb=Notification.Verb.POST_LIKE,
        message="test_author liked your post",
        url="/some-post/",
    )


@pytest.fixture
def disconnect_interactions_signals():
    """
    Disconnect the interactions post_save receivers for the duration
    of a test, so notification service functions can be tested in
    isolation.

    Use only when a test needs to call notify_* explicitly and
    assert on exactly what that call produced. For tests that
    exercise the end-to-end signal path, do NOT request this
    fixture.
    """
    from django.db.models.signals import post_save

    from interactions import signals as int_signals
    from interactions.models import Comment, CommentLike, Like

    bindings = [
        (Comment, int_signals.on_comment_created),
        (Like, int_signals.on_post_like_created),
        (CommentLike, int_signals.on_comment_like_created),
    ]

    for sender, receiver in bindings:
        post_save.disconnect(receiver, sender=sender)

    yield

    for sender, receiver in bindings:
        post_save.connect(receiver, sender=sender)
