from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from .views import *

# router = DefaultRouter()
# router.register('root-exams', RootExamViewSet)
# router.register('written-exams', WrittenExamViewSet)
# router.register('passages', PassageViewSet)
# router.register('written-questions', WrittenQuestionViewSet)
# router.register('sub-written-questions', SubWrittenQuestionViewSet)


urlpatterns = [
    path('api/wr-exams/create/', CreateWrittenExamAPIView.as_view(), name='create_exam'),
    path('api/wr-exams/', RootExamListView.as_view(), name='root_exam_list_create'),
    path('api/wr-exams/<int:pk>/', RootExamDetailView.as_view(), name='root-exam-detail'),
]




urlpatterns += [
   
    path('wr_exams/create/', TemplateView.as_view(template_name="Html/custom/written_exam/written_exam_create.html")),
    path('wr_exams/', TemplateView.as_view(template_name="Html/custom/written_exam/trs_wr_exams.html")),
    path('wr_exams/<int:exam_id>/', TemplateView.as_view(template_name="Html/custom/written_exam/wr-exam-details.html")),
]