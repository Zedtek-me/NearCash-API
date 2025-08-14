from django.contrib import admin

from .models import Wallet, Transaction, FinancialAsset

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('id', 'balance', 'date_created', 'last_updated')
    list_filter = ('date_created', 'last_updated')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'txn_ref', 'wallet_id', 'amount', 'charge', 'extra_charge', 'vendor', 'client', 'date_created',
        'last_updated', 'status', 'collection_mode', 'status', 'description', 'txn_location',
        'discounted'
    )
    search_fields = (
        'client__email', "client__username", "client__first_name", "client__last_name",
        'vendor__email', "vendor__username", "vendor__first_name", "vendor__last_name",
        'status', 'txn_ref', 'wallet_id', 'txn_location', 'category', 'description'
    )
    list_filter = ('date_created', 'last_updated', 'status', 'collection_mode')

@admin.register(FinancialAsset)
class FinancialAssetAdmin(admin.ModelAdmin):
    list_display = ('id', 'range', 'charge_rate', 'business', 'date_created', 'last_updated')
    search_fields = ('range', 'business__name', 'business__owner__email')
    list_filter = ('date_created', 'last_updated', 'range', 'business')
