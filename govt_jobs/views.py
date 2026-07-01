from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from .models import *
from .serializers import *
from quiz.permissions import *
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics, permissions
from firebase_admin import messaging
import logging
from notifications.models import NotificationLog


logger = logging.getLogger(__name__)  # ✅ define logger here

User = get_user_model()

class GovernmentJobViewSet(viewsets.ModelViewSet):
    queryset = GovernmentJob.objects.all().order_by('-posted_on')
    serializer_class = GovernmentJobSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        # Write operations (create, update, destroy) restricted to admin/teacher
        return [IsTeacherOrAdmin()]

    # def create(self, request, *args, **kwargs):
    #     # print("🔎 Raw request.data:", request.data)       # Shows raw data
    #     # print("🔎 Request.FILES:", request.FILES)        # Shows uploaded files
    #     # print("🔎 Request.user:", request.user)          # Shows user info

    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)

    #     # print("✅ Validated data:", serializer.validated_data)  # Shows serializer-cleaned data

    #     self.perform_create(serializer)
    #     headers = self.get_success_headers(serializer.data)
    #     return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # ✅ Check if notification should be sent
        send_notification = request.data.get("send_notification", False)
        if str(send_notification).lower() in ["true", "1", "yes"]:
            # Fetch all users who have tokens
            from notifications.models import DeviceToken  # if you store tokens in model
            tokens = list(DeviceToken.objects.values_list("token", flat=True))

            if tokens:
                 # ✅ Build notification content for users
                title = f"New Job Available!"
                body = f"🚨 {instance.title} is now open for applications. Don't miss this opportunity!"
                image_url = None  # (Optional: Add image if your job model includes one)
                click_action_url = f"https://jobs.academy/job-circular/{instance.id}/"

                sent_count = 0
                failed_count = 0

                try:
                    if len(tokens) > 10:
                        message = messaging.MulticastMessage(
                            notification=messaging.Notification(
                                title=title,
                                body=body,
                                image=image_url,
                            ),
                            data={"url": click_action_url} if click_action_url else {},
                            tokens=tokens,
                        )
                        response = messaging.send_multicast(message)
                        sent_count = response.success_count
                        failed_count = response.failure_count
                    else:
                        for token in tokens:
                            try:
                                messaging.send(
                                    messaging.Message(
                                        notification=messaging.Notification(title, body, image_url),
                                        data={"url": click_action_url} if click_action_url else {},
                                        token=token
                                    )
                                )
                                sent_count += 1
                            except Exception as e:
                                logger.error(f"Notification failed for token={token}, error={e}")
                                failed_count += 1
                except Exception as e:
                    logger.error(f"Batch notification error: {e}")
                    failed_count = len(tokens)

                # 📝 Log notification event
                NotificationLog.objects.create(
                    title=title,
                    body=body,
                    tokens=tokens,
                    success_count=sent_count,
                    failure_count=failed_count,
                )

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            print("❌ Serializer errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_update(serializer)
        return Response(serializer.data)

class NoticeViewSet(viewsets.ModelViewSet):
    queryset = Notice.objects.all().order_by("-created_at")
    serializer_class = NoticeSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsTeacherOrAdmin()]

