from django.contrib import admin

from .models import Wallet, Transaction, FinancialAsset, TransactionOpportunity

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('id', 'balance', 'date_created', 'last_updated')
    list_filter = ('date_created', 'last_updated')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'txn_ref', 'wallet_id', 'amount', 'charge', 'extra_charge', 'business',
        'vendor', 'client', 'date_created', 'last_updated', 'status', 'collection_mode',
        'status', 'description', 'txn_location', 'discounted'
    )
    search_fields = (
        'client__email', "client__username", "client__first_name", "client__last_name",
        'vendor__email', "vendor__username", "vendor__first_name", "vendor__last_name",
        'status', 'txn_ref', 'wallet_id', 'txn_location', 'category', 'description'
    )
    list_filter = ('date_created', 'last_updated', 'status', 'collection_mode', 'business')

@admin.register(FinancialAsset)
class FinancialAssetAdmin(admin.ModelAdmin):
    list_display = ('id', 'range', 'charge_rate', 'business', 'date_created', 'last_updated')
    search_fields = ('range', 'business__name', 'business__owner__email')
    list_filter = ('date_created', 'last_updated', 'range', 'business')


@admin.register(TransactionOpportunity)
class TransactionOpportunityAdmin(admin.ModelAdmin):
    list_display = [
        "id", "business", "transaction",
        "date_created", "last_updated"
    ]
    list_filter = ["business", "date_created", "last_updated"]
    search = [
        "business__name__icontains", "business__owner__email__icontains",
        "business__owner__first_name__icontains", "business__owner__last_name__icontains",
        "transaction__amount", "transaction__txn_ref",
    ]
