from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from .models import OTP

User = get_user_model()

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "email",
        "get_full_name",
        "phone_number",
        "account_status",
        "is_driver",
        "rating_as_driver",
        "date_joined",
    )
    
    list_filter = (
        "is_active",
        "is_staff",
        "is_driver",
        "current_role",
    )
    
    search_fields = (
        "email",
        "first_name",
        "last_name",
        "phone_number",
    )
    
    ordering = ("-date_joined",)
    
    actions = ['verify_users', 'verify_drivers']
    
    fieldsets = (
        (None, {
            "fields": ("email", "password")
        }),
        ("Personal info", {
            "fields": (
                "first_name",
                "last_name",
                "phone_number",
                "profile_photo",
            )
        }),
        ("Status", {
            "fields": (
                "is_active",
                "email_verified",
                "phone_verified",
                "is_driver",
                "current_role",
            )
        }),
        ("Vehicle Info", {
            "fields": (
                "vehicle_number",
                "vehicle_model",
                "total_seats",
                "drivers_license_image",
            )
        }),
        ("Permissions", {
            "fields": (
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
    )
    
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email",
                "password1",
                "password2",
                "first_name",
                "last_name",
                "phone_number",
                "is_active",
            ),
        }),
    )

    def get_full_name(self, obj):
        return obj.get_full_name() or "-"
    get_full_name.short_description = "Full Name"
    
    def account_status(self, obj):
        if not obj.is_active:
            return format_html('<span style="color: red;">Inactive</span>')
        return format_html('<span style="color: green;">Active</span>')
    account_status.short_description = "Status"
    
    def verify_users(self, request, queryset):
        updated = queryset.update(
            is_active=True,
            email_verified=True,
            phone_verified=True,
            registration_pending=False
        )
        self.message_user(request, f"{updated} users were verified.")
    verify_users.short_description = "Verify selected users"
    
    def verify_drivers(self, request, queryset):
        updated = queryset.update(is_driver=True, is_driver_verified=True)
        self.message_user(request, f"{updated} users were verified as drivers.")
    verify_drivers.short_description = "Verify selected users as drivers"


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "code",
        "type",
        "is_verified",
        "attempts",
        "created_at",
    )
    
    list_filter = (
        "type",
        "is_verified",
        "created_at",
    )
    
    search_fields = (
        "user__email",
        "user__phone_number",
        "code",
    )
    
    readonly_fields = (
        "code",
        "created_at",
        "attempts",
    )
    
    ordering = ("-created_at",)