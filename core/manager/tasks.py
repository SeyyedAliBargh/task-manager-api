from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


@shared_task
def send_registration_email(token, full_name, email):
    """
    Celery task to send a project invitation email.

    - Renders an HTML email template with the provided token and full name.
    - Includes a plain text fallback message.
    - Sends the email using Django's `EmailMultiAlternatives`.
    """

    # Render HTML content from template with token and full name
    html_content = render_to_string(
        "manager/invition_email.html",
        {
            "token": token,
            "full_name": full_name,
        }
    )

    # Plain text fallback content
    text_content = "This is an Invitation Email"

    # Create email object with subject, text, sender, and recipient
    email_obj = EmailMultiAlternatives(
        "Invitation Email",  # Subject
        text_content,  # Plain text content
        settings.DEFAULT_FROM_EMAIL,  # Sender email
        [email],  # Recipient list
    )

    # Attach HTML version of the email
    email_obj.attach_alternative(html_content, "text/html")

    # Send the email
    email_obj.send()