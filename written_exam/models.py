from django.db import models
from quiz.models import ExamType, Organization, Department, Position, Subject, PastExam
# Create your models here.
from django.contrib.auth import get_user_model
User = get_user_model()
class RootExam(models.Model):
    # This defines how the exam will be taken (fixed values)
    EXAM_MODE_CHOICES = [
        ('mcq', 'MCQ'),
        ('written', 'Written'),
        ('both', 'Both'),
    ]
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    # exam_mode refers to HOW it's taken (MCQ/written)
    exam_mode = models.CharField(max_length=10, choices=EXAM_MODE_CHOICES, null=True, blank=True)

    # exam_type refers to the TYPE or PURPOSE of the exam (Job Test, Final, Admission...)
    exam_type = models.ForeignKey(
        ExamType, on_delete=models.SET_NULL, null=True, blank=True, related_name='root_exams'
    )

    # total_questions = models.PositiveIntegerField()
    exam_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # --- ADD THIS FIELD ---
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_root_exams'
    )
    # ----------------------

    
    subjects = models.ManyToManyField(Subject, related_name='root_exams')
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name='root_exams')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='root_exams')
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True, related_name='root_exams')
    past_exam = models.OneToOneField(
        PastExam,
        on_delete=models.SET_NULL, # If the PastExam is deleted, set this field to NULL
        null=True, blank=True,     # The link is optional and can be null
        related_name='root_exam'   # Allows accessing RootExam from PastExam: past_exam_instance.root_exam
    )
    def __str__(self):
        return self.title

    
    

class WrittenExam(models.Model):
    """
    Represents a specific instance of a written exam linked to a RootExam,
    often for a particular subject.
    """
    root_exam = models.ForeignKey(RootExam, on_delete=models.CASCADE, related_name='written_exams')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE) # Subject for THIS specific written exam instance
    total_questions = models.PositiveIntegerField(null=True, blank=True)
    total_marks = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Written - {self.root_exam.title} - {self.subject.name}"


class Passage(models.Model):
    """
    A passage that can be associated with a single WrittenQuestion.
    """
    title = models.CharField(max_length=255, blank=True, null=True) # Made optional for flexibility
    text = models.TextField(blank=True, null=True) # Made optional for flexibility
    image = models.ImageField(upload_to='passage_images/', blank=True, null=True)
    is_image = models.BooleanField(default=False) # Consider removing if not strictly needed
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, blank=True, null=True) # Associated subject for the passage

    # Removed 'written_exam' ForeignKey, as Passage now links *only* via WrittenQuestion

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title if self.title else f"Passage {self.id}"

class WrittenQuestion(models.Model):
    """
    Represents a main question in a WrittenExam, with an optional passage.
    """
    written_exam = models.ForeignKey(WrittenExam, on_delete=models.CASCADE, related_name='questions') # Links to the specific WrittenExam instance
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, blank=True, null=True) # Subject of this specific question
    passage = models.ForeignKey(Passage, on_delete=models.SET_NULL, blank=True, null=True, related_name='written_questions') # One-to-one with Passage
    
    question_text = models.TextField()
    question_image = models.ImageField(upload_to='written_questions/', blank=True, null=True)
    
    answer_text = models.TextField(blank=True, null=True)
    answer_image = models.ImageField(
        upload_to='written_questions/answers/', blank=True, null=True # Changed path for clarity
    )
    
    # New fields for explanation
    explanation_text = models.TextField(
        blank=True, 
        null=True, 
        help_text="Detailed text explanation for the question."
    )
    explanation_image = models.ImageField(
        upload_to='written_questions/explanations/', 
        blank=True, 
        null=True, 
        help_text="Image-based explanation for the question."
    )

    
    is_image = models.BooleanField(default=False) # Consider removing if not strictly needed
    question_number = models.PositiveIntegerField()
    has_sub_questions = models.BooleanField(default=False) # Indicates if this question has sub-questions
    marks = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Q{self.question_number} ({self.written_exam.root_exam.title}): {self.question_text[:50]}..."

# ----------------------------------------------------------------------

class SubWrittenQuestion(models.Model):
    """
    Represents a sub-question linked to a WrittenQuestion.
    """
    parent_question = models.ForeignKey(WrittenQuestion, on_delete=models.CASCADE, related_name='sub_questions')
    text  = models.TextField() # Aligned with HTML field name 'text'
    image  = models.ImageField(upload_to='sub_written_questions/', blank=True, null=True) # Aligned with HTML 'image'
    
    answer_text = models.TextField(blank=True, null=True)
    answer_image = models.ImageField(
        upload_to='sub_written_questions/answers/', blank=True, null=True # Clarified upload path for sub-answers
    )
    
    # New fields for explanation
    explanation_text = models.TextField(
        blank=True, 
        null=True, 
        help_text="Detailed text explanation for the sub-question."
    )
    explanation_image = models.ImageField(
        upload_to='sub_written_questions/explanations/', 
        blank=True, 
        null=True, 
        help_text="Image-based explanation for the sub-question."
    )
    
    is_image = models.BooleanField(default=False) # Consider removing if not strictly needed
    number  = models.PositiveIntegerField() # Aligned with HTML field name 'number'
    marks = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True) # Added for consistency

    def __str__(self):
        return f"SubQ{self.number} (Parent Q{self.parent_question.question_number}): {self.text[:50]}..."