from django.contrib import admin

from .models import Notification



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
        "title", "message", "content_type", "object_id", "status", "meta"
        "date_created", "last_updated"
    ]
