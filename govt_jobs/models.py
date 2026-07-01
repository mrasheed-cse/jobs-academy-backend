from django.db import models
from quiz.models import *

class GovernmentJob(models.Model):
    title = models.CharField(max_length=255)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='government_jobs', null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='government_jobs')
    positions = models.ManyToManyField(Position, related_name='government_jobs', blank=True)  
    location = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    deadline = models.DateField(blank=True, null=True)
    posted_on = models.DateTimeField(auto_now_add=True)
    official_link = models.URLField(blank=True, null=True)
    pdf = models.FileField(upload_to='govt_job_pdfs/', blank=True, null=True)

    def __str__(self):
        return self.title



class Notice(models.Model):
    government_job = models.ForeignKey(
        GovernmentJob, on_delete=models.CASCADE, related_name="notices"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    pdf = models.FileField(upload_to="notices/", blank=True, null=True)
    link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notice for {self.government_job.title} - {self.title}"