import smtplib

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import loader


@shared_task(
    acks_late=True,
    autoretry_for=(smtplib.SMTPException, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def send_email(
    *,
    recipient,
    subject,
    text_template,
    html_template,
    context,
):
    text_content = loader.render_to_string(text_template, context)
    html_content = loader.render_to_string(html_template, context)

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )

    message.attach_alternative(html_content, "text/html")
    message.send(fail_silently=False)
