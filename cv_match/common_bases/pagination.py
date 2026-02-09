from rest_framework import pagination
from rest_framework.response import Response


class PaginationWithTotalPage(pagination.PageNumberPagination):
    page_size_query_param = 'page_size'
    page_size = 100

    def get_paginated_response(self, data):
        response = Response({
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'results': data
        })
        return response
