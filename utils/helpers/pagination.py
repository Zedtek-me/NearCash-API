from django.core.paginator import Paginator


class PaginationUtil:
    """Utility class for handling pagination."""

    @staticmethod
    def paginate(queryset, page_number: int, page_size: int):
        """
        Paginates the given queryset.

        :param queryset: The queryset to paginate.
        :param page_number: The page number to retrieve.
        :param page_size: The number of items per page.
        :return: A dictionary with paginated data and metadata.
        """
        paginator = Paginator(queryset, page_size)
        page = paginator.get_page(page_number)

        return {
            'items': list(page),
            'total_items': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page.number,
            'has_next': page.has_next(),
            'has_previous': page.has_previous(),
        }
