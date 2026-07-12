from django.urls import path
from .views import StartImportView, FixMathNotationView, ImportStatusView, PastExamListAdminView, PastExamDetailView, ExamQuestionsAdminView, QuestionEditView, OptionEditView, ExamPublishView

urlpatterns = [
    path('api/exam-import/start/',              StartImportView.as_view(),       name='exam-import-start'),
    path('api/exam-import/<int:job_id>/status/', ImportStatusView.as_view(),      name='exam-import-status'),
    path('api/exam-import/exams/',              PastExamListAdminView.as_view(), name='exam-import-list'),
    path('api/exam-import/exams/<int:exam_id>/questions/', PastExamDetailView.as_view(), name='exam-import-detail'),
    path('api/exam-import/fix-math/', FixMathNotationView.as_view(), name='fix-math'),
    path('api/exam-import/exams/<int:exam_id>/manage/', ExamQuestionsAdminView.as_view(), name='exam-manage-questions'),
    path('api/exam-import/exams/<int:exam_id>/publish/', ExamPublishView.as_view(), name='exam-publish'),
    path('api/exam-import/questions/<int:question_id>/', QuestionEditView.as_view(), name='question-edit'),
    path('api/exam-import/options/<int:option_id>/', OptionEditView.as_view(), name='option-edit'),
]
