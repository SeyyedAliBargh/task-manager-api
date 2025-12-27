from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
class DefaultPagination(PageNumberPagination):
    page_size = 10
    
    def get_paginated_response(self, data):
        return Response(
            {
                "page_size": self.page_size,
                "total_objects": self.page.paginator.count,
                "total_pages": self.page.paginator.num_pages,
                "current_page_number": self.page.number,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )
    