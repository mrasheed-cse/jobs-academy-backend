from django.urls import path
from .views import *
from django.views.generic import TemplateView


urlpatterns = [
    path("api/notifications/send/", SendNotificationView.as_view(), name="send_notification"),
    path('api/device-token/', RegisterDeviceTokenView.as_view()),
    path('api/segment-users/', SegmentUsersRawView.as_view(), name='segment-users'),
    path('api/log-activity/', LogActivityView.as_view(), name='log-activity'),
    path("api/track-click/", TrackClickAPIView.as_view(), name="track_click_api"),
    path("api/notifications/dashboard/", AdminDashboardView.as_view()), 
]



# Templates

urlpatterns += [
    path('segment-dashboard/', TemplateView.as_view(template_name="Html/custom/notifications/send_notification.html")),
    path('notification-dashboard/', TemplateView.as_view(template_name="Html/custom/notifications/admin_dashboard.html")),

]