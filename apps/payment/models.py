from django.db import models
from django.utils import timezone

from interfaces.models.base import BaseModel


class PaymentPlatformToken(BaseModel):
    TOKEN_SOURCES = [
        ("FLUTTERWAVE", "FLUTTERWAVE"),
        ("PAYSTACK", "PAYSTACK"),
        ("ANCHOR", "ANCHOR")
    ]
    token = models.TextField(null=True, blank=True)
    source = models.CharField(
        max_length=255, choices=TOKEN_SOURCES,
        default="FLUTTERWAVE", null=True, blank=True
    )
    expires_in = models.DurationField(
        null=True, blank=True, default=timezone.timedelta(seconds=600)
    )


    class Meta(BaseModel.Meta):
        verbose_name = "payment_platform_token"
        verbose_name_plural = "payment_platform_tokens"
        db_table = "payment_platform_token"

    def __str__(self):
        return f"{self.source} <--> expires in {self.expires_in.min}"


    @classmethod
    def fetch_token_info(cls, platform: str):
        return cls.objects.filter(source__icontains=platform).first()
