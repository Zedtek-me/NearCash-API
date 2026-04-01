from django.contrib import admin

from .models import (
    Business, BusinessTransactionPolicy, BusinessClientCategory,
    BusinessClient, CurrentLocation
)

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'owner', 'date_created', 'last_updated', 'country', 'currency', 'status',
        'parent_business_id', "available_liquidity", "is_primary", "is_online", "business_type"
    )
    search_fields = (
        'name__icontains', 'owner__email__iexact', 'owner__username__icontains',
        'owner__first_name__icontains', 'owner__last_name__icontains',
        'country__icontains', 'currency', "business_type__icontains"
    )
    list_filter = ('date_created', 'last_updated', "business_type")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('owner')


@admin.register(BusinessClientCategory)
class BusinessClientCategoryAdmin(admin.ModelAdmin):
    list_display = [
        "id", "name", "description", "business", "txn_policy"
    ]

    search_fields = [
        "name", "business__name", "txn_policy__name"
    ]


@admin.register(BusinessTransactionPolicy)
class BusinessTransactionPolicy(admin.ModelAdmin):
    list_display = [
        "id", "name", "description", "cash_collection_mode", "meet_up_charge", "business",
        "max_delivery_distance", "max_delivery_amount"
    ]
    search_fields = [
        "name__icontains", "cash_collection_mode__icontains", "meet_up_charge"
    ]
    fields = [
        "name", "description", "cash_collection_mode", "meet_up_charge", "business",
        "max_delivery_distance", "max_delivery_amount", "meta",
    ]


@admin.register(BusinessClient)
class BusinessClientAdmin(admin.ModelAdmin):
    list_display = [
        "id", "category", "client", "business", "last_patronized"
    ]
    search_fields = [
        "name", "category__name__icontains", "client__email__iexact", "client__first_name__icontains",
        "client__last_name__icontains", "business__name__icontains"
    ]



@admin.register(CurrentLocation)
class CurrentLocationAdmin(admin.ModelAdmin):
    list_display = [
        "id", "user", "business", "location_type"
    ]
    search_fields = [
        "user__email__iexact", "user__first_name__icontains", "user__last_name__icontains",
        "business__name__icontains", "location_type__icontains", "location_type__icontains"
    ]
    list_filter = ("date_created", "last_updated", "location_type")
    readonly_fields = ("location_type", "id")
