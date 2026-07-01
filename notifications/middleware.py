from django.utils.deprecation import MiddlewareMixin
from .models import *
from rest_framework_simplejwt.authentication import JWTAuthentication

from rest_framework.request import Request as DRFRequest

# class ActivityLoggerMiddleware(MiddlewareMixin):
#     def process_request(self, request):
#         # Skip DRF API views
#         if isinstance(request, DRFRequest) or request.path.startswith('/api/'):
#             return

#         device_id = request.COOKIES.get('device_id')
#         ip_address = self.get_client_ip(request)
#         fcm_token = self.get_fcm_token(request)
#         jwt_token = self.get_jwt_token(request)
#         path = request.path
#         method = request.method

#         user = None
#         if jwt_token:
#             try:
#                 from rest_framework_simplejwt.authentication import JWTAuthentication
#                 validated_user = JWTAuthentication().authenticate(request)
#                 if validated_user:
#                     user = validated_user[0]
#                     request.user = user
#             except Exception:
#                 pass

#         if device_id:
#             UserActivity.objects.create(
#                 user=user,
#                 device_id=device_id,
#                 token=fcm_token,
#                 ip_address=ip_address,
#                 path=path,
#                 method=method
#             )

#     def get_fcm_token(self, request):
#         token = request.headers.get('X-FCM-Token')
#         if token:
#             return token.strip()
#         return request.COOKIES.get('fcm_token')

#     def get_jwt_token(self, request):
#         auth_header = request.META.get('HTTP_AUTHORIZATION', '')
#         if auth_header.startswith('Bearer '):
#             return auth_header.split(' ')[1].strip()
#         return request.COOKIES.get('access_token')

#     def get_client_ip(self, request):
#         x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
#         if x_forwarded_for:
#             return x_forwarded_for.split(',')[0].strip()
#         return request.META.get('REMOTE_ADDR')


class ActivityLoggerMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Skip API views & assets
        EXCLUDED_PATHS = (
            '/api/',
            '/admin/',
            '/favicon.ico',
            '/media/',
            '/auth/',
            '/OneSignalSDK.sw.js',
            '/firebase-messaging-sw.js',
            '/OneSignalSDKWorker.js',
        )
        if request.path.startswith(EXCLUDED_PATHS):
            return

        # Extract values from cookies
        device_id = request.COOKIES.get('device_id')
        fcm_token = request.COOKIES.get('fcm_token')
        jwt_token = request.COOKIES.get('access_token')

        ip_address = self.get_client_ip(request)
        path = request.path
        method = request.method

        user = None
        if jwt_token:
            try:
                # Manually authenticate using JWT from cookie
                validated_user = JWTAuthentication().authenticate(request)
                if validated_user:
                    user = validated_user[0]
                    request.user = user  # override request.user
            except Exception:
                pass  # Invalid token, treat as guest

        device = None
        if device_id and fcm_token:
            # Get or create device record
            device, _ = DeviceToken.objects.get_or_create(
                device_id=device_id,
                defaults={
                    "user": user,
                    "token": fcm_token,
                    "device_type": "web",  # adjust if you can detect device type
                    "ip_address": ip_address,
                },
            )
            # If token changed or user updated → update record
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
            if updated:
                device.save()

        # Log activity
        UserActivity.objects.create(
            user=user,
            device=device,
            path=path,
            method=method,
            ip_address=ip_address,
        )

    def get_client_ip(self, request):
        """Get client IP from request headers"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
    
    
    
class ActivityLoggerMixin:
    def log_activity(self, request):
        device_id = request.COOKIES.get('device_id')
        ip_address = request.META.get('REMOTE_ADDR')
        path = request.path
        method = request.method

        if device_id:
            UserActivity.objects.create(
                user=request.user if request.user.is_authenticated else None,
                device_id=device_id,
                ip_address=ip_address,
                path=path,
                method=method
            )
