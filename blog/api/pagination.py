from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class PostPagination(PageNumberPagination):
    """
        Pagination for post lists.
        Query params:
        - page: page number (default 1)
        - page_size: override the default (max 50)
    Response shape:
    {
        "count": 120,
        "num_pages": 10,
        "current_page": 1,
        "page_size": 12,
        "next": "http://.../posts/?page=2",
        "previous": null,
        "results": [ ... ]
    }
    """

    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 50
    page_query_param = "page"

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "num_pages": self.page.paginator.num_pages,
                "current_page": self.page.number,
                "page_size": self.get_page_size(self.request),
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )
