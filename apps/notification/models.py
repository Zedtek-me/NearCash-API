from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


from interfaces.models.base import BaseModel



class Notification(BaseModel):
    title = models.CharField(max_length=255)
    message = models.TextField()
    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    content_object = GenericForeignKey("content_type", "object_id")

    def __repr__(self):
        return f"Notification(title={self.title})"

    def __str__(self):
        return f"{self.title}"

    class Meta(BaseModel.Meta):
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]
