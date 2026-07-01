from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import PracticeSession, UserPoints

User = get_user_model()

@receiver(post_save, sender=User)
def update_related_user_data(sender, instance, created, **kwargs):
    if created:
        phone = getattr(instance, 'phone_number', None)

        if phone:
            # Update all matching PracticeSessions
            sessions = PracticeSession.objects.filter(phone_number=phone, user__isnull=True)
            for session in sessions:
                session.user = instance
                session.phone_number = None
                session.username = None
                session.save()

            # Update all matching UserPoints
            points = UserPoints.objects.filter(phone_number=phone, user__isnull=True)
            for point in points:
                point.user = instance
                point.phone_number = None
                point.username = None
                point.save()
