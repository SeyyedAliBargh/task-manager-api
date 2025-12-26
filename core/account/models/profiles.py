from django.db import models
from django.utils.translation import gettext_lazy as _
from .users import User


class Profile(models.Model):
    """
    Profile model linked to the custom User model via OneToOne relationship.
    Stores additional user information such as name, image, and description.
    """

    # One-to-one relationship with the custom User model
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        help_text="The user associated with this profile.",
    )

    # Personal information fields
    first_name = models.CharField(
        _("first name"), max_length=50, help_text="The user's first name."
    )
    last_name = models.CharField(
        _("last name"), max_length=50, help_text="The user's last name."
    )
    image = models.ImageField(
        blank=True, null=True, help_text="Profile image of the user (optional)."
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Additional information or bio of the user (optional).",
    )

    # Timestamp fields
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="The date and time when the profile was created."
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="The date and time when the profile was last updated."
    )

    def __str__(self):
        """
        Return the string representation of the profile,
        which is the email of the related user.
        """
        return self.user.email

    def get_full_name(self):
        return self.first_name + " " + self.last_name
