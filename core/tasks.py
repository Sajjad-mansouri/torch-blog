import logging
import smtplib

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _render(template_name, kwargs):
    text_content = render_to_string(f"core/email/{template_name}.txt", kwargs)
    html_content = render_to_string(f"core/email/{template_name}.html", kwargs)

    return text_content, html_content


@shared_task(
    acks_late=True,
    autoretry_for=(smtplib.SMTPException, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def send_email_task(**kwargs):
    CONTACT_EMAIL = getattr(settings, "CONTACT_EMAIL", None)
    if CONTACT_EMAIL:
        text_body, html_body = _render("contact_notification", kwargs)
        email = EmailMultiAlternatives(
            subject=f"[Torch] New contact message from {kwargs.get('name')}",
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[CONTACT_EMAIL],
        )

        email.attach_alternative(html_body, "text/html")
        email.send(fail_silently=False)

    text_body, html_body = _render("contact_autoreply", kwargs)
    recipient = kwargs["email"]
    email = EmailMultiAlternatives(
        subject="Your message has been received",
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )

    email.attach_alternative(html_body, "text/html")
    email.send(fail_silently=False)
