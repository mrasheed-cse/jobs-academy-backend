from rest_framework import viewsets, permissions
from django.utils import timezone
from .models import *
from .serializers import *
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from firebase_admin import messaging
import logging
from notifications.models import DeviceToken, NotificationLog
from django.db import transaction
logger = logging.getLogger(__name__)

class IsAdminUserRole(permissions.BasePermission):
    """Allows admin, teacher, or Django staff. Fixed: original had role=="Admin"
    (capital A) but model stores "admin" (lowercase)."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            getattr(request.user, "role", None) in ("admin", "teacher")
            or request.user.is_staff
        )

# news/pagination.py
from rest_framework.pagination import PageNumberPagination

# Utility function to split a list into chunks (FCM limit is 500)
def chunk_list(data, size):
    """Yield successive n-sized chunks from data."""
    for i in range(0, len(data), size):
        yield data[i:i + size]
        
class NewsPagination(PageNumberPagination):
    page_size = 10  # items per page
    page_size_query_param = "page_size"  # optional, allow client to override
    max_page_size = 9
    
# class NewsViewSet(viewsets.ModelViewSet):
#     queryset = News.objects.all().order_by("-created_at")
#     serializer_class = NewsSerializer
#     pagination_class = NewsPagination  # 👈 Add this line
    
    
#     def get_permissions(self):
#         if self.action in ["create", "update", "partial_update", "destroy"]:
#             # Require authentication for creating, updating, and deleting.
#             return [permissions.IsAuthenticated()]
#         # Allow any user (authenticated or not) to view news details or list.
#         return [permissions.AllowAny()]
    
    
#     @action(detail=True, methods=['get'])
#     def recommended(self, request, pk=None):
#         # Exclude current news and return latest 5
#         queryset = News.objects.exclude(id=pk).order_by('-created_at')[:5]
#         serializer = self.get_serializer(queryset, many=True)
#         return Response(serializer.data)
    
#     def perform_create(self, serializer):
#         """Create a News object and send notification if requested."""
#         news_instance = serializer.save(author=self.request.user, published_date=timezone.now())

#         # ✅ Check if admin wants to send notification
#         send_notification = self.request.data.get("send_notification", False)

#         if str(send_notification).lower() in ["true", "1", "yes"]:
#             logger = logging.getLogger(__name__)

#             # ✅ Get all device tokens
#             tokens = list(DeviceToken.objects.values_list("token", flat=True))
#             if not tokens:
#                 logger.warning("No device tokens found — skipping notification.")
#                 return

#             # ✅ Build notification message
#             title = "📰 Latest News Update!"
#             body = f"{news_instance.title}\nStay informed — check it out now!"
#             image_url = getattr(news_instance, "image_url", None)
#             click_action_url = f"https://jobs.academy/news/details/{news_instance.id}/"

#             sent_count = 0
#             failed_count = 0

#             try:
#                 if len(tokens) > 10:
#                     # Batch send
#                     message = messaging.MulticastMessage(
#                         notification=messaging.Notification(
#                             title=title,
#                             body=body,
#                             image=image_url,
#                         ),
#                         data={"url": click_action_url} if click_action_url else {},
#                         tokens=tokens,
#                     )
#                     response = messaging.send_multicast(message)
#                     sent_count = response.success_count
#                     failed_count = response.failure_count
#                 else:
#                     # Send individually
#                     for token in tokens:
#                         try:
#                             messaging.send(
#                                 messaging.Message(
#                                     notification=messaging.Notification(title, body, image_url),
#                                     data={"url": click_action_url} if click_action_url else {},
#                                     token=token,
#                                 )
#                             )
#                             sent_count += 1
#                         except Exception as e:
#                             logger.error(f"Notification failed for token={token}, error={e}")
#                             failed_count += 1
#             except Exception as e:
#                 logger.error(f"Batch notification error: {e}")
#                 failed_count = len(tokens)

#             # ✅ Log the notification
#             NotificationLog.objects.create(
#                 title=title,
#                 body=body,
#                 tokens=tokens,
#                 success_count=sent_count,
#                 failure_count=failed_count,
#             )

class NewsCategoryViewSet(ModelViewSet):
    queryset = NewsCategory.objects.all().order_by("name")
    serializer_class = NewsCategorySerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdminUserRole()]
        return [permissions.AllowAny()]



class NewsViewSet(viewsets.ModelViewSet):
    queryset = News.objects.all().order_by("-created_at")
    serializer_class = NewsSerializer
    pagination_class = NewsPagination
    
    def get_queryset(self):
        queryset = News.objects.all().order_by("-created_at")

        # ✅ Filter by category if category_id exists
        category_id = self.request.query_params.get("category_id")
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        today = self.request.query_params.get("today")
        if today == "true":
            start = timezone.localtime().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end = start + timedelta(days=1)

            today_news = queryset.filter(
                published_date__gte=start,
                published_date__lt=end
            )

            # ✅ If today has news → return them (category-aware)
            if today_news.exists():
                return today_news

            # ✅ Else → return last 10 news (category-aware)
            return queryset[:10]

        return queryset
    
    
    # def get_queryset(self):
    #     base_queryset = News.objects.all().order_by("-created_at")

    #     today = self.request.query_params.get('today')
    #     if today == 'true':
    #         start = timezone.localtime().replace(
    #             hour=0, minute=0, second=0, microsecond=0
    #         )
    #         end = start + timedelta(days=1)

    #         today_news = base_queryset.filter(
    #             published_date__gte=start,
    #             published_date__lt=end
    #         )

    #         # ✅ If today has news → return them
    #         if today_news.exists():
    #             return today_news

    #         # ✅ Else → return last 10 news
    #         return base_queryset[:10]

    #     return base_queryset

# The URL for filtering would be: /api/news/?category_id=5
    
    
    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdminUserRole()]
        return [permissions.AllowAny()]
    
    @action(detail=True, methods=['get'])
    def recommended(self, request, pk=None):
        queryset = News.objects.exclude(id=pk).order_by('-created_at')[:5]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        """Create a News object and send a Data-Only notification."""
        category_id = self.request.data.get("category_id")
        category = None

        if category_id:
            try:
                category = NewsCategory.objects.get(id=category_id)
            except NewsCategory.DoesNotExist:
                raise ValidationError({"category_id": "Invalid category ID"})

        # 🔹 Save News with category
        news_instance = serializer.save(
            author=self.request.user,
            category=category,
            published_date=timezone.now()
        )

        send_notification = self.request.data.get("send_notification", False)

        if str(send_notification).lower() in ["true", "1", "yes"]:
            
            all_tokens = list(DeviceToken.objects.values_list("token", flat=True))
            if not all_tokens:
                logger.warning("No device tokens found — skipping notification.")
                return

            # ✅ 1. Build the Data-Only Payload (Data fields must be strings)
            # This is the single source of truth for the notification content
            title = "📰 Latest News Update!"
            body = f"{news_instance.title}\nStay informed — check it out now!"
            image_url = getattr(news_instance, "image_url", None)
            click_action_url = f"https://jobs.academy/news/details/{news_instance.id}/"

            notification_data = {
                "title": title,
                "body": body,
                "image_url": image_url if image_url else "", # Ensure string
                "url": click_action_url,
                "news_id": str(news_instance.id) # Useful for deep linking
            }
            
            total_success_count = 0
            total_failure_count = 0
            tokens_to_delete = []
            
            with transaction.atomic():
                try:
                    # Case 1: Multicast (Batch Send) for 10 or more tokens
                    if len(all_tokens) >= 10:
                        
                        for batch_tokens in chunk_list(all_tokens, 500):
                            
                            message = messaging.MulticastMessage(
                                # # *** ONLY SENDING DATA PAYLOAD ***
                                # data=notification_data,
                                # tokens=batch_tokens,
                                # # Notification key is REMOVED to prevent double notifications
                                
                                
                                notification=messaging.Notification(
                                    title=title,
                                    body=body,
                                ),
                                data=notification_data,
                                tokens=batch_tokens,
                            )
                            
                            response = messaging.send_each_for_multicast(message)
                            total_success_count += response.success_count
                            total_failure_count += response.failure_count
                            
                            # CRITICAL: Clean up invalid tokens
                            for i, result in enumerate(response.responses):
                                if not result.success and result.exception:
                                    error_code = getattr(result.exception, 'code', 'UNKNOWN')
                                    token = batch_tokens[i] 
                                    
                                    if error_code in [
                                        'messaging/invalid-registration-token',
                                        'messaging/registration-token-not-registered',
                                        'messaging/unregistered',
                                    ]:
                                        tokens_to_delete.append(token)
                                    else:
                                        logger.error(f"FCM error for token={token}. Code: {error_code}, Msg: {result.exception}")

                    # Case 2: Individual Send for less than 10 tokens
                    else:
                        for token in all_tokens:
                            try:
                                messaging.send(
                                    messaging.Message(
                                        # *** ONLY SENDING DATA PAYLOAD ***
                                        data=notification_data,
                                        token=token,
                                    )
                                )
                                total_success_count += 1
                            except exceptions.UnregisteredError:
                                tokens_to_delete.append(token)
                                total_failure_count += 1
                            except Exception as e:
                                logger.error(f"Notification failed for token={token}, error={e}")
                                total_failure_count += 1
                                
                    # Bulk Delete invalid tokens
                    if tokens_to_delete:
                        DeviceToken.objects.filter(token__in=tokens_to_delete).delete()
                        logger.info(f"Cleaned up {len(tokens_to_delete)} invalid tokens.")
                        
                except Exception as e:
                    logger.error(f"Catastrophic notification error: {e}", exc_info=True)
                    total_failure_count += len(all_tokens) - total_success_count - len(tokens_to_delete)


            # Log the notification outcome (using the data used for the send)
            NotificationLog.objects.create(
                title=title,
                body=body,
                tokens=all_tokens,
                success_count=total_success_count,
                failure_count=total_failure_count,
            )