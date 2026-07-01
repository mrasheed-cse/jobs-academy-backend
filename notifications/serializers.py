from rest_framework import serializers
from .models import DeviceToken, UserActivity, NotificationLog, NotificationClick


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = [
            "id",
            "user",
            "token",
            "device_type",
            "device_id",
            "ip_address",
            "user_agent",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class UserActivitySerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    device = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = UserActivity
        fields = [
            "id",
            "user",
            "device",
            "path",
            "method",
            "ip_address",
            "timestamp",
        ]
        read_only_fields = ["timestamp"]


class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = [
            "id",
            "title",
            "body",
            "tokens",
            "success_count",
            "failure_count",
            "sent_at",
        ]
        read_only_fields = ["success_count", "failure_count", "sent_at"]


class NotificationClickSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    device = serializers.StringRelatedField(read_only=True)
    notification = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = NotificationClick
        fields = [
            "id",
            "user",
            "device",
            "notification",
            "target_url",
            "clicked_at",
            "ip_address",
            "user_agent",
        ]
        read_only_fields = ["clicked_at"]




class LogActivityInputSerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=255)
    token = serializers.CharField(max_length=255, required=False, allow_blank=True)
    path = serializers.CharField(max_length=500)
    method = serializers.CharField(max_length=10, default="GET")
    ip_address = serializers.IPAddressField(required=False)


class SendNotificationInputSerializer(serializers.Serializer):
    tokens = serializers.ListField(
        child=serializers.CharField(), allow_empty=False
    )
    title = serializers.CharField(max_length=255)
    body = serializers.CharField()
    image = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    url = serializers.URLField(required=False, allow_blank=True, allow_null=True)
