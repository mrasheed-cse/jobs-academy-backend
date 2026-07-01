from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()
from django.utils import timezone
from datetime import date, timedelta
# Create your models here.


class Subject(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class PracticeQuestion(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True)  # New field
    text = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='practice_questions/', blank=True, null=True)
    marks = models.PositiveIntegerField(default=1)  
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text or f"Image Question ({self.id})"


class PracticeOption(models.Model):
    question = models.ForeignKey(PracticeQuestion, related_name='options', on_delete=models.CASCADE)
    text = models.CharField(max_length=255, blank=True, null=True)
    image = models.ImageField(upload_to='practice_options/', blank=True, null=True)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text or f"Image Option ({self.id})"

class PracticeSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    username = models.CharField(max_length=150, blank=True, null=True)  # For unauthenticated users
    phone_number = models.CharField(max_length=15, blank=True, null=True)  # For unauthenticated users
    duration = models.DurationField(null=True, blank=True)
    score = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def update_score(self, score):
        """Update the user's score at the end of the session."""
        self.score = score
        self.save()

    def __str__(self):
        return f"Session for {self.user.username if self.user else self.username}"


class UserPoints(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    username = models.CharField(max_length=150, blank=True, null=True)  # For unauthenticated users
    phone_number = models.CharField(max_length=15, blank=True, null=True)  # For unauthenticated users
    points = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.username if self.user else self.username}'s Points"

    def add_points(self, points):
        """Add points to the user's account."""
        self.points += points
        self.save()

    def subtract_points(self, points):
        """Subtract points from the user's account."""
        if self.points >= points:
            self.points -= points
            self.save()
        else:
            raise ValueError("Not enough points to subtract.")







# -------------------------------
#  REWARD SYSTEM MODELS
# -------------------------------
class RewardDistribution(models.Model):
    DISTRIBUTION_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('half_monthly', 'Half-Monthly'),
        ('monthly', 'Monthly'),
    ]

    distribution_type = models.CharField(max_length=20, choices=DISTRIBUTION_CHOICES)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    distributed_at = models.DateTimeField(auto_now_add=True)
    total_users = models.IntegerField(default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    note = models.TextField(blank=True, null=True)
    # 👇 Add this
    per_point_value = models.DecimalField(max_digits=10, decimal_places=4, default=0.01, help_text="Value of 1 point in Taka")
    
    def __str__(self):
        return f"{self.get_distribution_type_display()} Reward ({self.start_date} → {self.end_date})"

    def calculate_period(self):
        """Automatically determine start and end date based on the chosen type."""
        today = date.today()
        if self.distribution_type == 'daily':
            self.start_date = today
            self.end_date = today

        elif self.distribution_type == 'weekly':
            self.start_date = today - timedelta(days=7)
            self.end_date = today

        elif self.distribution_type == 'half_monthly':
            if today.day <= 15:
                self.start_date = today.replace(day=1)
                self.end_date = today.replace(day=15)
            else:
                self.start_date = today.replace(day=16)
                next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
                self.end_date = next_month - timedelta(days=1)

        elif self.distribution_type == 'monthly':
            self.start_date = today.replace(day=1)
            next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
            self.end_date = next_month - timedelta(days=1)

        self.save()


class UserReward(models.Model):
    distribution = models.ForeignKey(
        RewardDistribution,
        on_delete=models.CASCADE,
        related_name='user_rewards'
    )
    username = models.CharField(max_length=150, blank=True, null=True)
    phone_number = models.CharField(max_length=15)
    total_score = models.IntegerField(default=0)
    reward_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ('distribution', 'phone_number')
        ordering = ['-total_score']

    def __str__(self):
        return f"{self.username or 'Guest'} ({self.phone_number}) - {self.reward_amount}৳"

    def calculate_reward(self):
        """Default rule: 100 score = 1.00 Taka"""
        self.reward_amount = round(self.total_score / 100, 2)
        self.save()

class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,
                                null=True, blank=True)
    username = models.CharField(max_length=150, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)

    @property
    def display_name(self):
        if self.user and self.user.username:
            return self.user.username
        if self.username:
            return self.username
        return f"Guest-{self.phone_number}" if self.phone_number else "Guest"
    
    
    
    def get_full_history(self):
        """
        Retrieves all attempts across both Practice Sessions and Word Puzzles.
        """
        # Fetch Practice Sessions
        practice_history = PracticeSession.objects.filter(
            models.Q(user=self.user) | models.Q(phone_number=self.phone_number)
        ).order_by('-created_at')

        # Fetch Word Puzzle Attempts
        puzzle_history = WordGameAttempt.objects.filter(
            player=self
        ).order_by('-started_at')

        return {
            "practice_sessions": practice_history,
            "puzzle_attempts": puzzle_history,
            "total_points": self.get_points()
        }

    def get_points(self):
        points_obj = UserPoints.objects.filter(
            models.Q(user=self.user) | models.Q(phone_number=self.phone_number)
        ).first()
        return points_obj.points if points_obj else 0
    
    
    def __str__(self):
        if self.user:
            return self.user.username
        return f"{self.username} ({self.phone_number})"
  
class WordPuzzle(models.Model):
    title = models.CharField(max_length=200)
    banner = models.ImageField(upload_to="puzzle_banners/", null=True, blank=True)

    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("upcoming", "Upcoming"), ("ended", "Ended")],
        default="active"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Word(models.Model):
    puzzle = models.ForeignKey(
        WordPuzzle,
        on_delete=models.CASCADE,
        related_name="words"
    )

    text = models.CharField(max_length=100)  # original word

    meaning_bn = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    example_en = models.TextField(
        null=True,
        blank=True,
        help_text="Example sentence in English"
    )

    example_bn = models.TextField(
        null=True,
        blank=True,
        help_text="Example sentence in Bangla"
    )

    hint = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    difficulty = models.CharField(
        max_length=20,
        choices=[
            ("easy", "Easy"),
            ("medium", "Medium"),
            ("hard", "Hard")
        ],
        default="easy"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.text} ({self.difficulty})"




class WordGameAttempt(models.Model):
    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name="attempts"
    )
    puzzle = models.ForeignKey(
        WordPuzzle,
        on_delete=models.CASCADE,
        related_name="attempts"
    )

    score = models.IntegerField(default=0)

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.player} | {self.puzzle} | {self.score} | {self.started_at}"




class WordGameScore(models.Model):
    player = models.OneToOneField(Player, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.player} - {self.score}"
