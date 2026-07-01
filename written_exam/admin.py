from django.contrib import admin
from .models import (
    RootExam,
    WrittenExam,
    WrittenQuestion,
    SubWrittenQuestion,
    Passage
)

@admin.register(RootExam)
class RootExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'exam_mode', 'exam_type', 'exam_date', 'organization', 'department', 'position', 'created_by', 'created_at')
    list_filter = ('exam_mode', 'exam_type', 'organization', 'department', 'position')
    search_fields = ('title', 'description')

@admin.register(WrittenExam)
class WrittenExamAdmin(admin.ModelAdmin):
    list_display = ('root_exam', 'subject', 'total_questions', 'total_marks', 'created_at')
    list_filter = ('subject',)
    search_fields = ('root_exam__title', 'subject__name')

@admin.register(WrittenQuestion)
class WrittenQuestionAdmin(admin.ModelAdmin):
    list_display = ('written_exam', 'subject', 'question_number', 'marks', 'has_sub_questions', 'created_at')
    list_filter = ('subject', 'written_exam')
    search_fields = ('question_text',)
    # autocomplete_fields = ['passage']

@admin.register(SubWrittenQuestion)
class SubWrittenQuestionAdmin(admin.ModelAdmin):
    list_display = ('parent_question', 'number', 'marks', 'created_at')
    search_fields = ('text',)
    raw_id_fields = ['parent_question']

@admin.register(Passage)
class PassageAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'is_image', 'created_at')
    search_fields = ('title', 'text')
    list_filter = ('subject', 'is_image')
