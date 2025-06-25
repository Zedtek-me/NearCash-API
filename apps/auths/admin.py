from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.auths.models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('first_name', 'last_name', 'email', 'username', 'status', 'is_superuser')
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
