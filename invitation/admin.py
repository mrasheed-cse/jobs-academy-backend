from django.contrib import admin
from .models import ExamInvite

@admin.register(ExamInvite)
class ExamInviteAdmin(admin.ModelAdmin):
    list_display = ('exam', 'invited_by', 'invited_user', 'token', 'invited_at', 'is_accepted')
    search_fields = ('exam__title', 'invited_by__username', 'invited_user__email', 'token')
    list_filter = ('is_accepted', 'invited_at')
    readonly_fields = ('token', 'invited_at')

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('invited_by', 'exam', 'invited_user')
        return self.readonly_fields
