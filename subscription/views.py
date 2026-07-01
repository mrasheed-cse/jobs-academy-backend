import uuid
from rest_framework import viewsets, permissions, generics
from rest_framework.response import Response
from django.utils import timezone
from django.utils.timezone import now
from datetime import date
from rest_framework.views import APIView
from datetime import timedelta
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from rest_framework import status
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from .models import (
    SubscriptionPlanTier, SubscriptionPlanPrice,
    PlanExamAccessLimit, UserSubscription, UserExamAccess
)
from .serializers import (
    SubscriptionPlanTierSerializer, SubscriptionPlanPriceSerializer,
    PlanExamAccessLimitSerializer, UserSubscriptionSerializer,
    UserExamAccessSerializer
)
from quiz.models import Exam, PastExam  # adjust import as needed


class SubscriptionPlanTierViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SubscriptionPlanTier.objects.all()
    serializer_class = SubscriptionPlanTierSerializer
    permission_classes = [permissions.AllowAny]


class SubscriptionPlanPriceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SubscriptionPlanPrice.objects.select_related('plan_tier').all()
    serializer_class = SubscriptionPlanPriceSerializer
    permission_classes = [permissions.AllowAny]


class PlanExamAccessLimitViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PlanExamAccessLimit.objects.select_related('plan_tier', 'content_type').all()
    serializer_class = PlanExamAccessLimitSerializer
    permission_classes = [permissions.AllowAny]


class UserSubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = UserSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserSubscription.objects.filter(user=self.request.user, is_active=True)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)



class UserExamAccessViewSet(viewsets.ModelViewSet):
    serializer_class = UserExamAccessSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserExamAccess.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        content_type = serializer.validated_data['content_type']
        object_id = serializer.validated_data['object_id']
        content_model = content_type.model_class()
        instance = get_object_or_404(content_model, pk=object_id)

        plan = UserSubscription.objects.filter(user=self.request.user, is_active=True).first()
        if not plan:
            return Response({"error": "No active subscription"}, status=400)

        access_limit = PlanExamAccessLimit.objects.filter(
            plan_tier=plan.plan,
            content_type=content_type
        ).first()

        if access_limit:
            access_count = UserExamAccess.objects.filter(
                user=self.request.user,
                content_type=content_type
            ).count()
            if access_count >= access_limit.max_access_count:
                return Response({"error": "Access limit reached"}, status=403)

        serializer.save(user=self.request.user)


class ExamPermissionCheckView(APIView):
    permission_classes = [IsAuthenticated]

    def get_exam(self, exam_id):
        """
        Try to get Exam by UUID, or PastExam by int.
        """
        try:
            parsed_id = uuid.UUID(str(exam_id))
            return Exam.objects.get(exam_id=parsed_id)
        except (ValueError, Exam.DoesNotExist):
            pass

        try:
            parsed_id = int(exam_id)
            return PastExam.objects.get(id=parsed_id)
        except (ValueError, PastExam.DoesNotExist):
            return None

    def get(self, request, exam_id):
        user = request.user

        # Step 1: Validate Exam
        exam = self.get_exam(exam_id)
        if not exam:
            return Response({'has_access': False, 'reason': 'exam_not_found'}, status=404)

        object_id = exam.exam_id if hasattr(exam, 'exam_id') else exam.id
        # Step 2: Validate User Subscription
        subscriptions = UserSubscription.objects.filter(user=user, is_active=True)
        # Step 3: Trial Access for New Users
        today = date.today()
        trial_end_date = user.date_joined.date() + timedelta(days=7)
        if not subscriptions.exists() and today <= trial_end_date:
            # Allow access during trial period
            exam_ct = ContentType.objects.get_for_model(type(exam))

            # already_accessed = UserExamAccess.objects.filter(
            #     user=user,
            #     content_type=exam_ct,
            #     object_id=object_id
            # ).exists()

            # if already_accessed:
            #     return Response({'has_access': True})

            # UserExamAccess.objects.create(
            #     user=user,
            #     content_type=exam_ct,
            #     object_id=object_id
            # )

            return Response({'has_access': True, 'trial': True})
        if not subscriptions.exists():
            return Response({'has_access': False, 'reason': 'no_subscription'}, status=403)

        subscription = subscriptions.order_by('-end_date').first()
        if subscription.end_date and subscription.end_date < date.today():
            subscription.is_active = False
            subscription.save(update_fields=["is_active"])
            return Response({'has_access': False, 'reason': 'subscription_expired'}, status=403)

        # Step 3: Get Content Type for current exam type
        exam_ct = ContentType.objects.get_for_model(type(exam))

        # Step 4: Get Plan Limit
        try:
            plan_limit = PlanExamAccessLimit.objects.get(
                plan_tier=subscription.plan,
                content_type=exam_ct
            )
        except PlanExamAccessLimit.DoesNotExist:
            return Response({'has_access': False, 'reason': 'exam_not_allowed_in_plan'}, status=403)

        # Step 5: Check if user already accessed this exam
        already_accessed = UserExamAccess.objects.filter(
            user=user,
            content_type=exam_ct,
            object_id=object_id
        ).exists()

        if already_accessed:
            # ✅ Already accessed → allow repeat access
            return Response({'has_access': True})

        # Step 6: Check total unique accessed exams
        unique_exam_count = UserExamAccess.objects.filter(
            user=user,
            content_type=exam_ct
        ).values('object_id').distinct().count()

        if unique_exam_count >= plan_limit.max_access_count:
            # ❌ Access limit reached and new exam → block
            return Response({'has_access': False, 'reason': 'access_limit_reached'}, status=403)

        # Step 7: Log new access
        UserExamAccess.objects.create(
            user=user,
            content_type=exam_ct,
            object_id=object_id
        )

        return Response({'has_access': True})