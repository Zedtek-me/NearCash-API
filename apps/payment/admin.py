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
        "id", "event_type", "source", "transaction"
    ]
    list_filter = [
        "source", "event_type"
    ]
    search_fields = [
        "id", "event_type__icontains", "source__icontains"
    ]
    fields = [
        "event_type", "source", "event", "transaction"
    ]
