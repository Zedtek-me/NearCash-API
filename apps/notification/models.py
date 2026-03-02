from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from .constants import READ, UNREAD


from interfaces.models.base import BaseModel



class Notification(BaseModel):
    STATUSES = (
        (READ, READ), (UNREAD, UNREAD)
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    object_id = models.PositiveIntegerField(null=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    content_object = GenericForeignKey("content_type", "object_id")
    status = models.CharField(
        choices=STATUSES, default=UNREAD, null=True, blank=True
    )

    def __repr__(self):
        return f"Notification(title={self.title})"

    def __str__(self):
        return f"{self.title}"

    class Meta(BaseModel.Meta):
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        db_table = "notifications"
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]
