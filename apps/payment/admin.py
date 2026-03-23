from django.contrib import admin

from apps.payment.models import PaymentPlatformToken

@admin.register(PaymentPlatformToken)
class PaymentPlatformTokenAdmin(admin.ModelAdmin):
    list_display = [
        "id", "source", "expires_in",
        "date_created", "last_updated",
    ]
    list_display_links = [
        "id", "source", "expires_in"
    ]
