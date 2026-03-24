from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.auths.models import User, UserProfile

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('id','first_name', 'last_name', 'email', 'username', 'status', 'is_superuser')
    list_filter = ("first_name", "last_name", "email", "username", "status", "is_superuser")
    search_fields = ("id","first_name", "last_name", "email", "username")

    fieldsets = fieldsets = (
        (None, {'fields': ('email', 'first_name', 'last_name', 'username', 'status', 'meta', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'username', 'password1', 'password2'),
        }),
    )


@admin.register(UserProfile)
class UserProfileAmin(admin.ModelAdmin):
    list_display = [
        "user", "phone_number", "remittance_account_number",
        "remittance_bank_code", "remittance_bank_name",
        "nin", "bvn"
    ]
    search_fields = [
        "user__email__iexact", "user__first_name__icontains",
        "user__last_name__icontains", "phone_number__icontains",
        "remittance_bank_name__icontains", "remittances_account_number__icontains",
        "nin__icontains", "bvn__icontains"
    ]
