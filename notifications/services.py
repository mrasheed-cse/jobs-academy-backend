# notifications/services.py
from firebase_admin import messaging
from .models import DeviceToken

def send_custom_notification(title, body):
    tokens = list(DeviceToken.objects.values_list("token", flat=True))

    if not tokens:
        return "No devices registered"

    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        tokens=tokens,
    )

    response = messaging.send_multicast(message)
    return f"Sent: {response.success_count}, Failed: {response.failure_count}"
