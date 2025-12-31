from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class DefaultPagination(PageNumberPagination):
    """
    Custom pagination class for API responses.

    - Sets a default page size of 10.
    - Provides a structured paginated response including:
        * Page size
        * Total number of objects
        * Total number of pages
        * Current page number
        * Links to next and previous pages
        * Paginated results
    """

    # Default number of items per page
    page_size = 10

    def get_paginated_response(self, data):
        """
        Return a custom paginated response.

        - Includes metadata about pagination.
        - Provides navigation links (next/previous).
        - Returns the actual paginated results.
        """
        return Response(
            {
                "page_size": self.page_size,  # Number of items per page
                "total_objects": self.page.paginator.count,  # Total items in queryset
                "total_pages": self.page.paginator.num_pages,  # Total number of pages
                "current_page_number": self.page.number,  # Current page index
                "next": self.get_next_link(),  # Link to next page
                "previous": self.get_previous_link(),  # Link to previous page
                "results": data,  # Paginated results
            }
        )