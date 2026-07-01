from django.contrib import admin
from .models import DeviceToken, UserActivity, NotificationLog, NotificationClick


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "device_type", "device_id",
        "token", "is_active", "ip_address", "updated_at", "created_at"
    )
    list_filter = ("device_type", "is_active", "updated_at", "created_at")
    search_fields = ("token", "device_id", "user__username", "ip_address")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-updated_at",)


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "device", "path", "method",
        "ip_address", "timestamp"
    )
    list_filter = ("method", "timestamp")
    search_fields = ("user__username", "device__device_id", "path", "ip_address")
    readonly_fields = ("timestamp",)
    ordering = ("-timestamp",)


class NotificationClickInline(admin.TabularInline):
    """
    Show related clicks in NotificationLog.
    """
    model = NotificationClick
    extra = 0
    readonly_fields = ("user", "device", "target_url", "clicked_at", "ip_address", "user_agent")
    can_delete = False


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "success_count", "failure_count", "sent_at")
    list_filter = ("sent_at",)
    search_fields = ("title", "body")
    readonly_fields = ("sent_at",)
    ordering = ("-sent_at",)
    inlines = [NotificationClickInline]


@admin.register(NotificationClick)
class NotificationClickAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "device", "notification",
        "target_url", "clicked_at", "ip_address"
    )
    list_filter = ("clicked_at",)
    search_fields = (
        "user__username", "device__device_id", "notification__title",
        "target_url", "ip_address", "user_agent"
    )
    readonly_fields = ("clicked_at",)
    ordering = ("-clicked_at",)
