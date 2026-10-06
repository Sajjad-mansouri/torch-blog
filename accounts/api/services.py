from django.db.models import Count, Q, Sum


def get_author_stats(user):
    """
    Return aggregate stats for an author's published posts.

    Returns a dict:
        {
            'total_posts': int,
            'total_views': int,
            'total_likes': int,
            'total_comments': int,
            'total_bookmarks': int,
        }

    Runs a single database query.
    """
    from blog.models import Post

    stats = (
        Post.objects.published()
        .filter(author=user)
        .aggregate(
            total_posts=Count("id", distinct=True),
            total_views=Sum("views_count"),
            total_likes=Count("likes", distinct=True),
            total_comments=Count(
                "comments",
                filter=Q(comments__status="approved", comments__is_deleted=False),
                distinct=True,
            ),
            total_bookmarks=Count("bookmarks", distinct=True),
        )
    )
    # Sum returns None when there are no rows
    return {
        "total_posts": stats["total_posts"] or 0,
        "total_views": stats["total_views"] or 0,
        "total_likes": stats["total_likes"] or 0,
        "total_comments": stats["total_comments"] or 0,
        "total_bookmarks": stats["total_bookmarks"] or 0,
    }
