from django.db import models

class BaseModel(models.Model):
    """
    Base model that provides common fields for all models.
    """
    date_created = models.DateTimeField(auto_now_add=True, verbose_name="Date Created")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="Last Updated")
    meta = models.JSONField(default=dict, blank=True, null=True, verbose_name="Metadata")

    class Meta:
        abstract = True
        ordering = ['-last_updated','-date_created']
