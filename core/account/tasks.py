from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from datetime import timedelta
from django.utils import timezone
from .models import User

@shared_task
def send_registration_email(token, full_name, email):
    html_content = render_to_string(
        "account/registration_email.html",
        {
            "token": token,
            "full_name": full_name,
        }
    )
    text_content = "This is a Registration Email"

    email_obj = EmailMultiAlternatives(
        "Activation Email",
        text_content,
        settings.DEFAULT_FROM_EMAIL,
        [email],
    )
    email_obj.attach_alternative(html_content, "text/html")
    email_obj.send()


@shared_task
def delete_unverified_users():
    cutoff = timezone.now() - timedelta(days=1)
    users = User.objects.filter(is_verified=False, created_at__lt=cutoff)
    for user in users:
        user.delete()