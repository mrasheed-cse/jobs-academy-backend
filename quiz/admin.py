from django.contrib import admin
from .models import *
import nested_admin
from django.utils.html import format_html


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')



class QuestionOptionInline(nested_admin.NestedTabularInline):
    model = QuestionOption
    # extra = 4  # Number of extra forms to display in the admin
    classes = ['collapse']

class QuestionInline(nested_admin.NestedTabularInline):
    model = Question
    # extra = 0  # Number of extra forms to display in the admin
    inlines = [QuestionOptionInline]
    
    
@admin.register(QuestionUsage)
class QuestionUsageAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'exam', 'year')
    list_filter = ('exam', 'year')
    search_fields = ('question__text', 'exam')

    def question_text(self, obj):
        return obj.question.text
    question_text.short_description = 'Question Text'
    
class QuestionInline(admin.TabularInline):
    model = Exam.questions.through  # Assuming a Many-to-Many relationship
    extra = 0  # No extra empty fields 

class ExamQuestionInline(admin.TabularInline):  # Renamed here
    model = Exam.questions.through
    extra = 0
    
    
@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'total_questions', 'status', 'created_by', 'created_at', 'starting_time', 'last_date')
    list_filter = ('category',)  # Filters by category and status
    search_fields = ('title', 'category__name', 'created_by__username')  # Enables search by title, category name, and creator's username
    readonly_fields = ('status', 'created_at', 'updated_at')  # Makes non-editable fields read-only
    ordering = ('-created_at',)


    inlines = [QuestionInline]
    def status(self, obj):
        """Display current status of the exam."""
        return obj.status  # Uses the `status` property from the model
    status.short_description = "Exam Status"




@admin.register(ExamCategory)
class ExamCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'exam_count')  # Display the name and count of exams in each category
    search_fields = ('name',)  # Allows search by category name
    ordering = ('name',)  # Orders categories alphabetically
    readonly_fields = ('exam_count',)  # Makes exam_count a read-only field in admin

    def exam_count(self, obj):
        """Display number of exams in each category."""
        return obj.exam_count  # Uses the `exam_count` property from the model
    exam_count.short_description = "Number of Exams"             

class StatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'exam', 'status', 'reviewed_by')  # Display important fields
    list_filter = ('status', 'reviewed_by')  # Add filters for status and reviewer
    search_fields = ('exam__title',)  # Enable search on exam title and description
    autocomplete_fields = ['reviewed_by']  # Allows selecting from a long list of users easily
    readonly_fields = ['exam']  # Make exam field read-only
    list_select_related = ('exam', 'reviewed_by')  # Optimizes queries by selecting related objects

    def get_queryset(self, request):
        """Optimize queries by selecting related exam and reviewer"""
        queryset = super().get_queryset(request)
        return queryset.select_related('exam', 'reviewed_by')

admin.site.register(Status, StatusAdmin)      
                
@admin.register(ExamDifficulty)
class ExamDifficultyAdmin(admin.ModelAdmin):
    list_display = ('exam', 'difficulty1_percentage', 'difficulty2_percentage', 'difficulty3_percentage', 'difficulty4_percentage', 'difficulty5_percentage', 'difficulty6_percentage')
    search_fields = ('exam__title',)



from django.contrib.admin import SimpleListFilter

class PastExamFilter(SimpleListFilter):
    title = 'Past Exam'
    parameter_name = 'past_exam'

    def lookups(self, request, model_admin):
        from .models import PastExam
        return [(exam.id, exam.title) for exam in PastExam.objects.all()]

    def queryset(self, request, queryset):
        from .models import PastExamQuestion
        if self.value():
            question_ids = PastExamQuestion.objects.filter(
                past_exam_id=self.value()
            ).values_list('question_id', flat=True)
            return queryset.filter(id__in=question_ids)
        return queryset

class LiveExamFilter(SimpleListFilter):
    title = 'Live Exam'
    parameter_name = 'live_exam'

    def lookups(self, request, model_admin):
        from .models import Exam
        return [(exam.exam_id, exam.title) for exam in Exam.objects.all()]

    def queryset(self, request, queryset):
        from .models import ExamQuestion
        if self.value():
            question_ids = ExamQuestion.objects.filter(
                exam_id=self.value()
            ).values_list('question_id', flat=True)
            return queryset.filter(id__in=question_ids)
        return queryset



from django.utils.html import format_html, mark_safe
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 
        'text_snippet', 
        'question_image_preview', 
        'get_options',
        'get_exam_names', 
        'category', 
        'difficulty_level', 
        'marks', 
        'status', 
        'created_by', 
        'reviewed_by', 
        'created_at', 
        'updated_at'
    )
    list_filter = ('difficulty_level', 'status', 'category')
    search_fields = ('text', 'remarks')
    readonly_fields = ('created_at', 'updated_at', 'question_image_preview')
    ordering = ('-created_at',)

    def text_snippet(self, obj):
        return obj.text[:50] + "..." if obj.text and len(obj.text) > 50 else obj.text
    text_snippet.short_description = 'Question'

    def question_image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="auto" />', obj.image.url)
        return "No image"
    question_image_preview.short_description = 'Image Preview'

    def get_options(self, obj):
        output_lines = []

        # Regular options
        direct_options = obj.options.all()
        if direct_options.exists():
            output_lines.append("<u>Regular Options:</u>")
            output_lines.extend([
                f"<b>{opt.text}</b> {'✅' if opt.is_correct else ''}"
                for opt in direct_options
            ])

        # Past Exam Options
        past_exam_questions = PastExamQuestion.objects.filter(question=obj)
        past_exam_options = PastExamQuestionOption.objects.filter(
            question__in=past_exam_questions
        ).select_related('option')

        if past_exam_options.exists():
            output_lines.append("<u>Past Exam Options:</u>")
            output_lines.extend([
                f"<b>{po.option.text}</b> {'✅' if po.option.is_correct else ''}"
                for po in past_exam_options
            ])

        # Exam Options
        try:
            exam_options = ExamQuestionOption.objects.filter(exam_question=obj).select_related('option')
            if exam_options.exists():
                output_lines.append("<u>Exam Options:</u>")
                output_lines.extend([
                    f"<b>{eo.option.text}</b> {'✅' if eo.option.is_correct else ''}"
                    for eo in exam_options
                ])
        except:
            pass

        # Join with <br> and mark as safe HTML
        return mark_safe("<br>".join(output_lines)) if output_lines else "No options"
    def get_exam_names(self, obj):
        from .models import ExamQuestion, PastExamQuestion

        # Get Live Exams
        live_exams = ExamQuestion.objects.filter(question=obj).select_related('exam')
        live_exam_titles = [eq.exam.title for eq in live_exams if eq.exam]

        # Get Past Exams
        past_exams = PastExamQuestion.objects.filter(question=obj).select_related('exam')
        past_exam_titles = [peq.exam.title for peq in past_exams if peq.exam]

        # Combine both (avoid duplicates)
        all_titles = set(live_exam_titles + past_exam_titles)

        return ", ".join(all_titles) if all_titles else "—"
    get_exam_names.short_description = 'Exam(s)'



# Register the admin class
admin.site.register(Question, QuestionAdmin)



@admin.register(QuestionOption)
class QuestionOptionAdmin(admin.ModelAdmin):
    list_display = ('text', 'question', 'is_correct')
    list_filter = ('is_correct',)
    search_fields = ('text', 'question__text')

@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'exam', 'total_correct_answers', 'wrong_answers', 'answered', 'passed', 'attempt_time', 'score')
    list_filter = ('passed', 'exam')
    search_fields = ('user__username', 'exam__title')
    readonly_fields = ('score', 'attempt_time')
    ordering = ('-attempt_time',)

    def score(self, obj):
        return obj.score  # Uses the `score` property to display the calculated score
    score.short_description = 'Score'

@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ('user', 'score', 'exam')
    search_fields = ('user__username', 'exam__title')
    list_filter = ('exam', 'score')


class PastExamAttemptInline(admin.TabularInline):
    model = PastExamAttempt
    extra = 1  # Number of empty rows displayed in the inline formset

# PastExamAdmin
class PastExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'organization', 'department', 'position', 'exam_date', 'is_published', 'duration')
    list_filter = ('organization', 'department', 'position', 'is_published')
    search_fields = ('title', 'organization__name')
    ordering = ('exam_date',)
    inlines = [PastExamAttemptInline]  # Show related attempts inline

    # Fields displayed on the form when adding/editing a PastExam
    fieldsets = (
        (None, {
            'fields': ('title', 'organization', 'department', 'position', 'exam_date', 'duration','exam_type', 'is_published')
        }),
        # ('Questions', {
        #     'fields': ('questions',)
        # }),
    )

# PastExamAttemptAdmin
class PastExamAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'past_exam', 'attempt_time', 'score', 'answered_questions', 'correct_answers', 'wrong_answers')
    list_filter = ('past_exam', 'user')
    search_fields = ('user__username', 'past_exam__title')
    ordering = ('-attempt_time',)

    def save_model(self, request, obj, form, change):
        """ Recalculate score before saving the PastExamAttempt """
        obj.calculate_score()
        super().save_model(request, obj, form, change)

# Registering the models and admin classes
admin.site.register(PastExam, PastExamAdmin)
admin.site.register(PastExamAttempt, PastExamAttemptAdmin)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'address')
    search_fields = ('name', 'address')

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization')
    list_filter = ('organization',)
    search_fields = ('name', 'organization__name')

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    
    
    
    
class ExamQuestionOptionInline(admin.TabularInline):
    model = ExamQuestionOption
    extra = 0
    readonly_fields = ['option_text']

    def option_text(self, obj):
        return obj.option.text if obj.option else "-"
    option_text.short_description = "Option Text"
    
    
    
class ExamQuestionAdmin(admin.ModelAdmin):
    list_display = ['exam', 'question_text', 'points', 'order']
    inlines = [ExamQuestionOptionInline]

    def question_text(self, obj):
        return obj.question.text if obj.question else "-"
    question_text.short_description = "Question"
    
admin.site.register(ExamQuestion, ExamQuestionAdmin)
admin.site.register(ExamQuestionOption) 
