from django.contrib import admin

from .models import (
    Business, BusinessTransactionPolicy, BusinessClientCategory,
    CategoryClient
)

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'owner', 'date_created', 'last_updated', 'country', 'currency', 'status',
        'parent_business_id'
    )
    search_fields = (
        'name', 'owner__email', 'owner__username', 'owner__first_name', 'owner__last_name',
        'country', 'currency'
    )
    list_filter = ('date_created', 'last_updated')

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
        "id", "name", "description", "cash_collection_mode", "meet_up_charge"
    ]
    search_fields = [
        "name", "cash_collection_mode", "meet_up_charge"
    ]


@admin.register(CategoryClient)
class CategoryClientAdmin(admin.ModelAdmin):
    list_display = [
        "id", "category", "client", "business"
    ]
    search_fields = [
        "name", "category__name", "client__email", "client__first_name",
        "client__last_name", "business__name"
    ]
