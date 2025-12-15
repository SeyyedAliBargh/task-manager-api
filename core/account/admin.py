from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Profile


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Admin configuration for the custom User model.
    """

    # Columns displayed in the user list view
    list_display = ("email", "is_superuser", "is_active")

    # Fields used for searching users in the admin panel
    search_fields = ("email",)

    # Default ordering for the user list view
    ordering = ("email",)

    # Field layout for the change (edit) user form
    fieldsets = (
        (
            "Authentication",
            {
                "classes": ("wide",),
                "fields": ("email", "password"),
            },
        ),
        (
            "Permissions",
            {
                "classes": ("wide",),
                "fields": (
                    "is_staff",
                    "is_active",
                    "is_superuser",
                    "is_verified",
                ),
            },
        ),
        (
            "Group permissions",
            {
                "classes": ("wide",),
                "fields": ("groups", "user_permissions"),
            },
        ),
        (
            "Important dates",
            {
                "classes": ("wide",),
                "fields": ("last_login",),
            },
        ),
    )

    # Field layout for the add (create) user form
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "is_superuser",
                    "is_active",
                    "is_staff",
                    "is_verified",
                ),
            },
        ),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Profile model.
    """

    class Meta:
        model = Profile
