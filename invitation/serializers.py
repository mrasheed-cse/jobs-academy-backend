# serializers.py

from rest_framework import serializers
from .models import ExamInvite
from django.contrib.auth import get_user_model

User = get_user_model()

class ExamInviteSerializer(serializers.ModelSerializer):
    exam = serializers.StringRelatedField()
    invited_by = serializers.StringRelatedField()
    invited_user_email = serializers.EmailField(source='invited_user.email', read_only=True)
    exam_id = serializers.StringRelatedField()
    class Meta:
        model = ExamInvite
        fields = ['exam', 'invited_by', 'invited_user', 'invited_user_email', 'token', 'invited_at', 'is_accepted', 'exam_id']
        read_only_fields = ['token', 'invited_at', 'is_accepted', 'invited_at']
