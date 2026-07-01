from django.urls import path, include
from .views import *
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
router = DefaultRouter()
router.register(r'subjects', SubjectViewSet, basename='subject')

urlpatterns = [
    path('api/', include(router.urls)),
    
    
    
    path('api/start-practice/', StartPracticeSessionView.as_view(), name='start-practice'),
    path('api/submit-practice/', SubmitPracticeSessionView.as_view(), name='submit-practice'),
    path('api/practice/leaderboard/', PracticeLeaderboardAPIView.as_view(), name='leaderboard'),
    
    path('api/questions/upload/', PracticeQuestionUploadView.as_view()),
    path("api/top-scorers/", DailyTopScorerAPIView.as_view(), name="daily-top-scorers"),
    path("api/admin/analytics/", AdminAnalyticsAPIView.as_view(), name="admin-analytics"),
]


urlpatterns += [
    path('api/rewards/distribute/', RewardDistributionCreateAPIView.as_view(), name='create_distribution'),
    path('api/reward-distributions/', RewardDistributionListAPIView.as_view(), name='reward_list'),
    path('api/rewards/<int:distribution_id>/', UserRewardListAPIView.as_view(), name='user_rewards'),
    path('api/rewards/user/', UserRewardByPhoneAPIView.as_view(), name='user_reward_by_phone'),
    
    
    path('api/rewards-stats/', UserRewardEfficiencyView.as_view()),
    path('api/word-puzzles/', GameListView.as_view(), name='game-list'),
    path("api/puzzles/", PuzzleListView.as_view(), name="puzzle-list"),

    path('api/puzzles/<int:puzzle_id>/word/', PuzzleWordView.as_view(), name='puzzle-word'),
    path('api/word/upload-excel/', WordExcelUploadAPIView.as_view()),


] 

# templates
urlpatterns +=[
    path("upload-questions/", TemplateView.as_view(template_name="Html/custom/quick_quiz/upload_questions.html")),
    path("rewards-stats/", TemplateView.as_view(template_name="Html/custom/quick_quiz/reward-stats.html")),
    
    
    path("send-rewards/", TemplateView.as_view(template_name="Html/custom/quick_quiz/send_rewards_form.html")),
]

urlpatterns +=[
    path("api/word-game/submit/", SubmitWordGameAPIView.as_view(), name="submit_word_game_attempt"),
    path("api/word-game/leaderboard/", PivotWordGameLeaderboardAPIView.as_view(), name="wordgame_leaderboard"),
    path('api/v1/game-activity/', UserGameActivityView.as_view(), name='user-game-activity'),

]

urlpatterns += [
    path("games/word/upload-excel/", TemplateView.as_view(template_name="Html/custom/games/word-excel-upload.html"))
]
