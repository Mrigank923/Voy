from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

User = get_user_model()

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "email_verified",
        "phone_verified",
        "registration_pending",
        "date_joined",
    )
    
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    
    actions = ['verify_users']
    
    def verify_users(self, request, queryset):
        queryset.update(
            is_active=True,
            email_verified=True,
            phone_verified=True,
            registration_pending=False
        )
    verify_users.short_description = "Verify selected users"

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "is_active",
                    "email_verified",
                    "phone_verified",
                    "registration_pending",
                ),
            },
        ),
    )

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        ("Verification status", {
            "fields": (
                "is_active",
                "email_verified",
                "phone_verified",
                "registration_pending",
            )
        }),
        (
            "Permissions",
            {
                "fields": (
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )