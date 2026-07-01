from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class DeviceToken(models.Model):
    """
    Stores FCM tokens for both logged-in and guest users.
    """
    DEVICE_TYPES = (
        ('web', 'Web'),
        ('android', 'Android'),
        ('ios', 'iOS'),
    )

    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="device_tokens"
    )
    token = models.CharField(max_length=255, unique=True)
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES)
    device_id = models.CharField(max_length=255, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['device_id']),
            models.Index(fields=['user']),
            models.Index(fields=['ip_address']),
        ]
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.device_type} - {self.token[:10]}..."


class UserActivity(models.Model):
    """
    Logs page visits for both guests and logged-in users.
    """
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activities"
    )
    device = models.ForeignKey(
        DeviceToken,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activities"
    )
    path = models.CharField(max_length=500)
    method = models.CharField(max_length=10)
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['path']),
            models.Index(fields=['user']),
            models.Index(fields=['timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.device or 'Unknown device'} → {self.path} ({self.method})"


class NotificationLog(models.Model):
    """
    Records each notification attempt and delivery stats.
    """
    title = models.CharField(max_length=255)
    body = models.TextField()
    tokens = models.JSONField(help_text="List of FCM tokens")
    success_count = models.PositiveIntegerField(default=0)
    failure_count = models.PositiveIntegerField(default=0)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"Notification: {self.title} ({self.sent_at:%Y-%m-%d %H:%M})"


class NotificationClick(models.Model):
    """
    Tracks when a notification is clicked by a user or guest.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_clicks",
        help_text="User who clicked (if authenticated)"
    )
    device = models.ForeignKey(
        DeviceToken,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_clicks"
    )
    notification = models.ForeignKey(
        NotificationLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clicks",
        help_text="The notification that was clicked"
    )
    target_url = models.CharField(max_length=500)
    clicked_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-clicked_at"]

    def __str__(self):
        actor = self.user or "Anonymous"
        return f"{actor} clicked {self.notification or 'N/A'} → {self.target_url}"
