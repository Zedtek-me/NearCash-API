from django.db import models
from django.contrib.gis.db.models import PointField

from interfaces.models.base import BaseModel

from .constants import (
    MEET_UP, STORE_WALK_IN, MEET_UP_AND_STORE_WALK_IN,
    ACTIVE, INACTIVE, DELETED

)

class Business(BaseModel):
    STATUSES = (
        (ACTIVE, ACTIVE),
        (INACTIVE, INACTIVE),
        (DELETED, DELETED),
    )
    name = models.CharField(max_length=255, unique=True)
    owner = models.ForeignKey(to="auths.User", on_delete=models.CASCADE, related_name="businesses")
    description = models.TextField(blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(null=True)
    currency = models.CharField(max_length=10, blank=True, null=True)
    parent_business_id = models.CharField(max_length=25, blank=True, null=True)
    status = models.CharField(
        max_length=20, default='ACTIVE', choices=STATUSES, db_index=True
    )
    geo_location = PointField(
        null=True, blank=True, db_index=True, verbose_name="Location Cordinates",
        geography=True, srid=4326
    )

    class Meta:
        db_table = 'business'
        verbose_name = "Business"
        verbose_name_plural = "Businesses"

    def __str__(self):
        return f"{self.name}"

class BusinessTransactionPolicy(BaseModel):
    CASH_COLLECTION_CHOICES = (
        (MEET_UP, MEET_UP),
        (STORE_WALK_IN, STORE_WALK_IN),
        (MEET_UP_AND_STORE_WALK_IN, MEET_UP_AND_STORE_WALK_IN)
    )
    name = models.CharField(max_length=255, null=True)
    description = models.TextField(
        null=True, default="General Policy"
    )
    business = models.ForeignKey(to="Business", on_delete=models.CASCADE, null=True)
    cash_collection_mode = models.CharField(
        max_length=255, null=True, choices=CASH_COLLECTION_CHOICES,
        default=STORE_WALK_IN
    )
    meet_up_charge = models.FloatField(default=0.0, null=True)

    class Meta(BaseModel.Meta):
        db_table = "business_transaction_policy"
        verbose_name = "business transaction policy"
        verbose_name_plural = "business transaction policies"

    def __repr__(self):
        return f"{self.name}->{self.id}"

    def __str__(self):
        return f"{self.name}->{self.id}"

class BusinessClientCategory(BaseModel):
    """
    When a vendor starts having loyal and recurring clients,
    they may decide to categorize some clients, and specify a different
    transaction policy for those clients; hence, this model.
    """
    name = models.CharField(max_length=255, null=True)
    description = models.TextField(null=True)
    business = models.ForeignKey(
        to="Business", on_delete=models.CASCADE, null=True,
        help_text="Business that created this category"
    )
    txn_policy = models.ForeignKey(
        to="BusinessTransactionPolicy", on_delete=models.SET_NULL, null=True,
        help_text="The transaction policy that applies to the clients in this category"
    )

    def __repr__(self):
        return f"{self.name}->{self.id}"

    def __str__(self):
        return f"{self.name}->{self.id}"

    class Meta(BaseModel.Meta):
        db_table = "business_client_category"
        verbose_name = "categry for clients"
        verbose_name_plural = "category for clients"


class CategoryClient(BaseModel):
    """
    A client can be added to multiple category as long as
    the business that owns the categories differs; i.e,
    a client can't be added to multiple categories in the same business.
    """
    category = models.ForeignKey(
        to="BusinessClientCategory", on_delete=models.CASCADE, null=True,
        help_text="category this client belongs to"
    )
    client = models.ForeignKey(
        to="auths.User", on_delete=models.CASCADE, null=True,
        help_text="The actual client added to this category"
    )
    business = models.ForeignKey(to="Business", on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        if self.category and not self.business:
            self.business = self.category.business
        super().save(*args, **kwargs)

    def __repr__(self):
        return f"{self.category} -> {self.client}"

    def __str__(self):
        return f"{self.category} -> {self.client}"

    class Meta(BaseModel.Meta):
        db_table = "category_client"
        verbose_name = "client"
        verbose_name_plural = "clients"
        constraints = [
            models.UniqueConstraint(
                fields=["business", "client"],
                name="category_business_client_constraint",
                violation_error_message="Client already belongs to a category in this business!"
            )
        ]
