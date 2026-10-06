from rest_framework.exceptions import ValidationError


class PostOrderingMixin:
    """
    Provides consistent ordering behavior across views that list posts.
    """

    ORDER_MAP = {
        "newest": "-published_at",
        "oldest": "published_at",
        "most_viewed": "-views_count",
        "most_liked": "-like_count",
        "most_commented": "-comment_count",
        "title_asc": "title",
        "title_desc": "-title",
    }
    DEFAULT_ORDER = "-published_at"

    def apply_ordering(self, qs, request):
        ordering = request.query_params.get("ordering")
        if ordering and ordering not in self.ORDER_MAP:
            raise ValidationError(
                {
                    "ordering": (
                        f'Invalid value "{ordering}". '
                        f"Choose from: {', '.join(self.ORDER_MAP.keys())}"
                    )
                }
            )
        order_field = self.ORDER_MAP.get(ordering, self.DEFAULT_ORDER)
        return qs.order_by(order_field)
