# notifications/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import *
from .serializers import *
from rest_framework.permissions import AllowAny, IsAdminUser
from django.apps import apps
from django.utils.timezone import now
from django.db.models import Count, Q
from django.utils.timezone import now, timedelta
from django.db import transaction
# Example usage


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .fcm_service import send_fcm_message


class SendNotificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        device_token = request.data.get("device_token")
        title = request.data.get("title", "Default Title")
        body = request.data.get("body", "Default Body")

        if not device_token:
            return Response({"error": "Device token is required"}, status=400)

        result = send_fcm_message(device_token, title, body)
        return Response(result) 



import firebase_admin
from firebase_admin import credentials, messaging 
import os
from django.shortcuts import render, HttpResponse
import time

def send_data_message(token, title, body, image_url=None, click_action_url=None):
    
    # print(token, title, body, image_url)
    data = {
        "title":title,
        "body":body,
        "icon":"https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQCj1uO57grh0JddNU0gc13RFPBqZiwmrRFnw&s",
        "timestamp": str(time.time())  
    }
    if image_url:
        data["image"]=image_url
    
    if click_action_url:
        notification_id = str(int(time.time()))
        # Create tracking URL (redirect style)
        tracking_url = (
            f"https://jobs.academy/api/track-click/"
            f"?next={click_action_url}"
            f"&notification_id={notification_id}"
            f"&fcm_token={token}"
        )
        
        
        data["url"] = tracking_url  # This will be used in the service worker
        
    message = messaging.Message(data=data, token=token)

    response = messaging.send(message)
    print("Data message sent: ", response)
     
     
     

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import DeviceToken
from .serializers import DeviceTokenSerializer
from django.db import connection
from django.db import DatabaseError
import logging

logger = logging.getLogger(__name__)


class RegisterDeviceTokenView(APIView):
    permission_classes = []  # Allow both guests and authenticated users

    def post(self, request):
        # Step 1: Extract Authorization header
        auth_header = request.headers.get('Authorization')
        print("Authorization header:", auth_header)

        access_token = None
        if auth_header and auth_header.startswith('Bearer '):
            access_token = auth_header.split(' ')[1]
            print("Access token:", access_token)

        # Step 2: Try to authenticate user via JWT
        user = None
        try:
            validated_user = JWTAuthentication().authenticate(request)
            if validated_user:
                user = validated_user[0]
                print("Authenticated user:", user)
        except Exception as e:
            print("JWT authentication failed:", str(e))

        # Step 3: Extract token from request
        token = request.data.get('token')
        if not token:
            return Response({'error': 'Missing token'}, status=status.HTTP_400_BAD_REQUEST)

        # Step 4: Create or update DeviceToken
        instance, created = DeviceToken.objects.get_or_create(token=token)

        instance.device_type = request.data.get('device_type', instance.device_type)
        instance.device_id = request.data.get('device_id', instance.device_id)
        instance.ip_address = request.data.get('ip_address', instance.ip_address)

        # Step 5: Link user if authenticated
        if user and user != instance.user:
            print(f"Linking token to user: {user}")
            instance.user = user

        instance.save()

        # Step 6: Respond with status
        return Response({
            'message': 'Token created' if created else 'Token updated',
            'token': instance.token
        }, status=status.HTTP_200_OK)


# test query
# SELECT DISTINCT id, user_id, device_id
# FROM notifications_useractivity
# WHERE user_id IS NOT NULL
#   AND user_id NOT IN (
#     SELECT user_id
#     FROM notifications_useractivity
#     WHERE path = '/quiz/'
#       AND timestamp >= datetime('now', '-30 days')
#   )



# SELECT
#     user_id,
#     device_id,
#     token
# FROM notifications_devicetoken
# WHERE device_type = 'android';


ALLOWED_MODELS = ['UserActivity', 'DeviceToken']

class SegmentUsersRawView(APIView):
    """
    Accepts raw SELECT queries only and executes them on the database.

    Restricted to admin users, and only SELECT statements are permitted
    (no INSERT/UPDATE/DELETE/DDL), to prevent this endpoint from being
    used for arbitrary SQL execution.
    """
    permission_classes = [IsAdminUser]

    def post(self, request, format=None):
        raw_query = request.data.get("query")
        if not raw_query:
            return Response({"error": "Missing 'query' in request."}, status=status.HTTP_400_BAD_REQUEST)

        normalized = raw_query.strip().lower()
        if not normalized.startswith("select"):
            return Response({"error": "Only SELECT queries are allowed."}, status=status.HTTP_400_BAD_REQUEST)

        # Reject queries containing multiple statements or write/DDL keywords,
        # even if disguised inside the SELECT.
        forbidden_keywords = [
            "insert", "update", "delete", "drop", "alter", "truncate",
            "create", "grant", "revoke", "--", ";",
        ]
        if any(keyword in normalized for keyword in forbidden_keywords):
            return Response({"error": "Query contains disallowed keywords."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with connection.cursor() as cursor:
                cursor.execute(raw_query)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

            # Normalize expected fields
            def extract(row):
                row_dict = dict(zip(columns, row))
                return {
                    "user": row_dict.get("user_id"),
                    "device_id": row_dict.get("device_id"),
                    "token": row_dict.get("token")
                }

            users = [extract(row) for row in rows]
            return Response({"users": users})

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        
# class SendNotificationView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         serializer = SendNotificationInputSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         data = serializer.validated_data

#         tokens = data['tokens']
#         title = data['title']
#         body = data['body']
#         image_url = data.get('image')
#         click_action_url = data.get('url')

#         sent_count = 0
#         failed_count = 0

#         # 🚀 Batch send if many tokens
#         if len(tokens) > 10:  # Adjust threshold if needed
#             message = messaging.MulticastMessage(
#                 notification=messaging.Notification(
#                     title=title,
#                     body=body,
#                     image=image_url,
#                 ),
#                 data={"url": click_action_url} if click_action_url else {},
#                 tokens=tokens,
#             )

#             # Use send_each_for_multicast in your current firebase-admin version
#             responses = messaging.send_each_for_multicast(message)

#             sent_count = sum(1 for r in responses.responses if r.success)
#             failed_count = sum(1 for r in responses.responses if not r.success)


#         else:
#             # Fallback: send individually
#             for token in tokens:
#                 try:
#                     messaging.send(
#                         messaging.Message(
#                             notification=messaging.Notification(title, body, image_url),
#                             data={"url": click_action_url} if click_action_url else {},
#                             token=token
#                         )
#                     )
#                     sent_count += 1
#                 except Exception as e:
#                     logger.error(f"Notification failed for token={token}, error={e}")
#                     failed_count += 1

#         # 📝 Log the notification attempt
#         NotificationLog.objects.create(
#             title=title,
#             body=body,
#             tokens=tokens,
#             success_count=sent_count,
#             failure_count=failed_count
#         )

#         return Response({
#             'message': f'Notification send attempt complete for {len(tokens)} tokens.',
#             'sent_count': sent_count,
#             'failed_count': failed_count
#         }, status=status.HTTP_200_OK)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from firebase_admin import messaging
import logging

from .serializers import SendNotificationInputSerializer
from .models import NotificationLog

logger = logging.getLogger(__name__)

# Utility function to split a list into chunks (FCM limit is 500)
def chunk_list(data, size):
    """Yield successive n-sized chunks from data."""
    for i in range(0, len(data), size):
        yield data[i:i + size]
        
        
class SendNotificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SendNotificationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        title = data["title"]
        body = data["body"]
        image_url = data.get("image") or ""
        click_action_url = data.get("url") or ""

        notification_data = {
            "title": title,
            "body": body,
            "image": image_url,
            "url": click_action_url,
        }

        all_tokens = data["tokens"]
        total_tokens = len(all_tokens)

        if total_tokens == 0:
            return Response(
                {"error": "No device tokens found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sent_count = 0
        failed_count = 0
        tokens_to_delete = []

        try:
            # -------- MULTICAST --------
            if total_tokens >= 10:
                for batch_tokens in chunk_list(all_tokens, 500):
                    message = messaging.MulticastMessage(
                        notification=messaging.Notification(
                            title=title,
                            body=body,
                            image=image_url if image_url else None,
                        ),
                        data=notification_data,
                        tokens=batch_tokens,
                    )

                    response = messaging.send_each_for_multicast(message)

                    sent_count += response.success_count
                    failed_count += response.failure_count

                    for i, res in enumerate(response.responses):
                        if not res.success and res.exception:
                            code = getattr(res.exception, "code", "")
                            token = batch_tokens[i]

                            if code in (
                                "messaging/invalid-registration-token",
                                "messaging/registration-token-not-registered",
                            ):
                                tokens_to_delete.append(token)
                            else:
                                logger.error(
                                    f"FCM error token={token}, code={code}, error={res.exception}"
                                )

            # -------- SINGLE SEND --------
            else:
                for token in all_tokens:
                    try:
                        messaging.send(
                            messaging.Message(
                                notification=messaging.Notification(
                                    title=title,
                                    body=body,
                                    image=image_url if image_url else None,
                                ),
                                data=notification_data,
                                token=token,
                            )
                        )
                        sent_count += 1
                    except exceptions.UnregisteredError:
                        tokens_to_delete.append(token)
                        failed_count += 1
                    except Exception as e:
                        logger.error(f"FCM send failed token={token}, error={e}")
                        failed_count += 1

            # -------- CLEAN INVALID TOKENS --------
            if tokens_to_delete:
                DeviceToken.objects.filter(token__in=tokens_to_delete).delete()
                logger.info(f"Deleted {len(tokens_to_delete)} invalid FCM tokens")

        except Exception as e:
            logger.error("FCM catastrophic failure", exc_info=True)
            failed_count = total_tokens - sent_count

        return Response(
            {
                "message": "Notification processing completed",
                "total_tokens": total_tokens,
                "sent": sent_count,
                "failed": failed_count,
                "invalid_tokens_removed": len(tokens_to_delete),
            },
            status=status.HTTP_200_OK,
        )


class LogActivityView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data

        device_id = data.get('device_id')
        fcm_token = data.get('token')  # This is FCM token
        path = data.get('path')
        method = data.get('method', 'GET')
        ip_address = data.get('ip_address') or self.get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        user = None

        # JWT from header Authorization: Bearer <token>
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            try:
                validated_user = JWTAuthentication().authenticate(request)
                if validated_user:
                    user = validated_user[0]
            except Exception:
                pass  # Invalid token, treat as guest

        # Required fields check
        if not device_id or not path:
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure device exists
        device = None
        if device_id and fcm_token:
            device, _ = DeviceToken.objects.get_or_create(
                device_id=device_id,
                defaults={
                    "user": user,
                    "token": fcm_token,
                    "device_type": "web",  # adjust if you can detect platform
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                },
            )
            updated = False
            if user and device.user != user:
                device.user = user
                updated = True
            if fcm_token and device.token != fcm_token:
                device.token = fcm_token
                updated = True
            if ip_address and device.ip_address != ip_address:
                device.ip_address = ip_address
                updated = True
            if user_agent and device.user_agent != user_agent:
                device.user_agent = user_agent
                updated = True
            if updated:
                device.save()

        # Save activity
        UserActivity.objects.create(
            user=user,
            device=device,
            path=path,
            method=method,
            ip_address=ip_address,
        )

        return Response({'status': 'activity logged'}, status=status.HTTP_201_CREATED)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
    
    
    
class TrackClickAPIView(APIView):
    permission_classes = [AllowAny]  # allow both logged-in and anonymous users

    def post(self, request):
        notification_id = request.data.get("notification_id")
        target_url = request.data.get("target_url", "/")
        fcm_token = request.data.get("fcm_token")

        user = request.user if request.user.is_authenticated else None
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        # Resolve Notification object
        notification = None
        if notification_id:
            notification = NotificationLog.objects.filter(id=notification_id).first()

        # Resolve DeviceToken object
        device = None
        if fcm_token:
            device = DeviceToken.objects.filter(token=fcm_token).first()

        # Create click log
        click = NotificationClick.objects.create(
            user=user,
            device=device,
            notification=notification,
            target_url=target_url,
            ip_address=ip_address,
            user_agent=user_agent,
            clicked_at=now()
        )

        return Response(
            {
                "status": "success",
                "message": "Click recorded",
                "click_id": click.id,
            },
            status=status.HTTP_201_CREATED,
        )

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
    
    


class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = now().date()
        last_7_days = today - timedelta(days=7)

        # Device stats
        device_counts = DeviceToken.objects.values('device_type').annotate(count=Count('id'))

        # Active users/devices
        active_devices = DeviceToken.objects.filter(is_active=True).count()
        active_users = DeviceToken.objects.filter(user__isnull=False, is_active=True).values('user').distinct().count()

        # User activity
        recent_activity = UserActivity.objects.filter(timestamp__date__gte=last_7_days).count()
        top_paths = UserActivity.objects.values('path').annotate(count=Count('id')).order_by('-count')[:5]

        # Notifications
        recent_notifications = NotificationLog.objects.filter(sent_at__date__gte=last_7_days).count()
        total_clicks = NotificationClick.objects.count()
        click_through_rate = (
            total_clicks / NotificationLog.objects.aggregate(total=Count('id'))['total']
            if NotificationLog.objects.exists() else 0
        )

        # Chart data (example: clicks per day)
        clicks_per_day = NotificationClick.objects.filter(clicked_at__date__gte=last_7_days)\
            .extra({'day': "date(clicked_at)"}).values('day')\
            .annotate(count=Count('id')).order_by('day')

        return Response({
            "device_stats": list(device_counts),
            "active_devices": active_devices,
            "active_users": active_users,
            "recent_activity_count": recent_activity,
            "top_paths": list(top_paths),
            "recent_notifications": recent_notifications,
            "total_clicks": total_clicks,
            "click_through_rate": round(click_through_rate, 2),
            "clicks_per_day": list(clicks_per_day),
        })
