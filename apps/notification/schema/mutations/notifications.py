import graphene
from graphql_jwt.decorators import login_required

from django.db import transaction

from ..types.notification_types import NotificationType, NotificationEnum
from apps.notification.models import FirebaseDevice
from utils.helpers.exception import CustomException

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



class RegisterFirebaseDevice(graphene.Mutation):
    """Associates a Firebase installation with the authenticated user."""

    message = graphene.String()
    installation_id = graphene.String()

    class Arguments:
        installation_id = graphene.String(required=True)
        platform = graphene.String(required=False, default_value="web")

    @login_required
    @transaction.atomic
    def mutate(self, info, **kwargs):
        installation_id = NotificationUtil.register_firebase_device(
            info.context.user, kwargs.get("installation_id", ""),
            platform=kwargs.get("platform", "web")
        )
        return RegisterFirebaseDevice(
            message=(
                "Firebase device successfully registered!"
            ),
            installation_id=installation_id
        )


class Mutation(graphene.ObjectType):
    update_notification = UpdateNotification.Field(
        description="Updates notification to either 'READ' or 'UNREAD'"
    )
    register_firebase_device = RegisterFirebaseDevice.Field(
        description="Registers a Firebase installation for the authenticated user."
    )
