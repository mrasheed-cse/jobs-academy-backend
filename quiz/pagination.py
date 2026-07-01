from rest_framework.pagination import PageNumberPagination

class CustomPageNumberPagination(PageNumberPagination):
    page_size = 10  # Set a default page size

    def get_page_size(self, request):
        # Get the page size from query parameters or use the default
        page_size = request.query_params.get('page_size', self.page_size)
        try:
            # Convert page size to int and limit max size
            return min(int(page_size), 100)  # Limit max size to 100
        except (ValueError, TypeError):
            return self.page_size  # Fallback to the default page size
