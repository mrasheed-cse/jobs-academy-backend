from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('id', 'phone_number', 'username', 'email', 'role', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_active', 'role')
    fieldsets = (
        (None, {'fields': ('phone_number', 'username', 'password')}),
        ('Personal info', {'fields': ('email', 'address', 'other_information', 'profile_picture', 'date_of_birth', 'gender', 'secondary_phone_number', 'bio', 'facebook_profile', 'twitter_profile', 'linkedin_profile', 'preferences')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'role')}),
        ('Important dates', {'fields': ( 'last_login', )}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'username', 'email', 'password1', 'password2', 'role', 'is_staff', 'is_active')
        }),
        ('Additional info', {
            'classes': ('wide',),
            'fields': ('profile_picture', 'address', 'other_information', 'profile_picture', 'date_of_birth', 'gender', 'secondary_phone_number', 'bio', 'facebook_profile', 'twitter_profile', 'linkedin_profile', 'preferences'),
        }),
    )
    search_fields = ('phone_number', 'username', 'email')
    ordering = ('phone_number',)
    filter_horizontal = ()

admin.site.register(CustomUser, CustomUserAdmin)
