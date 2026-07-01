from django.contrib import admin
from .models import *

@admin.register(NewsCategory)
class NewsCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
   

class NewsImageInline(admin.TabularInline):
    """
    Allows adding and editing news images directly from the News admin page.
    """
    model = NewsImage
    extra = 1  # Provides one extra empty form for new images

from django.contrib import admin
from django.utils.html import format_html
from .models import News, NewsImage


class NewsImageInline(admin.TabularInline):
    model = NewsImage
    extra = 0


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    """
    Admin configuration for the News model with auto notification support
    """

    # 📋 LIST VIEW
    list_display = (
        "title",
        "author",
        "published_date",
        "send_notification",
        "notification_delay_hours",
        "notification_datetime",
        "notification_status",
        "created_at",
    )

    list_filter = (
        "send_notification",
        "auto_notification_sent",
        "published_date",
        "author",
        "category",
    )

    search_fields = ("title", "content", "category__name")
    date_hierarchy = "published_date"

    inlines = [NewsImageInline]

    # 🔒 READ ONLY FIELDS
    readonly_fields = (
        "created_at",
        "updated_at",
        "notification_datetime",
        "auto_notification_sent",
    )

    # 🧩 FORM LAYOUT
    fieldsets = (
        (None, {
            "fields": (
                "category",
                "title",
                "content",
                "published_date",
                "author",
            )
        }),

        ("🔔 Notification", {
            "fields": (
                "send_notification",
                "notification_delay_hours",
                "notification_datetime",
                "notification_expire_at",
                "auto_notification_sent",
            )
        }),

        ("🕒 Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    # 🔍 QUERYSET PERMISSIONS
    def get_queryset(self, request):
        """
        Show all news for superuser,
        only own news for regular users.
        """
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(author=request.user)

    # ✍️ AUTO AUTHOR
    def save_model(self, request, obj, form, change):
        """
        Automatically set author.
        """
        if not obj.author:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    # 📊 CUSTOM STATUS COLUMN
    @admin.display(description="Notification Status")
    def notification_status(self, obj):
        if not obj.send_notification:
            return format_html("<span style='color:#999;'>Disabled</span>")

        if obj.auto_notification_sent:
            return format_html("<span style='color:green;'>Sent ✔</span>")

        if obj.notification_datetime:
            return format_html(
                "<span style='color:orange;'>Scheduled</span>"
            )

        return format_html("<span style='color:red;'>Invalid</span>")


@admin.register(NewsImage)
class NewsImageAdmin(admin.ModelAdmin):
    """
    Admin configuration for the NewsImage model (optional, but good practice).
    """
    list_display = ('__str__', 'news')
    list_filter = ('news',)
    search_fields = ('news__title',)