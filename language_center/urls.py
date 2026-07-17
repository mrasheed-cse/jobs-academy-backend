from django.urls import path
from .views import *
from django.views.generic import TemplateView


urlpatterns = [
    path("api/languages/", LanguageListAPIView.as_view(), name="language-list"),
    path("api/word-of-the-day/", WordOfTheDayAPIView.as_view(), name="word-of-the-day"),
    # path("api/words/", WordListAPIView.as_view(), name="word-list"),
    path("api/words/<int:pk>/", WordDetailAPIView.as_view(), name="word-detail"),
    path("api/words/az/", WordAZAPIView.as_view(), name="word-az"),
    path("api/words/search/", WordSearchAPIView.as_view(), name="word-search"),
    path("api/language/<int:language_id>/words/upload/", DictionaryExcelUploadAPIView.as_view()),
    path("api/language/<int:language_id>/words/create/", WordCreateAPIView.as_view(), name="word-create"),
    path("api/illustration/", IllustrationProxyView.as_view(), name="illustration-proxy"),
    path("api/pixabay/", PixabayProxyView.as_view(), name="pixabay-proxy"),
    
    
]



# Template 

urlpatterns +=[
    path("language/", TemplateView.as_view(template_name="new_custom/language/language-home.html")),
    
    
    # admin Templates
    path("language/<int:language_id>/upload-words/", TemplateView.as_view(template_name="Html/custom/language/upload-words.html")),
    
    
]
from .word_import_views import (
    WordImportStartView, WordImportStatusView, PendingWordsView,
    WordApproveView, WordRejectView, WordBulkApproveView, WordEditView
)

word_import_patterns = [
    path('api/word-import/start/', WordImportStartView.as_view()),
    path('api/word-import/<int:job_id>/status/', WordImportStatusView.as_view()),
    path('api/word-import/pending/', PendingWordsView.as_view()),
    path('api/word-import/bulk-approve/', WordBulkApproveView.as_view()),
    path('api/word-import/words/<int:word_id>/', WordEditView.as_view()),
    path('api/word-import/words/<int:word_id>/approve/', WordApproveView.as_view()),
    path('api/word-import/words/<int:word_id>/reject/', WordRejectView.as_view()),
]
urlpatterns += word_import_patterns
