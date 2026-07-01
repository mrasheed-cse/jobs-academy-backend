from django.contrib import admin
from .models import *



@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']
    
    

# PracticeOption Admin
class PracticeOptionInline(admin.TabularInline):
    model = PracticeOption
    extra = 0
    can_delete = False
    readonly_fields = ('text', 'image', 'is_correct')
    show_change_link = False
    max_num = 0  # Prevent adding new rows

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

class PracticeQuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'short_text', 'marks', 'created_at')
    search_fields = ('text', )
    list_filter = ('subject', 'created_at')
    inlines = [PracticeOptionInline]

    def short_text(self, obj):
        return obj.text[:50] + "..." if obj.text and len(obj.text) > 50 else obj.text
    short_text.short_description = "Question Text"

admin.site.register(PracticeQuestion, PracticeQuestionAdmin)

# PracticeSession Admin
@admin.register(PracticeSession)
class PracticeSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'duration', 'score', 'created_at']
    search_fields = ['user__username']  # Allow searching by username of the user

@admin.register(UserPoints)
class UserPointsAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_user_name', 'get_user_phone', 'username', 'points']
    search_fields = ['user__username', 'username', 'user__phone_number', 'phone_number']

    def get_user_name(self, obj):
        """Show username from related User or fallback username field"""
        return obj.user.username if obj.user else obj.username
    get_user_name.short_description = 'User'

    def get_user_phone(self, obj):
        """Show phone number from related User or fallback phone_number field"""
        return obj.user.phone_number if obj.user else obj.phone_number
    get_user_phone.short_description = 'Phone Number'



class UserRewardInline(admin.TabularInline):
    model = UserReward
    extra = 0
    readonly_fields = ('username', 'phone_number', 'total_score', 'reward_amount')
    can_delete = False
    ordering = ('-total_score',)
    show_change_link = False


@admin.register(RewardDistribution)
class RewardDistributionAdmin(admin.ModelAdmin):
    list_display = (
        'distribution_type',
        'start_date',
        'end_date',
        'per_point_value',
        'total_users',
        'total_amount',
        'distributed_at',
    )
    list_filter = ('distribution_type', 'distributed_at')
    search_fields = ('distribution_type', 'note')
    readonly_fields = ('distributed_at', 'total_users', 'total_amount')
    inlines = [UserRewardInline]
    ordering = ('-distributed_at',)
    fieldsets = (
        ('Distribution Details', {
            'fields': (
                'distribution_type',
                'start_date',
                'end_date',
                'per_point_value',
                'note',
            )
        }),
        ('Statistics', {
            'fields': (
                'total_users',
                'total_amount',
                'distributed_at',
            )
        }),
    )


@admin.register(UserReward)
class UserRewardAdmin(admin.ModelAdmin):
    list_display = (
        'username',
        'phone_number',
        'distribution',
        'total_score',
        'reward_amount',
    )
    list_filter = ('distribution__distribution_type',)
    search_fields = ('username', 'phone_number')
    readonly_fields = ('reward_amount',)
    ordering = ('-total_score',)
    
    

# ---------------------------------
# Word Inline (inside Puzzle)
# ---------------------------------
class WordInline(admin.TabularInline):
    model = Word
    extra = 1
    fields = ("text", "meaning_bn","hint", "difficulty", "created_at")
    readonly_fields = ("created_at",)

@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    list_display = (
        "text",
        "puzzle",
        "difficulty",
        "meaning_bn",
        "short_example_en",
        "created_at",
    )

    list_filter = (
        "difficulty",
        "puzzle",
        "created_at",
    )

    search_fields = (
        "text",
        "meaning_bn",
        "example_en",
        "example_bn",
        "hint",
    )

    ordering = ("-created_at",)

    readonly_fields = ("created_at",)

    fieldsets = (
        ("Puzzle Info", {
            "fields": ("puzzle", "difficulty"),
        }),
        ("Word Details", {
            "fields": (
                "text",
                "meaning_bn",
                "example_en",
                "example_bn",
                "hint",
            ),
        }),
        ("Meta", {
            "fields": ("created_at",),
        }),
    )

    # 🔹 Short preview for list view
    def short_example_en(self, obj):
        if obj.example_en:
            return obj.example_en[:40] + "..." if len(obj.example_en) > 40 else obj.example_en
        return "-"

    short_example_en.short_description = "Example (EN)"

# ---------------------------------
# WordPuzzle Admin
# ---------------------------------
class WordPuzzleAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "start_date", "end_date", "created_at")
    list_filter = ("status",)
    search_fields = ("title",)
    # inlines = [WordInline]

admin.site.register(WordPuzzle, WordPuzzleAdmin)
class WordGameScoreInline(admin.StackedInline):
    model = WordGameScore
    extra = 0
    max_num = 1
    can_delete = False
    verbose_name = "Word Game Score"
    verbose_name_plural = "Word Game Score"


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("id", "username_display", "phone_number", "user")
    search_fields = ("username", "phone_number", "user__username")
    list_filter = ("user",)
    inlines = [WordGameScoreInline]

    def username_display(self, obj):
        return obj.user.username if obj.user else obj.username

    username_display.short_description = "Player Name"


@admin.register(WordGameScore)
class WordGameScoreAdmin(admin.ModelAdmin):
    list_display = ("player", "score")
    search_fields = ("player__username", "player__phone_number", "player__user__username")



@admin.register(WordGameAttempt)
class WordGameAttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "player", "puzzle", "score", "started_at", "finished_at")
    list_filter = ("puzzle", "started_at", "finished_at")
    search_fields = ("player__username", "player__phone_number", "puzzle__title")
    ordering = ("-finished_at", "-score")
    readonly_fields = ("started_at", "finished_at")
    list_per_page = 25