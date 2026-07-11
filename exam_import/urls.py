from django.urls import path
from .views import StartImportView, FixMathNotationView, ImportStatusView, PastExamListAdminView, PastExamDetailView

urlpatterns = [
    path('api/exam-import/start/',              StartImportView.as_view(),       name='exam-import-start'),
    path('api/exam-import/<int:job_id>/status/', ImportStatusView.as_view(),      name='exam-import-status'),
    path('api/exam-import/exams/',              PastExamListAdminView.as_view(), name='exam-import-list'),
    path('api/exam-import/exams/<int:exam_id>/questions/', PastExamDetailView.as_view(), name='exam-import-detail'),
    path('api/exam-import/fix-math/', FixMathNotationView.as_view(), name='fix-math'),
]
