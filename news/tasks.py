from celery import shared_task
from django.utils import timezone
from django.db import transaction
import logging

from .models import News
from .utils import process_scheduled_news    # your FCM logic

logger = logging.getLogger(__name__)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=30, retry_kwargs={"max_retries": 3})
def send_scheduled_news_notifications(self):
    now = timezone.now()

    news_qs = News.objects.select_for_update(skip_locked=True).filter(
        send_notification=True,
        auto_notification_sent=False,
        notification_datetime__lte=now,
    ).filter(
        models.Q(notification_expire_at__isnull=True) |
        models.Q(notification_expire_at__gt=now)
    )

    if not news_qs.exists():
        return "No pending notifications"

    sent_count = 0

    with transaction.atomic():
        for news in news_qs:
            try:
                send_news_notification(news)  # 🔔 Your FCM logic
                news.auto_notification_sent = True
                news.save(update_fields=["auto_notification_sent"])
                sent_count += 1
            except Exception as e:
                logger.error(f"Notification failed for news {news.id}: {e}")

    return f"Sent {sent_count} news notifications"
