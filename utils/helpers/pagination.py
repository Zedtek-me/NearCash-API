from django.core.paginator import Paginator
from django.db.models.query import QuerySet


class PaginationUtil:
    """Utility class for handling pagination."""

    @classmethod
    def paginate(
        cls, queryset: QuerySet, page_number: int, page_size: int
    ):
        """
        Paginates the given queryset.

        :param queryset: The queryset to paginate.
        :param page_number: The page number to retrieve.
        :param page_size: The number of items per page.
        :return: A dictionary with paginated data and metadata.
        """
        paginator = Paginator(queryset, page_size)
        page = paginator.get_page(page_number)

        pagination_data = {
            "items": list(page),
            "total_items": paginator.count,
            "total_pages": paginator.num_pages,
            "per_page": page_size,
            "current_page": page.number,
            "next_page": page.next_page_number() if page.has_next() else None,
            "previous_page": page.previous_page_number() if page.has_previous() else None,
        }

        return pagination_data

    @classmethod
    def paginate_notifications(
        cls, queryset: QuerySet, page_number: int, page_size: int
    ):
        """
        Paginates notifications queryset and adds is_read annotation.

        :param queryset: The notifications queryset to paginate.
        :param page_number: The page number to retrieve.
        :param page_size: The number of items per page.
        :return: A dictionary with paginated notifications and metadata.
        """
        unread_notif_queryset = queryset.filter(status__iexact="unread")
        read_notif_queryset = queryset.filter(status__iexact="read")
        paginated_data = cls.paginate(queryset, page_number, page_size)
        paginated_data.update({
            "total_unread_items": unread_notif_queryset.count(),
            "total_read_items": read_notif_queryset.count()
        })
        return paginated_data
