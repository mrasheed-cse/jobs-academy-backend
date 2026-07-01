from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *
from django.views.generic import TemplateView
router = DefaultRouter()
router.register(r'govt-jobs', GovernmentJobViewSet, basename='governmentjob')
router.register(r'notices', NoticeViewSet, basename='notice')

urlpatterns = [
    path('api/', include(router.urls)),
    
]



# Template urls

urlpatterns += [
    path('govt-job-form/', TemplateView.as_view(template_name='Html/custom/govt_jobs/govt_job_form.html'), name = "govt_job_form"),
    path('govt-jobs/', TemplateView.as_view(template_name='Html/custom/govt_jobs/govt_jobs.html'), name = "govt_jobs"),
    path('govt-job-details/<int:id>/', TemplateView.as_view(template_name='Html/custom/govt_jobs/govt_job_details.html'), name='govt-job-details'),
    path('govt-jobs/<int:id>/update/', TemplateView.as_view(template_name="Html/custom/govt_jobs/govt_jobs_update.html")),
    
]
