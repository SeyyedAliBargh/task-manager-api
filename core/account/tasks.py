from .models import User
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


@shared_task
def send_registration_email(token, full_name, email):
    """
    Celery task to send a registration/activation email.

    Args:
        token (str): Unique activation token for the user.
        full_name (str): Full name of the user (used in the email template).
        email (str): Recipient's email address.

    Process:
        - Render HTML content using the 'registration_email.html' template.
        - Attach both plain text and HTML versions to the email.
        - Send the email to the provided address.
    """
    # Render HTML email content with token and full name
    html_content = render_to_string(
        "account/registration_email.html",
        {
            "token": token,
            "full_name": full_name,
        }
    )

    # Fallback plain text content
    text_content = "This is a Registration Email"

    # Create email object with subject, sender, and recipient
    email_obj = EmailMultiAlternatives(
        "Activation Email",
        text_content,
        settings.DEFAULT_FROM_EMAIL,
        [email],
    )

    # Attach HTML alternative
    email_obj.attach_alternative(html_content, "text/html")

    # Send the email
    email_obj.send()


@shared_task
def send_change_email(code, new_email):
    """
    Celery task to send an email change verification code.

    Args:
        code (str): Verification code generated for email change.
        new_email (str): The new email address to verify.

    Process:
        - Render HTML content using the 'change_email.html' template.
        - Attach both plain text and HTML versions to the email.
        - Send the email to the new address.
    """
    # Render HTML email content with verification code
    html_content = render_to_string(
        "account/change_email.html",
        {
            "code": code,
        }
    )

    # Fallback plain text content
    text_content = "This is a Change Email Request"

    # Create email object with subject, sender, and recipient
    email_obj = EmailMultiAlternatives(
        "Change Email",
        text_content,
        settings.DEFAULT_FROM_EMAIL,
        [new_email],
    )

    # Attach HTML alternative
    email_obj.attach_alternative(html_content, "text/html")

    # Send the email
    email_obj.send()


@shared_task
def delete_unverified_users():
    """
    Celery task to delete unverified users older than 1 day.

    Process:
        - Calculate cutoff time (current time minus 1 day).
        - Find all users who are not verified and created before cutoff.
        - Delete those users from the database.
    """
    # Calculate cutoff time (1 day ago)
    cutoff = timezone.now() - timedelta(days=1)

    # Query unverified users older than cutoff
    users = User.objects.filter(is_verified=False, created_at__lt=cutoff)

    # Delete each unverified user
    for user in users:
        user.delete()