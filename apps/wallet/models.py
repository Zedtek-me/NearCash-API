from django.db import models
from django.conf import settings

from interfaces.models.base import BaseModel
from utils.helpers.validators import Validator

from .constants import (
    COLLECTION_MODES, IN_PROGRESS, CANCELLED,
    FULFILLED, MEETUP, OUTLET_WALK_IN, TXN_STATUSES
)

class FinancialAsset(BaseModel):
    business = models.ForeignKey(
        to="core.business", on_delete=models.CASCADE, related_name="assets"
    )
    range = models.CharField(
        max_length=255,
        help_text="The range of the asset, e.g., '1000-5000', '5000-10000', etc."
    )
    charge_rate = models.FloatField(
        null=True, default=100.0, validators=[Validator.validate_number]
    )

    class Meta:
        db_table = 'financial_asset'
        verbose_name = "Financial Asset"
        verbose_name_plural = "Financial Assets"

    def __str__(self):
        return f"{self.business.name}->{self.range}"

class Transaction(BaseModel):
    txn_ref = models.CharField(
        max_length=100, unique=True, help_text="Unique reference for the transaction"
    )
    client = models.ForeignKey(
        to=settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="client_transactions",
        related_query_name="client_transactions", null=True
    )
    vendor = models.ForeignKey(
        to=settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="vendor_transactions",
        related_query_name="vendor_transactions", null=True
    )
    asset = models.ForeignKey(
        to="wallet.FinancialAsset", on_delete=models.CASCADE, related_name="transactions"
    )
    charge = models.FloatField(help_text="amount charged for the txn")
    currency = models.CharField(max_length=15, default="NGN")
    business = models.ForeignKey(
        to="core.Business", on_delete=models.SET_NULL, related_name="transactions", null=True
    )
    collection_mode = models.CharField(
        max_length=255, choices=COLLECTION_MODES, db_index=True, null=True
    )
    txn_location = models.CharField(
        max_length=255, help_text="Location where the transaction is to be fulfilled"
    )
    discounted = models.BooleanField(default=False)
    extra_charge = models.JSONField(
        default=dict, blank=True, null=True,
        help_text="Should contain amount and reason keys for the extra charge"
    )
    status = models.CharField(
        max_length=255, choices=TXN_STATUSES, default=IN_PROGRESS, db_index=True
    )
    description = models.TextField(null=True)
    category = models.CharField(
        max_length=255, null=True, blank=True,
        help_text="help determines whether it is a product or service(system) txn"
    )
    wallet_id = models.CharField(
        max_length=25, null=True, blank=True,
        help_text="ID of the wallet used for the transaction"
    )
    
    class Meta:
        db_table = 'transaction'
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"

class Wallet(BaseModel):
    """
    This model would represent the wallet of the
    vendors on the platform, from where the system is meant to charge vendors
    per transaction they make.
    For a start, vendors would not be charged until they get to a certain
    txn fulfilment threshold or customer base threshold -- to be decided later.
    """
    business_id = models.CharField(
        max_length=25, help_text="Unique identifier for the business that owns the wallet"
    )
    balance = models.FloatField(default=0.0)
    status = models.CharField(
        max_length=255, null=True, blank=True
    )
    currency = models.CharField(
        max_length=15, default="NGN", help_text="Currency of the wallet balance"
    )

    class Meta:
        db_table = 'wallet'
        verbose_name = "wallet"
        verbose_name_plural = "wallets"
