from django.db import models
from django.contrib.gis.db.models import PointField

from interfaces.models.base import BaseModel


class Business(BaseModel):
    STATUSES = (
        ("ACTIVE", "ACTIVE"),
        ("INACTIVE", "INACTIVE"),
        ("DELETED", "DELETED"),
    )
    name = models.CharField(max_length=255, unique=True)
    owner = models.ForeignKey(to="auths.User", on_delete=models.CASCADE, related_name="businesses")
    description = models.TextField(blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    currency = models.CharField(max_length=10, blank=True, null=True)
    parent_business_id = models.CharField(max_length=25, blank=True, null=True)
    status = models.CharField(
        max_length=20, default='ACTIVE', choices=STATUSES, db_index=True
    )
    _location = PointField(
        null=True, blank=True, db_index=True, verbose_name="Location Cordinates",
        geography=True, srid=4326
    )

    class Meta:
        db_table = 'business'
        verbose_name = "Business"
        verbose_name_plural = "Businesses"

    def __str__(self):
        return f"{self.name}"
