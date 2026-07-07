from django.db import models
from quiz.models import PastExam


class ImportJob(models.Model):
    STATUS_CHOICES = [
        ('pending',    'Pending'),
        ('processing', 'Processing'),
        ('done',       'Done'),
        ('failed',     'Failed'),
    ]

    # Exam being populated
    exam_title    = models.TextField()
    org_name      = models.TextField()
    position_name = models.TextField()
    exam_year     = models.IntegerField()
    subject_name  = models.TextField(default='General Knowledge')
    marks_per_q   = models.IntegerField(default=1)
    negative_mark = models.FloatField(default=0.25)

    # Result
    past_exam     = models.ForeignKey(PastExam, null=True, blank=True,
                                       on_delete=models.SET_NULL,
                                       related_name='import_jobs')

    # Progress
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_pages      = models.IntegerField(default=0)
    processed_pages  = models.IntegerField(default=0)
    questions_found  = models.IntegerField(default=0)
    current_page     = models.TextField(blank=True, default='')
    error_log        = models.TextField(blank=True, default='')

    created_at  = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    @property
    def progress_percent(self):
        if self.total_pages == 0:
            return 0
        return round((self.processed_pages / self.total_pages) * 100)

    def __str__(self):
        return f'ImportJob #{self.pk} — {self.exam_title} ({self.status})'
