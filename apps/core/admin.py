from django.contrib import admin

from .models import Business

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
