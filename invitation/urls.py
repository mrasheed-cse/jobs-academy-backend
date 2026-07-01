from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InviteViewSet, accept_invitation, InvitedExamsView
from django.views.generic import TemplateView


# router = DefaultRouter()
# router.register(r'invites', InviteViewSet, basename='invite')

urlpatterns = [
    path('invite-user/<uuid:exam_id>/', InviteViewSet.as_view({'post': 'create'}), name='invite_user'),
    path('accept-invitation/<uuid:token>/', accept_invitation, name='accept-invitation'),
    path('invited-exams/', InvitedExamsView.as_view(), name='invited-exams'),
    # invite template
    path('invite_user/<uuid:exam_id>/', TemplateView.as_view(template_name='Html/custom/invitation/invite_user.html'), name='invite_user'),
    path('invitation-accepted/<uuid:token>/', TemplateView.as_view(template_name='invitation_accept.html')),
    path('invited_exams/', TemplateView.as_view(template_name='Html/custom/invitation/invited_exams.html'), name = 'invited_exams'), 

]
