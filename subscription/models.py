from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
User = get_user_model()

# -------------------------
# 1. Subscription Plans
# -------------------------

class SubscriptionPlanTier(models.Model):
    TIER_CHOICES = [
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('plus', 'Plus'),
        ('premium', 'Premium'),
    ]
    name = models.CharField(max_length=50, choices=TIER_CHOICES, unique=True)

    # Feature fields
    ad_free = models.BooleanField(default=False)
    free_model_test = models.BooleanField(default=True)
    paid_model_test = models.BooleanField(default=True)
    daily_previous_year_questions = models.PositiveIntegerField(default=0)
    upcoming_special_model_tests = models.PositiveIntegerField(default=0)
    prize_winning_special_exam = models.BooleanField(default=False)
    daily_live_exam_room_access = models.PositiveIntegerField(default=0)  # how many live exams per day

    def __str__(self):
        return self.get_name_display()


# -------------------------
# 2. Plan Prices
# -------------------------

class SubscriptionPlanPrice(models.Model):
    PLAN_DURATION_CHOICES = [
        ('weekly', 'সাপ্তাহিক'),
        ('biweekly', 'পাক্ষিক'),
        ('monthly', 'মাসিক'),
        ('quarterly', 'ত্রৈমাসিক'),
        ('halfyearly', 'ষাণ্মাসিক'),
    ]
    plan_tier = models.ForeignKey(SubscriptionPlanTier, on_delete=models.CASCADE, related_name='prices')
    duration = models.CharField(max_length=20, choices=PLAN_DURATION_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('plan_tier', 'duration')

    def __str__(self):
        return f"{self.plan_tier.name} - {self.get_duration_display()} @ {self.price}"


# -------------------------
# 3. Plan Exam Type Limits
# -------------------------

class PlanExamAccessLimit(models.Model):
    LIMIT_TYPE_CHOICES = [
        ('daily', 'Daily'),
        ('total', 'Total'),
    ]

    plan_tier = models.ForeignKey(SubscriptionPlanTier, on_delete=models.CASCADE, related_name='exam_access_limits')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)  # Exam or PastExam
    max_access_count = models.PositiveIntegerField()
    limit_type = models.CharField(max_length=10, choices=LIMIT_TYPE_CHOICES, default='total')

    class Meta:
        unique_together = ('plan_tier', 'content_type')

    def __str__(self):
        return f"{self.plan_tier.name} - {self.content_type} max {self.max_access_count} ({self.limit_type})"



# -------------------------
# 4. User Subscriptions
# -------------------------

class UserSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlanTier, on_delete=models.SET_NULL, null=True)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

  

    def __str__(self):
        return f"{self.user} - {self.plan.name}"
    
    def save(self, *args, **kwargs):
        today = timezone.now().date()
        self.is_active = self.end_date is None or today <= self.end_date
        super().save(*args, **kwargs)
# ----------------  ---------
# 5. User Exam Access Tracking
# -------------------------

class UserExamAccess(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)  # Exam or PastExam
    object_id = models.UUIDField()  # You can use UUIDField or IntegerField depending on your Exam model
    content_object = GenericForeignKey('content_type', 'object_id')
    accessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'content_type', 'object_id')

    def __str__(self):
        return f"{self.user} accessed {self.content_type} - {self.object_id}"
