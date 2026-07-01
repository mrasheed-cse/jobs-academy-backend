from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from .models import *

from django.contrib.auth import get_user_model
User = get_user_model()
from django.utils import timezone
from datetime import timedelta



# 2. SubscriptionPlanPrice Serializer
class SubscriptionPlanPriceSerializer(serializers.ModelSerializer):
    plan_tier = serializers.SlugRelatedField(slug_field='name', queryset=SubscriptionPlanTier.objects.all())

    class Meta:
        model = SubscriptionPlanPrice
        fields = '__all__'
        



# 3. PlanExamAccessLimit Serializer
class PlanExamAccessLimitSerializer(serializers.ModelSerializer):
    plan_tier = serializers.SlugRelatedField(slug_field='name', queryset=SubscriptionPlanTier.objects.all())
    content_type = serializers.SlugRelatedField(slug_field='model', queryset=ContentType.objects.all())

    class Meta:
        model = PlanExamAccessLimit
        fields = '__all__'
        
        
class SubscriptionPlanTierSerializer(serializers.ModelSerializer):
    prices = SubscriptionPlanPriceSerializer(many=True, read_only=True)
    exam_access_limits = PlanExamAccessLimitSerializer(many=True, read_only=True)

    class Meta:
        model = SubscriptionPlanTier
        fields = '__all__'
class UserSubscriptionSerializer(serializers.ModelSerializer):
    price = serializers.PrimaryKeyRelatedField(
        queryset=SubscriptionPlanPrice.objects.all(),
        write_only=True
    )

    class Meta:
        model = UserSubscription
        fields = ['id', 'plan', 'start_date', 'end_date', 'is_active', 'price']
        read_only_fields = ['plan', 'start_date', 'end_date', 'is_active']

    def create(self, validated_data):
        price = validated_data.pop('price')

        duration_map = {
            'weekly': 7,
            'biweekly': 14,
            'monthly': 30,
            'quarterly': 90,
            'halfyearly': 180,
        }

        days = duration_map.get(price.duration)
        if not days:
            raise serializers.ValidationError({'price': 'Invalid duration'})

        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=days)

        user = self.context['request'].user

        subscription, created = UserSubscription.objects.get_or_create(
            user=user,
            defaults={
                'plan': price.plan_tier,
                'start_date': start_date,
                'end_date': end_date,
                'is_active': True
            }
        )

        if not created:
            # Update the existing subscription
            subscription.plan = price.plan_tier
            subscription.start_date = start_date
            subscription.end_date = end_date
            subscription.is_active = True
            subscription.save()

        return subscription

# 4. UserSubscription Serializer
# class UserSubscriptionSerializer(serializers.ModelSerializer):
#     user = serializers.HiddenField(default=serializers.CurrentUserDefault())
#     plan = serializers.SlugRelatedField(slug_field='name', queryset=SubscriptionPlanTier.objects.all())
#     price = serializers.PrimaryKeyRelatedField(queryset=SubscriptionPlanPrice.objects.all())

#     class Meta:
#         model = UserSubscription
#         fields = '__all__'

    # def create(self, validated_data):
    #     price = validated_data['price']
    #     validated_data['start_date'] = timezone.now().date()

    #     duration_days_map = {
    #         'weekly': 7,
    #         'biweekly': 14,
    #         'monthly': 30,
    #         'quarterly': 90,
    #         'halfyearly': 180,
    #     }

    #     days = duration_days_map.get(price.duration, 30)
    #     validated_data['end_date'] = validated_data['start_date'] + timedelta(days=days)

    #     return super().create(validated_data)



# 5. UserExamAccess Serializer
class UserExamAccessSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    content_type = serializers.SlugRelatedField(slug_field='model', queryset=ContentType.objects.all())

    class Meta:
        model = UserExamAccess
        fields = ['id', 'user', 'content_type', 'object_id', 'accessed_at']
