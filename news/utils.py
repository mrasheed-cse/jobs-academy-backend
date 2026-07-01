# news/utils.py

import logging
from django.utils import timezone
# from notifications.fcm import send_fcm_notification  # Your existing FCM logic
from .models import News
from notifications.models import DeviceToken

logger = logging.getLogger(__name__)

def get_scheduled_news_to_send():
    """
    Returns a queryset of News that should be sent now via notification.
    Conditions:
    - send_notification=True
    - auto_notification_sent=False
    - notification_delay_hours is set
    - scheduled send time <= now
    """
    now = timezone.now()
    return News.objects.filter(
        send_notification=True,
        auto_notification_sent=False,
        notification_delay_hours__isnull=False
    ).filter(
        created_at__lte=now - timezone.timedelta(hours=0)  # just for clarity
    )


def mark_news_as_sent(news_instance):
    """
    Marks a News instance as notification sent and updates notification_datetime
    """
    news_instance.auto_notification_sent = True
    news_instance.notification_datetime = timezone.now()
    news_instance.save()
    logger.info(f"News {news_instance.id} marked as sent.")


def send_news_notification(news_instance):
    """
    Sends FCM notification for a given News instance
    """
    all_tokens = list(DeviceToken.objects.values_list("token", flat=True))
    if not all_tokens:
        logger.warning("No device tokens found, skipping notification.")
        return 0

    try:
        # Call your existing FCM function
        send_fcm_notification(news_instance, all_tokens)
        logger.info(f"Notification sent for News {news_instance.id} to {len(all_tokens)} devices.")
        return len(all_tokens)
    except Exception as e:
        logger.error(f"Failed to send notification for News {news_instance.id}: {e}")
        return 0


def process_scheduled_news():
    """
    Main utility function for scheduled task
    - Finds all news ready for notification
    - Sends notification
    - Marks as sent
    """
    news_to_send = get_scheduled_news_to_send()
    total_sent = 0

    for news in news_to_send:
        # Calculate scheduled time
        scheduled_time = news.created_at + timezone.timedelta(hours=news.notification_delay_hours or 0)
        if scheduled_time <= timezone.now():
            # Send notification
            sent_count = send_news_notification(news)
            if sent_count > 0:
                mark_news_as_sent(news)
                total_sent += 1

    logger.info(f"Processed {len(news_to_send)} scheduled news, notifications sent: {total_sent}")
    return total_sent



# news/tasks.py
from celery import shared_task
from news.utils import process_scheduled_news  # <-- changed from notifications.utils

@shared_task
def send_scheduled_news_notifications():
    process_scheduled_news()
