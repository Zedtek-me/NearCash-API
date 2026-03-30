from django.contrib import admin

from apps.payment.models import PaymentPlatformToken, PaymentPlatformEvent

@admin.register(PaymentPlatformToken)
class PaymentPlatformTokenAdmin(admin.ModelAdmin):
    list_display = [
        "id", "source", "expires_in",
        "date_created", "last_updated",
    ]
    list_display_links = [
        "id", "source", "expires_in"
    ]
    search_fields = [
        "source__icontains", "id"
    ]


@admin.register(PaymentPlatformEvent)
class PaymentPlatformEventAdmin(admin.ModelAdmin):
    list_display = [
        "id", "source", "transaction"
    ]
    list_filter = [
        "source"
    ]
    search_fields = [
        "id", "source__icontains"
    ]
    fields = [
        "source", "event", "transaction"
    ]
