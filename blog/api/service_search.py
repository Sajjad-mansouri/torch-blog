from django.db.models import Q

from accounts.models import User
from blog.models import Post

MIN_QUERY_LENGTH = 2
MAX_QUERY_LENGTH = 100


def search_posts(query, limit=None):
    """
    Search published posts by title, summary, and body.

    uses SearchVector with ranking. Otherwise uses icontains.

    Returns a QuerySet of Post with `for_card()` annotations.
    """

    base = Post.objects.published().for_card()

    return _search_posts_icontains(base, query, limit)


def _search_posts_icontains(base, query, limit):
    qs = base.filter(
        Q(title__icontains=query)
        | Q(summary__icontains=query)
        | Q(body__icontains=query)
    ).order_by("-published_at")
    if limit:
        qs = qs[:limit]
    return qs


def search_authors(query, limit=None):
    """
    Search authors and editors by username, first/last name, or bio.
    """
    qs = (
        User.objects.filter(role__in=[User.Role.AUTHOR, User.Role.EDITOR])
        .filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(bio__icontains=query)
        )
        .prefetch_related("social_links")
        .order_by("username")
    )
    if limit:
        qs = qs[:limit]
    return qs


# ============================================================
# Tags
# ============================================================


def search_tags(query, limit=None):
    """
    Search tags by name. Only returns tags that are in use.
    """
    from blog.models import Tag

    qs = (
        Tag.objects.filter(name__icontains=query)
        .filter(usage_count__gt=0)
        .order_by("-usage_count", "name")
    )

    if limit:
        qs = qs[:limit]
    return qs


# ============================================================
# Query normalization
# ============================================================


def normalize_query(raw_query):
    """
    Trim, collapse whitespace, and enforce length limits.
    Returns None if the query is too short to be useful.
    """
    if not raw_query:
        return None
    query = " ".join(raw_query.split()).strip()
    if len(query) < MIN_QUERY_LENGTH:
        return None
    return query[:MAX_QUERY_LENGTH]
