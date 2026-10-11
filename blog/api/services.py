from datetime import timedelta

from django.db import models
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.settings import api_settings

from blog.models import Post, PostView


def get_ident(request):
    """
    Identify the machine making the request by parsing HTTP_X_FORWARDED_FOR
    if present and number of proxies is > 0. If not use all of
    HTTP_X_FORWARDED_FOR if it is available, if not use REMOTE_ADDR.
    """
    xff = request.headers.get("x-forwarded-for")
    remote_addr = request.META.get("REMOTE_ADDR")
    num_proxies = api_settings.NUM_PROXIES

    if num_proxies is not None:
        if num_proxies == 0 or xff is None:
            return remote_addr
        addrs = xff.split(",")
        client_addr = addrs[-min(num_proxies, len(addrs))]
        return client_addr.strip()

    return "".join(xff.split()) if xff else remote_addr


# view recording


def record_view(request, post, dedup_hours=1):
    user = request.user if request.user.is_authenticated else None
    ip_address = get_ident(request)
    user_agent = request.META.get("HTTP_USER_AGENT", "")[:300]
    # Get session key if the request has a session(django template views)
    # and drf with sessionauthentication do
    # jwt-only requests dont
    session_key = ""
    if hasattr(request, "session") and request.session.session_key:
        session_key = request.session.session_key
    cutoff = timezone.now() - timedelta(hours=dedup_hours)

    # build the dedup query
    if user:
        dedup_filter = models.Q(user=user)
    elif session_key:
        dedup_filter = models.Q(session_key=session_key)
    else:
        dedup_filter = models.Q(
            ip_address=ip_address, user_agent=user_agent, user__isnull=True
        )

    already = PostView.objects.filter(
        dedup_filter, post=post, created_at__gte=cutoff
    ).exists()
    if already:
        return False
    PostView.objects.create(
        post=post,
        user=user,
        ip_address=ip_address,
        session_key=session_key,
        user_agent=user_agent,
    )
    # Increment the denormalized counter on Post
    Post.objects.filter(pk=post.pk).update(views_count=models.F("views_count") + 1)

    # Refresh the in-memory instance so the serializer sees the new count
    post.refresh_from_db(fields=["views_count"])
    return True


# similar posts
def get_similar_posts(post, limit=4):
    """
    Return published posts that share tags with the given post.

    Strategy:
    - Posts that share at least one tag
    - Exclude the current post
    - Order by number of shared tags (most relevant first)
    - Fallback: if fewer than `limit` results, fill with recent posts
      from the same category.
    """
    tag_ids = list(post.tags.values_list("id", flat=True))
    if tag_ids:
        similar = (
            Post.objects.published()
            .filter(tags__id__in=tag_ids)
            .exclude(pk=post.pk)
            .annotate(shared_tags=Count("tags", filter=Q(tags__id__in=tag_ids)))
            .order_by("-shared_tags", "-published_at")[:limit]
        )
        results = list(similar)
    else:
        results = []

    # fill with recent posts the same category
    if len(results) < limit and post.category_id:
        exclude_ids = [post.pk] + [p.pk for p in results]
        fallback = (
            Post.objects.published()
            .filter(category_id=post.category_id)
            .exclude(pk__in=exclude_ids)
            .order_by("-published_at")[: limit - len(results)]
        )
        results.extend(fallback)

    return results


# other posts by the same author
def get_author_other_posts(post, limit=3):
    """
    Return other published posts by the same author.
    """
    return (
        Post.objects.published()
        .filter(author=post.author)
        .exclude(pk=post.pk)
        .order_by("-published_at")[:limit]
    )
