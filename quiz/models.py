import uuid
from django.db import models
from django.db.models import Sum
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from datetime import date
from invitation.models import ExamInvite
# from django.contrib.auth import get_user_model

User = get_user_model()



class ExamCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    @property
    def exam_count(self):
        """Return the number of exams under this category."""
        return self.exams.count()

    class Meta:
        verbose_name_plural = "Exam Categories"
        ordering = ['name']


class ExamType(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Organization(models.Model):
    name = models.CharField(max_length=255, unique=True)
    address = models.TextField(null=True, blank=True)
    def __str__(self):
        return self.name
    
class Department(models.Model):
    name = models.CharField(max_length=255)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="departments")

    def __str__(self):
        return f"{self.name} - {self.organization.name}"


class Position(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name
    
    
    
    

class Exam(models.Model):
    exam_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam_type = models.ForeignKey('ExamType', on_delete=models.SET_NULL, null=True, blank=True, related_name='exams')
    title = models.CharField(max_length=255, unique=True)
    total_questions = models.PositiveIntegerField()
    created_by = models.ForeignKey(User, related_name='exams_created', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Add organization hierarchy  
    organization = models.ForeignKey('Organization', on_delete=models.SET_NULL, null=True, blank=True, related_name="exam_organizations")
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True, related_name="exam_departments")
    position = models.ForeignKey('Position', on_delete=models.SET_NULL, null=True, blank=True, related_name="exam_positions")
    
    # Subject relation
    subject = models.ForeignKey('Subject', on_delete=models.SET_NULL, related_name="exams", null=True, blank=True)

    
    total_mark = models.PositiveIntegerField()
    pass_mark = models.PositiveIntegerField()
    negative_mark = models.FloatField(null=True, blank=True, default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    starting_time = models.DateTimeField(null=True, blank=True)
    last_date = models.DateField(null=True, blank=True)
    category = models.ForeignKey(ExamCategory, related_name='exams', on_delete=models.SET_NULL, null=True, blank=True)
    duration = models.DurationField(null=True, blank=True, help_text="Duration in format: HH:MM:SS (e.g., 1:30:00 for 1 hour 30 minutes)")
    
    
    
    def __str__(self):
        return f"{self.title} (Category: {self.category.name if self.category else 'Uncategorized'})"

    @property
    def status(self):
        """Return exam status as 'Upcoming', 'Ongoing', or 'Closed'."""
        now = timezone.now()
        if self.starting_time and self.last_date:
            end_time = self.starting_time + self.duration if self.duration else timezone.make_aware(
                timezone.datetime.combine(self.last_date, timezone.datetime.max.time()))
            if now < self.starting_time:
                return "Upcoming"
            elif self.starting_time <= now <= end_time:
                return "active"
            
        if self.last_date:
            now = now = timezone.now().date()
            if now <= self.last_date:
                return "Ongoing"
            

        return "archived"

    def calculate_pass_fail(self, correct_answers):
        """Determine if the user has passed or failed based on correct answers."""
        return correct_answers >= self.pass_mark

    def get_user_attempt_count(self, user):
        """Get the number of attempts by a specific user."""
        return ExamAttempt.objects.filter(user=user, exam=self).count()

    def can_user_access(self, user):
        """
        Determines if a user can access the exam based on ownership, invitation, or subscription usage.
        """
        # Allow access if the user is the creator of the exam
        if self.created_by == user:
            return True

        # Allow access if the user has an accepted invitation
        if ExamInvite.objects.filter(exam=self, invited_user=user, is_accepted=True).exists():
            return True

        # Get the user's active subscription
       
        
        # Ensure the user has not exceeded their exam-taking limit
        

        print("hello world")
        # Ensure other conditions, such as exam category matching or subscription specifics, are met


        return True

    def delete(self, *args, **kwargs):
        # Get the questions associated with this exam
        related_questions = self.questions.all()

        # First, delete the Exam instance
        super().delete(*args, **kwargs)

        # Now, iterate through the questions that were related to this exam
        for question in related_questions:
            # Check if this question is still related to any other Exam instances
            if not question.exams.exists():
                # If the question is not linked to any other exams, delete it
                question.delete()
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Exam"
        verbose_name_plural = "Exams"


class Status(models.Model):
    STATUS_CHOICES = [
        ('student', 'student'),
        ('draft', 'Draft'),
        ('submitted_to_admin', 'Submitted to Admin'),
        ('under_review', 'Under Review'),
        ('reviewed', 'Reviewed'),
        ('returned_to_creator', 'Returned to Creator'),
        ('published', 'Published'),
    ]
    
    exam = models.OneToOneField(Exam, on_delete=models.CASCADE, related_name = 'exam')
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name="user")
    # description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='draft')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name = "reviewed_by")  # Admin who reviewed the exam

    def __str__(self):
        return f"{self.exam.title} - {self.status}"


    def get_exam_details(self):
        """
        This method returns a dictionary containing the exam details needed for the frontend.
        """
        return {
            'title': self.exam.title,
            # 'category': self.exam.category.name,
            'created_by': self.exam.created_by.username,  # Assuming 'created_by' is a ForeignKey to User in Exam model
            'total_questions': self.exam.total_questions,
            'total_marks': self.exam.total_mark,
            'negative_mark': self.exam.negative_mark,
            'pass_mark': self.exam.pass_mark,
            'starting_time': self.exam.starting_time,
            'duration': self.exam.duration,
            'last_date': self.exam.last_date,
            'status': self.status,
            'reviewed_by': self.reviewed_by.username if self.reviewed_by else None,
            'user': self.user.username if self.user else None,
        }
        
        

    
class ExamDifficulty(models.Model):
    exam = models.OneToOneField(Exam, on_delete=models.CASCADE, related_name='difficulty')
    difficulty1_percentage = models.IntegerField(default=0)  # Difficulty 1 (0-100%)
    difficulty2_percentage = models.IntegerField(default=0)  # Difficulty 2 (0-100%)
    difficulty3_percentage = models.IntegerField(default=0)  # Difficulty 3 (0-100%)
    difficulty4_percentage = models.IntegerField(default=0)  # Difficulty 4 (0-100%)
    difficulty5_percentage = models.IntegerField(default=0)  # Difficulty 5 (0-100%)
    difficulty6_percentage = models.IntegerField(default=0)  # Difficulty 6 (0-100%)

    def clean(self):
        """
        Ensure the sum of the difficulty percentages is 100%.
        """
        total_percentage = (self.difficulty1_percentage + self.difficulty2_percentage +
                            self.difficulty3_percentage + self.difficulty4_percentage +
                            self.difficulty5_percentage + self.difficulty6_percentage)
        if total_percentage != 100:
            raise ValidationError("The total percentage of difficulty questions must equal 100.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Difficulty for {self.exam.title}"

    class Meta:
        verbose_name = 'Exam Difficulty'
        verbose_name_plural = 'Exam Difficulties'




class ExamAttempt(models.Model):
    exam = models.ForeignKey('Exam', related_name='attempts', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exam_attempts')
    answered = models.PositiveIntegerField(default=0)
    wrong_answers = models.PositiveIntegerField(default=0)
    passed = models.BooleanField(default=False, null=True)
    total_correct_answers = models.PositiveIntegerField(default=0)
    attempt_time = models.DateTimeField(auto_now_add=True)
    score = models.FloatField(default=0.0, null=True, blank=True)
    class Meta:
        ordering = ['-attempt_time']
        verbose_name = "Exam Attempt"
        verbose_name_plural = "Exam Attempts"

    def __str__(self):
        return f"{self.user.username} - {self.exam.title} - {self.total_correct_answers} correct answers"

    def get_answered_questions(self):
        return self.user_answers.filter(selected_option__isnull=False)

    def get_unanswered_questions(self):
        all_questions = self.exam.questions.all()
        answered_questions_ids = self.user_answers.values_list('question', flat=True)
        return all_questions.exclude(id__in=answered_questions_ids)

    def get_wrong_answers(self):
        return self.user_answers.filter(is_correct=False)
    
    
    
    
    @property
    def is_passed(self):
        """Check if the attempt passed based on exam pass mark.

        Compares the stored, negative-mark-adjusted `score` against the
        exam's pass_mark — NOT raw total_correct_answers, since that ignores
        negative marking and would disagree with the score actually shown
        to the user.
        """
        return self.score >= self.exam.pass_mark

    @classmethod
    def total_correct_for_user_exam(cls, user, exam):
        """Get total correct answers for a user across all attempts for a specific exam."""
        return cls.objects.filter(user=user, exam=exam).aggregate(total_correct=Sum('total_correct_answers'))['total_correct'] or 0

    def save(self, *args, **kwargs):
        """Override save to auto-set `passed` based on `is_passed`."""
        self.passed = self.is_passed
        super().save(*args, **kwargs)
        
        Leaderboard.update_best_score(self.user, self.exam)


      
        
class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name

class Question(models.Model):
    DIFFICULTY_LEVEL_CHOICES = [
        (1, 'Very Easy'),
        (2, 'Easy'),
        (3, 'Medium'),
        (4, 'Hard'),
        (5, 'Very Hard'),
        (6, 'Expert'),
    ]
    
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('reviewed', 'Reviewed'),
        ('approved', 'Approved'),
        ('published', 'Published'),
        ('rejected', 'Rejected'),
    ]
    
    exams = models.ManyToManyField('Exam', related_name='questions', blank=True)
    text = models.TextField(unique=True, null=True, blank=True)
    image = models.ImageField(upload_to='question_images/', null=True, blank=True)

    # explanation = models.TextField(null=True, blank=True)
    # explanation_image = models.ImageField(upload_to='explanation_images/', null=True, blank=True)

    marks = models.IntegerField()
    category = models.ForeignKey(Category, related_name='questions', on_delete=models.CASCADE, null=True, blank=True)
    difficulty_level = models.IntegerField(choices=DIFFICULTY_LEVEL_CHOICES, default=1, null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='submitted', null=True)
    remarks = models.TextField(blank=True, null=True)
    time_limit = models.IntegerField(help_text="Time limit for this question in seconds", default=60)
    created_by = models.ForeignKey(User, related_name="question_created_by", null=True, blank=True, on_delete=models.CASCADE)
    reviewed_by = models.ForeignKey(User, related_name="question_reviewed_by", null=True, blank=True, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, related_name='questions', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateField(auto_now_add=True, null=True)
    updated_at = models.DateField(auto_now=True, null=True)

    def get_options(self):
        return self.options.all()

    def get_correct_answer(self):
        correct_option = self.options.filter(is_correct=True).first()
        return correct_option.text if correct_option else None

    def __str__(self):
        return self.text if self.text else "Image-based Question"

    def category_name(self):
        return self.category.name if self.category else None

    def clean(self):
        """Ensure only one of 'text' or 'image' is provided, and only one of 'explanation' or 'explanation_image'."""
        if not self.text and not self.image:
            raise ValueError("Either 'text' or 'image' must be provided.")
        if self.text and self.image:
            raise ValueError("You cannot provide both 'text' and 'image' for a question.")

        if self.explanation and self.explanation_image:
            raise ValueError("You cannot provide both a text and image explanation.")


    

class QuestionOption(models.Model):
    question = models.ForeignKey(Question, related_name='options', on_delete=models.CASCADE)
    text = models.TextField(null=True, blank=True)  # Optional text
    image = models.ImageField(upload_to="question_options/", blank=True, null=True)  # Image option
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text if self.text else f"Image Option ({self.image.url if self.image else 'No Image'})"




class UserAnswer(models.Model):
    exam_attempt = models.ForeignKey(ExamAttempt, related_name='user_answers', on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(QuestionOption, on_delete=models.SET_NULL, null=True, blank=True)
    is_correct = models.BooleanField(default=False)

  


class Leaderboard(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leaderboard', null=True)
    score = models.IntegerField(default=0)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='leaderboards')
    total_questions = models.IntegerField(default=0, null=True)
    class Meta:
        ordering = ['-score']  # Order by score descending

    def __str__(self):
        return f'{self.user} - {self.score}'

    @staticmethod
    def update_best_score(user, exam):
        # Calculate the cumulative total of correct answers across all attempts
        total_correct = ExamAttempt.objects.filter(user=user, exam=exam).aggregate(
            total_correct=Sum('total_correct_answers')
        )['total_correct'] or 0

        # Calculate total answered questions across all attempts for this user and exam
        total_answered = ExamAttempt.objects.filter(user=user, exam=exam).aggregate(
            total_answered=Sum('answered')
        )['total_answered'] or 0

        # Update the leaderboard entry with the cumulative score and total answered questions
        leaderboard_entry, created = Leaderboard.objects.get_or_create(user=user, exam=exam)
        leaderboard_entry.score = total_correct
        leaderboard_entry.total_questions = total_answered
        leaderboard_entry.save()
    
    def get_position(self):
        # Fetch all leaderboard entries for the exam ordered by score
        ordered_leaderboard = Leaderboard.objects.filter(exam=self.exam).order_by('-score')
        # Generate a list of users with their ranks
        position = 1
        for entry in ordered_leaderboard:
            if entry.user == self.user:
                return position
            position += 1
        return None
        





# past exams models
# ******><*******


    






class PastExam(models.Model):
    title = models.TextField(unique=True)  # Exam Name
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="exams")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="exams")
    position = models.ForeignKey(Position, on_delete=models.CASCADE, related_name="exams")
    exam_type = models.ForeignKey(ExamType, on_delete=models.SET_NULL, null=True, blank=True, related_name="past_exams")
    exam_date = models.DateField()  # When the exam was conducted
    duration = models.IntegerField(null=True, blank=True)
    is_published = models.BooleanField(default=True)  # Admin controls visibility
    questions = models.ManyToManyField(Question, related_name="past_exams", through='PastExamQuestion')  # Many-to-Many with Question
    total_questions = models.PositiveIntegerField(default=0) 
    pass_mark = models.PositiveIntegerField(default=50)  # Minimum passing percentage
    negative_mark = models.FloatField(default=0.0)  # Penalty per wrong answer
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="created_past_exams"
    )
    def save(self, *args, **kwargs):
        is_new = self.pk is None  # Check if it's a new instance
    
        super().save(*args, **kwargs)  # Save if it's new, get the ID

        if not is_new:  # Only update total_questions for existing records
            self.total_questions = self.questions.count()
            super().save(update_fields=["total_questions"])  # Save only the updated field

    
    
    def __str__(self):
        return f"{self.title} ({self.organization.name})"




class PastExamAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    past_exam = models.ForeignKey(PastExam, on_delete=models.CASCADE, related_name="exam_attempts")
    attempt_time = models.DateTimeField(auto_now_add=True)
    total_questions = models.PositiveIntegerField()
    answered_questions = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    wrong_answers = models.PositiveIntegerField(default=0)
    score = models.FloatField(default=0.0)  # Store the final score

    # class Meta:
    #     unique_together = ('user', 'past_exam')  # Prevents duplicate attempts for the same user-exam pair

    def calculate_score(self):
        """ Example score calculation method """
        if self.total_questions > 0:
            self.score = (self.correct_answers / self.total_questions) * 100  # Percentage score
            self.save()

    def __str__(self):
        return f"{self.user.username} - {self.past_exam.title} (Score: {self.score})"

class PastUserAnswer(models.Model):
    exam_attempt = models.ForeignKey(PastExamAttempt, related_name='user_answers', on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(QuestionOption, on_delete=models.SET_NULL, null=True, blank=True)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.exam_attempt.user.username} - {self.question.text[:50]}"



class ExamQuestion(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    question  = models.ForeignKey(Question, on_delete=models.CASCADE, blank=True)
    points = models.FloatField(null=True, blank=True)
    order = models.IntegerField(null=True, blank=True)
    

class ExamQuestionOption(models.Model):
    exam_question = models.ForeignKey(ExamQuestion, on_delete=models.CASCADE)
    option = models.ForeignKey(QuestionOption, on_delete=models.CASCADE, blank=True)

class QuestionUsage(models.Model):
    question = models.ForeignKey(Question, related_name='usages', on_delete=models.CASCADE, null=True, blank=True)
    exam = models.CharField(max_length=255, help_text="Name of the external exam where the question was used", null=True, blank=True)
    past_exam = models.ForeignKey(PastExam, related_name='question_usages', on_delete=models.CASCADE, null=True, blank=True)
    year = models.IntegerField(default=date.today().year)

    def __str__(self):
        return f"{self.question.text} ({self.year})"


class PastExamQuestion(models.Model):
    exam = models.ForeignKey(PastExam, on_delete=models.CASCADE, related_name='related_questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='related_pastexams')
    order = models.IntegerField(null=True, blank=True)
    points = models.FloatField(null=True, blank=True)

    # 🔥 NEW: Explanation for this specific instance
    explanation = models.TextField(null=True, blank=True)
    explanation_image = models.ImageField(upload_to='past_explanation_images/', null=True, blank=True)

class PastExamQuestionOption(models.Model):
    question = models.ForeignKey(PastExamQuestion, on_delete=models.CASCADE, related_name='selected_options')
    option = models.ForeignKey(QuestionOption, on_delete=models.CASCADE, related_name='used_in_pastexams')

