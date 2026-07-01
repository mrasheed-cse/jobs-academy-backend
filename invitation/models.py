from django.db import models

# from quiz.models import Exam
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.template import Context
User = get_user_model()
from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse

import uuid
class ExamInvite(models.Model):
    exam = models.ForeignKey('quiz.Exam', on_delete=models.CASCADE, related_name='exams')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invites')
    invited_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_invites', null=True)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    invited_at = models.DateTimeField(auto_now=True)
    is_accepted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('exam', 'invited_user')
    
    # def generate_token(self):
    #     self.token = uuid.uuid4().hex

    def save(self, *args, **kwargs):
        if not self.token:
            self.generate_token()  # Ensure token is generated
        super().save(*args, **kwargs)
        
    def send_invitation_email(self):
        subject = 'Invitation to Participate in an Exam'
        accept_url = reverse('accept-invitation', args=[self.token])  # Include token in URL
        token = self.token
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:8000')
        full_accept_url = f'You are invite the quiz exam. Here is the link: http://localhost:8000/api/invitation-accepted/{token}/'  # Assuming you have a frontend URL set up
        # context = {
        #     'exam': self.exam,
        #     'invited_by':self.invited_by,
        #     'invited_user': self.invited_user,
        #     'accept_link':"https://www.w3schools.com/"
        # }

        template_name = 'invitation_email.html'
        
        # message = render_to_string(template_name=template_name, context=context)
        # plain_message = strip_tags(message)
        
        recipient_list = [self.invited_user.email]
        print(full_accept_url)
        send_mail(subject, full_accept_url, settings.DEFAULT_FROM_EMAIL, recipient_list)