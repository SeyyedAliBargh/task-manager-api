from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Profile


@receiver(post_save, sender=User)
def save_profile(sender, instance, created, **kwargs):
    """
    Signal handler to automatically create a Profile instance
    whenever a new User instance is created.
    """

    if created:
        # Create a profile linked to the newly created user
        Profile.objects.create(user=instance)
