from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import generics
from django.contrib.auth import logout
from django.contrib.auth import get_user_model
from .serializers import *
from django.core.exceptions import ObjectDoesNotExist 
from .models import CustomUser
from quiz.permissions import *
from .serializers import UserSerializer
User = get_user_model()
from django.db.models import Count, CharField
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncDate, Cast
from django.utils.timezone import now
from quiz.models import Question

class SignupView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        email = request.data.get('email')
        username = request.data.get('username')
        password = request.data.get('password')
        # print(request.data)
        try:
            # Check if user already exists (created during exam attempt)
            user = User.objects.get(phone_number=phone_number, is_active=False)
            user.email = email
            user.username = username
            if password:
                user.set_password(password)
            user.is_active = True
            user.save()
        except User.DoesNotExist:
            # Create new user
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()

        # You can apply free subscription logic here if needed
        if user.role == 'student':
            end_date = timezone.now() + timedelta(days=30)
            # Create a "free" subscription here if needed

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)
        
class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        # Assuming you're using JWT and you want to invalidate tokens client-side
        # There's no built-in JWT token invalidation in SimpleJWT; typically, tokens are cleared on the client side.
        logout(request)
        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)

class DeleteMyAccountAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        phone_number = request.data.get("phone_number")
        password = request.data.get("password")

        if not phone_number or not password:
            return Response(
                {"detail": "Phone number and password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify credentials
        user = authenticate(username=phone_number, password=password)
        if not user or user != request.user:
            return Response(
                {"detail": "Invalid phone number or password."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Delete user account
        request.user.delete()
        return Response(
            {"detail": "Your account has been deleted successfully."},
            status=status.HTTP_200_OK
        )

class UserRoleView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = request.user.role
        # role = role.capitalize()
        user_id = request.user.id
        return Response({'role': role, 'username': request.user.username, 'user_id': user_id})
    
class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        # print(request.data)
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True)  # partial=True allows updating some fields only

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        if not serializer.is_valid():
            print("Validation errors:", serializer.errors)  # This will help pinpoint the exact field(s) causing issues.
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    
class RequestOTPView(APIView):
    """
    View to request an OTP for password reset.
    """
    permission_classes = [AllowAny]
    def post(self, request):
        phone_number = request.data.get('phone_number')
        try:
            user = User.objects.get(phone_number=phone_number)
            user.generate_otp()  # Generate OTP
            user.send_otp_email()  # Send OTP to email
            return Response({"message": "OTP sent to your email."}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response({"error": "No user found with this email."}, status=status.HTTP_404_NOT_FOUND)
        
        
class VerifyOTPView(APIView):
    """
    View to verify the OTP and reset the password.
    """
    permission_classes = [AllowAny]
    def post(self, request):
        phone_number = request.data.get('phone_number')
        otp = request.data.get('otp')
        new_password = request.data.get('new_password')
        
        try:
            user = User.objects.get(phone_number=phone_number)

            if user.otp_is_valid() and user.otp == otp:
                # Reset password
                user.set_password(new_password)
                user.otp = None  # Invalidate OTP after use
                user.otp_created_at = None
                user.save()

                return Response({"message": "Password reset successfully."}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)

        except ObjectDoesNotExist:
            return Response({"error": "Phone number does not exist."}, status=status.HTTP_404_NOT_FOUND)



class Validate_token(APIView):
    authentication_classes = [JWTAuthentication]  # JWT authentication
    permission_classes = [IsAuthenticated]  # User must be authenticated

    def get(self, request):
        # print("hello")
        return Response({
            'message': 'Access granted. You are authenticated!',
            'user': request.user.username
        }, status=status.HTTP_200_OK)
        
        
        
class DashboardStatisticsView(APIView):
    permission_classes = [IsAuthenticated]  # Ensures only authenticated users can access this view

    def get(self, request, *args, **kwargs):
        User = get_user_model()

        # Count the number of questions
        question_count = Question.objects.count()
        
        # Count the number of users with the role "student"
        student_count = User.objects.filter(role='student').count()
        
        # Count the number of users using non-free packages
        # package_user_count = User.objects.filter(
        #     subscription_package__name__in=['basic', 'standard', 'premium']
        # ).distinct().count()

        # Prepare the response data
        data = {
            'question_count': question_count,
            'student_count': student_count,
            # 'package_user_count': package_user_count,
        }
        
        return Response(data)







class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        User = get_user_model()

        # Count total students
        total_students = User.objects.filter(role='student').count()

        # Count total package users (non-free users)
        # total_package_users = UserSubscription.objects.filter(
        #     package__name__in=['basic', 'standard', 'premium'],
        #     status='active'
        # ).count()

        # Count total questions
        total_questions = Question.objects.count()

        # Date range (e.g., last 7 days)
        today = now().date()
        last_week = today - timedelta(days=6)
        dates = [last_week + timedelta(days=i) for i in range(7)]

        # Questions published by date
        question_counts = (
            Question.objects.annotate(created_date=Cast('created_at', output_field=CharField()))
            .filter(created_date__range=(last_week, today))
            .values('created_date')
            .annotate(count=Count('id'))
        )
        question_data = {q['created_date']: q['count'] for q in question_counts}

        # Users by date
        user_counts = (
            User.objects.annotate(joined_date=Cast('date_joined', output_field=CharField()))
            .filter(joined_date__range=(last_week, today))
            .values('joined_date')
            .annotate(count=Count('id'))
        )
        user_data = {u['joined_date']: u['count'] for u in user_counts}

        # Package users by date
        package_user_counts = (
            User.objects.filter(
                usersubscription__package__name__in=["basic", "standard", "premium"],
                usersubscription__status='active',
            )
            .annotate(joined_date=Cast('date_joined', output_field=CharField()))
            .filter(joined_date__range=(last_week, today))
            .values('joined_date')
            .annotate(count=Count('id'))
        )
        package_user_data = {u['joined_date']: u['count'] for u in package_user_counts}

        # Align counts with dates
        def get_date_counts(data):
            return [data.get(date, 0) for date in dates]

        response_data = {
            "summary": {
                "total_students": total_students,
                # "total_package_users": total_package_users,
                "total_questions": total_questions,
            },
            "chart_data": {
                "labels": [date.strftime("%Y-%m-%d") for date in dates],
                "datasets": [
                    {
                        "label": "Questions Published",
                        "data": get_date_counts(question_data),
                        "backgroundColor": "#FF6384",
                    },
                    {
                        "label": "Users Joined",
                        "data": get_date_counts(user_data),
                        "backgroundColor": "#36A2EB",
                    },
                    {
                        "label": "Package Users Joined",
                        "data": get_date_counts(package_user_data),
                        "backgroundColor": "#FFCE56",
                    },
                ],
            },
        }

        return Response(response_data)
    
    
    
    
    
class TempUserCreateView(APIView):
    def post(self, request):
        serializer = TempUserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            return Response({
                'user_id': user.id,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'message': 'User created or reused'
            }, status=201)
        
        return Response(serializer.errors, status=400)