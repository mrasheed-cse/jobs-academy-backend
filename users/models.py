from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.mail import send_mail  # Optional if you want to send emails
import random
from datetime import timedelta
from django.utils import timezone
import secrets
from django.core.validators import MinLengthValidator, RegexValidator

class UserManager(BaseUserManager):

    def create_user(self, phone_number, email=None, username=None, password=None, role='student', **extra_fields):
        if not phone_number:
            raise ValueError('The phone number must be set')
        if not email:
            raise ValueError('The email must be required')
        
        if not username:
            raise ValueError('The username must be required')
        
        email = self.normalize_email(email)
        user = self.model(phone_number=phone_number, email=email, username=username, role=role, **extra_fields)
        user.set_password(password)
        # if password:
        #     user.set_password(password)
        # else:
        #     user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, email=None, username=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')  # Default role for superuser

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(phone_number, email, username, password, **extra_fields)
        

class CustomUser(AbstractUser):
    ADMIN = 'admin'
    TEACHER = 'teacher'
    STUDENT = 'student'
    OPERATOR = 'operator'

    ROLE_CHOICES = [
        (ADMIN, 'Admin'),
        (TEACHER, 'Teacher'),
        (STUDENT, 'Student'),
        (OPERATOR, 'Operator'),
    ]

    username = models.CharField(max_length=100, unique=True)
    phone_number = models.CharField(max_length=20, unique=True, validators=[MinLengthValidator(10), RegexValidator(r'^\d+$', 'Only numeric characters are allowed.')])
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=STUDENT)
    email = models.EmailField(unique=True, null=True, blank=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    other_information = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], blank=True, null=True)
    secondary_phone_number = models.CharField(max_length=20, blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    facebook_profile = models.URLField(blank=True, null=True)
    twitter_profile = models.URLField(blank=True, null=True)
    linkedin_profile = models.URLField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    preferences = models.JSONField(blank=True, null=True)
    # created_at = models.DateTimeField(auto_now_add=True)

    
    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)
    
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['username', 'email']

    objects = UserManager()

    def save(self, *args, **kwargs):
        # Automatically set is_staff to True if the role is admin
        if self.role == self.ADMIN:
            self.is_staff = True
        super().save(*args, **kwargs)

    def __str__(self):
        return self.phone_number
    
    
    def generate_otp(self):
        """Generates a 6-digit OTP and stores its creation time"""
        self.otp = str(secrets.randbelow(10**6)).zfill(6)  # 6-digit OTP
        self.otp_created_at = timezone.now()
        self.save()
        
        
    def otp_is_valid(self):
        """Check if the OTP is still valid (valid for 10 minutes)"""
        if not self.otp or not self.otp_created_at:
            return False
        valid_duration = timedelta(minutes=10)  # OTP valid for 10 minutes
        return timezone.now() < (self.otp_created_at + valid_duration)
    
    
    
    
    
    def send_otp_email(self):
        """Sends the OTP to the user's email"""
        if not self.email:
            raise ValueError("User must have a valid email to send OTP")

        subject = 'Your OTP for Password Reset'
        message = f'Your OTP is: {self.otp}'
        from_email = 'jonaetshanto8@gmail.com'  # Replace with your own email
        recipient_list = [self.email]

        send_mail(subject, message, from_email, recipient_list)

    # def email_user(self, subject, message, from_email=None, **kwargs):
    #     """Send an email to this user."""
    #     send_mail(subject, message, from_email, [self.email], **kwargs)
