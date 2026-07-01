from rest_framework.routers import DefaultRouter
from django.urls import path, include
from django.views.generic import TemplateView
from .views import *

router = DefaultRouter()

router.register(r'subscription-plans', SubscriptionPlanTierViewSet)
router.register(r'plan-prices', SubscriptionPlanPriceViewSet)
router.register(r'access-limits', PlanExamAccessLimitViewSet)
router.register(r'user-subscriptions', UserSubscriptionViewSet, basename='user-subscription')
router.register(r'user-exam-accesses', UserExamAccessViewSet, basename='user-exam-access')


urlpatterns = [
    path('api/', include(router.urls)),
    path('api/check-permission/<exam_id>/', ExamPermissionCheckView.as_view(), name='check_exam_permission'),

]




# templates

urlpatterns +=[
    path('subscription/', TemplateView.as_view(template_name='new_custom/subscription/all_packages.html')),
]