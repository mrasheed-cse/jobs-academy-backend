from django.contrib import admin
from .models import ImportJob

@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display  = ['pk', 'exam_title', 'status', 'processed_pages', 'total_pages', 'questions_found', 'created_at']
    list_filter   = ['status']
    readonly_fields = ['created_at', 'finished_at', 'error_log']
