from django.contrib import admin
from .models import (
    SubscriptionPlanTier,
    SubscriptionPlanPrice,
    PlanExamAccessLimit,
    UserSubscription,
    UserExamAccess
)


@admin.register(SubscriptionPlanTier)
class SubscriptionPlanTierAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'ad_free', 'free_model_test', 'paid_model_test',
        'daily_previous_year_questions', 'upcoming_special_model_tests',
        'prize_winning_special_exam', 'daily_live_exam_room_access'
    )
    list_filter = ('ad_free', 'free_model_test', 'paid_model_test')
    search_fields = ('name',)


@admin.register(SubscriptionPlanPrice)
class SubscriptionPlanPriceAdmin(admin.ModelAdmin):
    list_display = ('plan_tier', 'duration', 'price')
    list_filter = ('plan_tier', 'duration')
    search_fields = ('plan_tier__name',)
    ordering = ('plan_tier', 'duration')


@admin.register(PlanExamAccessLimit)
class PlanExamAccessLimitAdmin(admin.ModelAdmin):
    list_display = ('plan_tier', 'content_type', 'max_access_count')
    list_filter = ('plan_tier', 'content_type')
    search_fields = ('plan_tier__name',)


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active', 'plan')
    search_fields = ('user__username', 'user__phone_number')
    ordering = ('-start_date',)


@admin.register(UserExamAccess)
class UserExamAccessAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_type', 'object_id', 'accessed_at')
    list_filter = ('content_type', 'accessed_at')
    search_fields = ('user__username', 'object_id')
    ordering = ('-accessed_at',)
