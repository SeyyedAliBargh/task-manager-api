from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """
    Custom user manager where email is the unique identifier
    instead of username.
    """

    def create_user(self, email, password=None, **extra_fields):
        """
        Create and return a regular user with an email and password.
        """
        if not email:
            raise ValueError(_("Users must have an email address"))

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and return a superuser with elevated permissions.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model that uses email as the primary identifier
    instead of username.
    """

    email = models.EmailField(max_length=250, unique=True)

    is_staff = models.BooleanField(
        default=False,
        help_text="Designates whether the user can access the admin site.",
    )
    is_superuser = models.BooleanField(
        default=False,
        help_text="Designates that this user has all permissions.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Designates whether this user should be treated as active.",
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Indicates whether the user's email address has been verified.",
    )

    created_date = models.DateTimeField(
        auto_now_add=True,
        help_text="The date and time when the user was created.",
    )
    updated_date = models.DateTimeField(
        auto_now=True,
        help_text="The date and time when the user was last updated.",
    )

    # Authentication settings
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        """
        Return the string representation of the user.
        """
        return self.email


class EmailChangeRequestModel(models.Model):
    """
    Model to store pending email change requests.

    Purpose:
        - Keeps track of a user's request to change their email address.
        - Stores the new email, verification code (OTP), and status.
        - Used in a two-step verification process:
            1. User requests email change → code is generated and sent.
            2. User confirms code → email is updated if valid and not expired.

    Fields:
        user (ForeignKey): Reference to the user requesting the email change.
        new_email (EmailField): The new email address to be verified.
        code (CharField): 6-digit OTP code sent to the new email.
        created_at (DateTimeField): Timestamp when the request was created.
        is_verified (BooleanField): Flag indicating whether the request has been confirmed.
    """

    # Link to the user who requested the email change
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # The new email address that needs to be verified
    new_email = models.EmailField()

    # One-time password (OTP) code for verification
    code = models.CharField(max_length=6)

    # Timestamp when the request was created (auto set)
    created_at = models.DateTimeField(auto_now_add=True)

    # Whether the request has been verified successfully
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        """
        String representation of the model.
        Shows the user and the new email for easier debugging.
        """
        return f"{self.user.email} → {self.new_email} (verified: {self.is_verified})"

class PasswordResetRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)  # OTP code
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} - verified: {self.is_verified}"
