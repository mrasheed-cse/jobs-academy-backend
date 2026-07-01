from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
User = get_user_model()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    phone_number = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        password = attrs.get('password')

        if phone_number and password:
            user = authenticate(request=self.context.get('request'), phone_number=phone_number, password=password)
            if not user:
                raise serializers.ValidationError('Invalid phone number or password.')

            attrs['user'] = user
            
            data = super().validate(attrs)
            attrs['user_id'] = self.user.id
            attrs['username'] = self.user.username
            attrs['role'] = self.user.role
            return attrs
        else:
            raise serializers.ValidationError('Must include "phone_number" and "password".')


# class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
#     phone_number = serializers.CharField()
#     password = serializers.CharField()
#     device_id = serializers.CharField(write_only=True, required=True)

#     def validate(self, attrs):
#         phone_number = attrs.get('phone_number')
#         password = attrs.get('password')
#         device_id = attrs.get('device_id')
#         request = self.context.get('request')

#         if not (phone_number and password):
#             raise serializers.ValidationError('Must include "phone_number" and "password".')

#         user = authenticate(request=request, phone_number=phone_number, password=password)
#         if not user:
#             raise serializers.ValidationError('Invalid phone number or password.')

#         # Check or register device
#         user_agent = request.META.get('HTTP_USER_AGENT', '')
#         ip_address = request.META.get('REMOTE_ADDR', '')

#         devices = UserDevice.objects.filter(user=user)

#         if not devices.filter(device_id=device_id).exists():
#             if devices.count() >= 2:
#                 raise serializers.ValidationError("Device limit reached. You can only use 2 devices.")
#             # Add new device
#             UserDevice.objects.create(
#                 user=user,
#                 device_id=device_id,
#                 user_agent=user_agent,
#                 ip_address=ip_address
#             )
#         else:
#             # Update last_used timestamp
#             device = devices.get(device_id=device_id)
#             device.last_used = now()
#             device.save()

#         # Pass validated user to the parent class
#         self.user = user
#         data = super().validate(attrs)

#         # Add custom fields to the response
#         data['user_id'] = user.id
#         data['username'] = user.username
#         data['role'] = user.role
#         return data

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, required=False)
    email = serializers.EmailField(required=True)
    address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    other_information = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], required=False, allow_blank=True)
    secondary_phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    facebook_profile = serializers.URLField(required=False, allow_blank=True)
    twitter_profile = serializers.URLField(required=False, allow_blank=True)
    linkedin_profile = serializers.URLField(required=False, allow_blank=True)
    bio = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    preferences = serializers.JSONField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'phone_number', 'password', 'role', 'email', 'address',
            'other_information', 'profile_picture', 'date_of_birth', 'gender',
            'secondary_phone_number', 'facebook_profile', 'twitter_profile',
            'linkedin_profile', 'bio', 'preferences'
        )
        extra_kwargs = {'password': {'write_only': True}}
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise ValidationError("A user with this email already exists. Please try another email.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            phone_number=validated_data['phone_number'],
            email=validated_data['email'],
            password=validated_data['password'],
            username=validated_data.get('username', ''),  # Username is optional
            role=validated_data.get('role', User.STUDENT),  # Default to 'student' if no role is provided
            address=validated_data.get('address', ''),
            other_information=validated_data.get('other_information', ''),
            profile_picture=validated_data.get('profile_picture'),
            date_of_birth=validated_data.get('date_of_birth'),
            gender=validated_data.get('gender'),
            secondary_phone_number=validated_data.get('secondary_phone_number', ''),
            facebook_profile=validated_data.get('facebook_profile', ''),
            twitter_profile=validated_data.get('twitter_profile', ''),
            linkedin_profile=validated_data.get('linkedin_profile', ''),
            bio=validated_data.get('bio', ''),
            preferences=validated_data.get('preferences', {})
        )
        return user

    def update(self, instance, validated_data):
        # Update user instance with new data
        instance.address = validated_data.get('address', instance.address)
        instance.other_information = validated_data.get('other_information', instance.other_information)

        # Handle file upload for profile picture
        if 'profile_picture' in validated_data:
            instance.profile_picture = validated_data['profile_picture']
        
        instance.date_of_birth = validated_data.get('date_of_birth', instance.date_of_birth)
        instance.gender = validated_data.get('gender', instance.gender)
        instance.secondary_phone_number = validated_data.get('secondary_phone_number', instance.secondary_phone_number)
        instance.facebook_profile = validated_data.get('facebook_profile', instance.facebook_profile)
        instance.twitter_profile = validated_data.get('twitter_profile', instance.twitter_profile)
        instance.linkedin_profile = validated_data.get('linkedin_profile', instance.linkedin_profile)
        instance.bio = validated_data.get('bio', instance.bio)
        instance.preferences = validated_data.get('preferences', instance.preferences)
        
        # Update fields that are editable
        instance.username = validated_data.get('username', instance.username)
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.email = validated_data.get('email', instance.email)
        instance.role = validated_data.get('role', instance.role)
        
        # Update password if provided
        if 'password' in validated_data:
            instance.set_password(validated_data['password'])
        
        instance.save()
        return instance



class RequestOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)





class TempUserCreateSerializer(serializers.Serializer):
    username = serializers.CharField()
    phone_number = serializers.CharField()

    def create(self, validated_data):
        phone = validated_data['phone_number']
        username = validated_data['username']
        
        user, created = User.objects.get_or_create(
            phone_number=phone,
            defaults={
                'username': username,
                'is_active': False
            }
        )
        return user