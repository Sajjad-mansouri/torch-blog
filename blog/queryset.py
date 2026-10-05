from django.db import models
from django.db.models import Count, Q
from django.utils import timezone


class PostQuerySet(models.QuerySet):
    def published(self):
        return self.filter(
            status="published",
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

    # optimization
    def for_card(self):
        """
        -eager-loads author and category
        -Annotate like_count, comment,  bookmark_count
        """

        return self.selected_related("author", "category").annotate(
            like_count=Count("likes", distinct=True),
            comment_count=Count(
                "comments",
                filter=Q(comments__status="approved", comments__is_deleted=False),
                distinct=True,
            ),
            bookmark_count=Count("bookmarks", distinct=True),
        )
