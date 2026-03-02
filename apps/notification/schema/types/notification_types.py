import graphene
from graphene_django import DjangoObjectType
from ...constants import READ, UNREAD

from apps.notification.models import Notification


class NotificationType(DjangoObjectType):
    class Meta:
        model = Notification
        fields = "__all__"


class NotificationEnum(graphene.Enum):
    READ = READ
    UNREAD = UNREAD
