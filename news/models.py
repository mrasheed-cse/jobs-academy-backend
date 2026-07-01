from django.db import models
from django.conf import settings
# from django.utils.text import slugify

from django.utils import timezone
from datetime import timedelta


class NewsCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    # slug = models.SlugField(unique=True)

    
    # def save(self, *args, **kwargs):
    #     if not self.slug:
    #         self.slug = slugify(self.name)
    #     super().save(*args, **kwargs)
    def __str__(self):
        return self.name
    
    
    
    
class News(models.Model):
    category = models.ForeignKey(
        NewsCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="news"
    )

    title = models.CharField(max_length=255)
    content = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_date = models.DateTimeField(null=True, blank=True)

    
    # 🔔 Notification system
    send_notification = models.BooleanField(
        default=False,
        help_text="Enable notification for this news"
    )

    notification_delay_hours = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Enter hours after which notification will be sent"
    )

    notification_datetime = models.DateTimeField(
        null=True,
        blank=True,
        editable=False
    )

    auto_notification_sent = models.BooleanField(
        default=False,
        help_text="Auto updated after notification is sent"
    )
    
    notification_expire_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="After this date, notification will never be sent"
    )


    def save(self, *args, **kwargs):
        """
        Calculate notification time ONLY ONCE
        """
        if (
            self.send_notification
            and self.notification_delay_hours
            and not self.notification_datetime
        ):
            self.notification_datetime = timezone.now() + timedelta(
                hours=self.notification_delay_hours
            )

        super().save(*args, **kwargs)

    def is_ready_for_notification(self):
        now = timezone.now()

        if not self.send_notification:
            return False

        if self.auto_notification_sent:
            return False

        if not self.notification_datetime:
            return False

        if now < self.notification_datetime:
            return False

        # ❌ Expired — NEVER SEND
        if self.notification_expire_at and now > self.notification_expire_at:
            return False

        return True

    def mark_expired(self):
        if self.notification_expire_at and timezone.now() > self.notification_expire_at:
            self.send_notification = False
            self.save(update_fields=["send_notification"])


    def __str__(self):
        return self.title




class NewsImage(models.Model):
    news = models.ForeignKey(
        News, 
        related_name="images", 
        on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to="news_images/")

    def __str__(self):
        return f"Image for {self.news.title}"
