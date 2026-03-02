import graphene
from graphql_jwt.decorators import login_required

from django.db import transaction

from ..types.notification_types import NotificationType, NotificationEnum

from utils.notifications.notifications import NotificationUtil


class UpdateNotification(graphene.Mutation):
    message = graphene.String()
    notification = graphene.Field(NotificationType)

    class Arguments:
        notification_id = graphene.String(required=True)
        status = NotificationEnum(required=True)

    @login_required
    @transaction.atomic
    def mutate(self, info, **kwargs):
        user = info.context.user
        notification = NotificationUtil.update_notification(user, kwargs)
        return UpdateNotification(
            message="Notification successfully updated!",
            notification=notification
        )



class Mutation(graphene.ObjectType):
    update_notification = UpdateNotification.Field(
        description="Updates notification to either 'READ' or 'UNREAD'"
    )
