from django.contrib import admin
from .models import *



class NoticeInline(admin.TabularInline):  # or admin.StackedInline for bigger form
    model = Notice
    extra = 1
    fields = ("title", "description", "pdf", "link", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")


@admin.register(GovernmentJob)
class GovernmentJobAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'organization',
        'department',
        'get_positions',   # custom method for many-to-many
        'location',
        'deadline',
        'posted_on',
    )
    list_filter = (
        'organization',
        'department',
        'positions',   # now plural
        'location',
        'posted_on',
        'deadline',
    )
    search_fields = (
        'title',
        'description',
        'organization__name',
        'department__name',
        'positions__name',   # updated for M2M
        'location',
    )
    date_hierarchy = 'posted_on'
    ordering = ('-posted_on',)
    inlines = [NoticeInline] 
    fieldsets = (
        (None, {
            'fields': ('title', 'organization', 'department', 'positions', 'location')
        }),
        ('Job Details', {
            'fields': ('description', 'official_link', 'pdf')
        }),
        ('Important Dates', {
            'fields': ('deadline',)
        }),
    )

    filter_horizontal = ('positions',)  # adds a nice widget for selecting multiple

    def get_positions(self, obj):
        return ", ".join([pos.name for pos in obj.positions.all()])
    get_positions.short_description = "Positions"

@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ("title", "government_job", "created_at", "updated_at")
    search_fields = ("title", "government_job__title")
    list_filter = ("created_at", "updated_at", "government_job")
    ordering = ("-created_at",)