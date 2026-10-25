from django.contrib import admin

from .models import Notification, FirebaseDevice



@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        "id", "title", "message", "content_type", "object_id", "status",
        "date_created", "last_updated"
    ]
    list_filter = [
        "date_created", "last_updated", "status"
    ]
    search_fields = [
        "title__icontains", "message__icontains", "content_type__model__icontains",
        "status__icontains"
    ]
    readonly_fields = [
        "date_created", "last_updated", "content_type", "object_id", "title", "message"
    ]
    fields = [
        "title", "message", "content_type", "object_id", "status", "meta",
        "date_created", "last_updated"
    ]


@admin.register(FirebaseDevice)
class FirebaseDeviceAdmin(admin.ModelAdmin):
    list_display = [
        "user", "installation_id", "platform", "token",
        "date_created", "last_updated"
    ]
    list_filter = [
        "date_created", "last_updated", "user"
    ]
    search_fields = [
        "installation_id__icontains",
        "user__first_name__icontains",
        "user__last_name__icontains",
        "user__email__icontains",
        "user__id"
    ]
