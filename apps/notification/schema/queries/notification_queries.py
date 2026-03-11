import graphene
from graphql_jwt.decorators import login_required

from django.db.models import Q

from apps.notification.schema.types.notification_types import NotificationType

from utils.notifications.notifications import NotificationUtil
from utils.helpers.pagination import PaginationUtil
from utils.helpers.logs import logger

class Query(graphene.ObjectType):
    pagination = None

    notifications = graphene.List(
        NotificationType,
        id=graphene.String(required=False),
        user_id=graphene.String(required=False),
        business_id=graphene.String(required=False),
        search=graphene.String(required=False),
        status=graphene.String(required=False),
        page_number=graphene.Int(),
        page_count=graphene.Int()
    )

    @login_required
    def resolve_notifications(self, info, **kwargs):
        user_id = kwargs.pop("user_id", None)
        business_id = kwargs.pop("business_id", None)
        _id = kwargs.get("id")
        search = kwargs.pop("search", None)
        status = kwargs.pop("status", None)
        page_number = kwargs.get("page_number", 1)
        page_count = kwargs.get("page_count", 10)

        filters = {}
        search = Q()

        if search:
            search = Q(title__icontains=search) | Q(message__icontains=search)
        if _id:
            filters["id"] = _id
        if user_id:
            filters["user_id"] = user_id
        if business_id:
            filters["business_id"] = business_id
        if status:
            filters["status__iexact"] = status
        notifications_qs = NotificationUtil.fetch_notifications(
            **filters, search=search
        )

        paginated = PaginationUtil.paginate_notifications(
            notifications_qs, page_number, page_count
        )
        info.context.pagination = paginated
        return paginated.pop("items")
