from django.db import models
from django.contrib.gis.db.models import PointField
from django.utils.translation import gettext_lazy as _

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
    BUSINESS_TYPES = (
        ("LOCAL", "LOCAL"),
        ("FX", "FX")
    )
    name = models.CharField(max_length=255, unique=True)
    owner = models.ForeignKey(to="auths.User", on_delete=models.CASCADE, related_name="businesses")
    description = models.TextField(blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(null=True)
    currency = models.CharField(max_length=10, blank=True, null=True)
    business_type = models.CharField(
        max_length=100, choices=BUSINESS_TYPES, default="LOCAL"
    )
    parent_business_id = models.CharField(max_length=25, blank=True, null=True)
    status = models.CharField(
        max_length=20, default='ACTIVE', choices=STATUSES, db_index=True
    )
    geo_location = PointField(
        null=True, blank=True, db_index=True, verbose_name="Location Cordinates",
        geography=True, srid=4326
    )
    is_primary = models.BooleanField(default=False)
    is_online = models.BooleanField(default=True)
    available_liquidity = models.FloatField(
        null=True, help_text=(
            "POS Vendors are to set their available liquidity for the day\n"
            "giving room for vendor ranking based on liquidity availabilty too."
        )
    )

    class Meta(BaseModel.Meta):
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
    max_delivery_amount = models.FloatField(null=True)
    max_delivery_distance = models.FloatField(
        null=True, help_text="maximum distance a vendor can delivery cash -- in km"
    )

    class Meta(BaseModel.Meta):
        db_table = "business_transaction_policy"
        verbose_name = "business transaction policy"
        verbose_name_plural = "business transaction policies"

    def __repr__(self):
        return f"{self.name}->{self.id}{'->' + str(self.business) if self.business else ''}"

    def __str__(self):
        return f"{self.name}->{self.id}{'->' + str(self.business) if self.business else ''}"

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


class BusinessClient(BaseModel):
    """
    Records all clients that have patronized businesses.
    Clients could be added to a category within a business, in order
    to apply a different policy to that category.
    """
    category = models.ForeignKey(
        to="BusinessClientCategory", on_delete=models.SET_NULL, null=True,
        help_text="category this client belongs to"
    )
    client = models.ForeignKey(
        to="auths.User", on_delete=models.CASCADE, null=True,
        help_text="The actual client added to this category"
    )
    business = models.ForeignKey(to="Business", on_delete=models.CASCADE, null=True)
    last_patronized = models.DateTimeField(null=True)

    def save(self, *args, **kwargs):
        if self.category and not self.business:
            self.business = self.category.business
        super().save(*args, **kwargs)

    def __repr__(self):
        return f"{self.business} -> {self.client}"

    def __str__(self):
        return f"{self.business} -> {self.client}"

    class Meta(BaseModel.Meta):
        db_table = "business_client"
        verbose_name = "business client"
        verbose_name_plural = "business clients"
        constraints = [
            models.UniqueConstraint(
                fields=["business", "client"],
                name="category_business_client_constraint",
                violation_error_message="Client is already a patron of this business!"
            )
        ]



class CurrentLocation(BaseModel):
    """
    Records the last known location of both a business owner
    and their clients.
    """
    class CurrentLocationType(models.TextChoices):
        VENDOR = "Vendor"
        CLIENT = "Client"


    user = models.ForeignKey(
        to="auths.User", on_delete=models.CASCADE, null=True,
        related_name="current_locations"
    )
    business = models.ForeignKey(
        to="Business", on_delete=models.CASCADE, null=True,
        related_name="current_locations"
    )
    location = PointField(
        null=True, blank=True, db_index=True, verbose_name="Location Cordinates",
        geography=True, srid=4326
    )
    location_type = models.CharField(
        max_length=20, choices=CurrentLocationType.choices,
        default=CurrentLocationType.VENDOR, db_index=True
    )

    def __str__(self):
        return f"{self.user} - {self.location_type}"
    
    class Meta(BaseModel.Meta):
        db_table = "current_location"
        verbose_name = "current location"
        verbose_name_plural = "current locations"
        ordering = ["-date_created"]
