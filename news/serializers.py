from rest_framework import serializers
from django.utils import timezone
from .models import News, NewsImage, NewsCategory
from datetime import timedelta


class NewsImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = NewsImage
        fields = ["id", "image_url"]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if request and obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None


class NewsCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsCategory
        fields = ["id", "name"]


from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import News, NewsImage


class NewsSerializer(serializers.ModelSerializer):
    images = NewsImageSerializer(many=True, read_only=True)

    uploaded_images = serializers.ListField(
        child=serializers.ImageField(
            max_length=1000000,
            allow_empty_file=False,
            use_url=False
        ),
        write_only=True,
        required=False
    )

    # 🔔 Notification fields
    send_notification = serializers.BooleanField(required=False)
    notification_delay_hours = serializers.IntegerField(
        required=False,
        min_value=1
    )

    notification_expire_at = serializers.DateTimeField(
        required=False,
        allow_null=True
    )

    notification_datetime = serializers.DateTimeField(read_only=True)
    auto_notification_sent = serializers.BooleanField(read_only=True)

    class Meta:
        model = News
        fields = [
            "id",
            "category",
            "title",
            "content",
            "author",
            "created_at",
            "updated_at",
            "published_date",

            # 🔔 Notification
            "send_notification",
            "notification_delay_hours",
            "notification_datetime",
            "notification_expire_at",
            "auto_notification_sent",

            # 🖼 Images
            "images",
            "uploaded_images",
        ]

        read_only_fields = [
            "author",
            "created_at",
            "updated_at",
            "notification_datetime",
            "auto_notification_sent",
        ]

    # ✅ VALIDATION
    def validate(self, attrs):
        instance = self.instance
        now = timezone.now()

        send_notification = attrs.get(
            "send_notification",
            getattr(instance, "send_notification", False)
        )

        delay_hours = attrs.get(
            "notification_delay_hours",
            getattr(instance, "notification_delay_hours", None)
        )

        expire_at = attrs.get(
            "notification_expire_at",
            getattr(instance, "notification_expire_at", None)
        )

        # 🚫 Do not allow notification edits after sent
        if instance and instance.auto_notification_sent:
            if any(
                field in attrs
                for field in (
                    "send_notification",
                    "notification_delay_hours",
                    "notification_expire_at",
                )
            ):
                raise serializers.ValidationError(
                    "Notification settings cannot be modified after notification is sent."
                )

        # Delay required when notification is enabled
        if send_notification and not delay_hours:
            raise serializers.ValidationError({
                "notification_delay_hours":
                    "This field is required when send_notification is enabled."
            })

        # Delay not allowed when notification disabled
        if delay_hours and not send_notification:
            raise serializers.ValidationError({
                "send_notification":
                    "Enable send_notification to use delay hours."
            })

        # Expiry must be in the future
        if expire_at and expire_at <= now:
            raise serializers.ValidationError({
                "notification_expire_at":
                    "Expire date must be in the future."
            })

        # Expiry must be AFTER scheduled send time
        if delay_hours and expire_at:
            base_time = (
                instance.created_at
                if instance and instance.created_at
                else now
            )

            scheduled_time = base_time + timedelta(hours=delay_hours)

            if expire_at <= scheduled_time:
                raise serializers.ValidationError({
                    "notification_expire_at":
                        "Expire date must be after notification send time."
                })

        return attrs

    # ✅ CREATE
    def create(self, validated_data):
        uploaded_images = validated_data.pop("uploaded_images", [])

        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["author"] = request.user

        news = News.objects.create(**validated_data)

        for image in uploaded_images:
            NewsImage.objects.create(news=news, image=image)

        return news

    # ✅ UPDATE
    def update(self, instance, validated_data):
        uploaded_images = validated_data.pop("uploaded_images", [])

        # 🚫 Prevent re-trigger after notification sent
        if instance.auto_notification_sent:
            validated_data.pop("send_notification", None)
            validated_data.pop("notification_delay_hours", None)
            validated_data.pop("notification_expire_at", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        for image in uploaded_images:
            NewsImage.objects.create(news=instance, image=image)

        return instance
