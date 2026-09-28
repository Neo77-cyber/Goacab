"""Sends admin-facing alert emails (disputes, new-driver signups, stale
rides) through Resend's SMTP relay, deliberately separate from Django's
global EMAIL_BACKEND — that default stays on the console backend because
OTP login/signup codes go through it (otp.py), and those can never be put
at risk of a real provider silently rejecting a recipient (e.g. Resend's
sandbox restricting delivery before a domain is verified) and locking
everyone out of logging in. Admin alerts are much lower-stakes if a send
occasionally fails, so they're the only thing that uses Resend directly.

Safe no-op behavior matches every other "unconfigured until you set a key"
integration in this project: no RESEND_API_KEY means these calls just fall
back to Django's default send_mail() (the console backend), so nothing
breaks before Resend is actually wanted.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import get_connection, send_mail

logger = logging.getLogger(__name__)


def send_admin_mail(subject: str, message: str, recipient_list: list[str]) -> None:
    if not recipient_list:
        return

    if not settings.RESEND_API_KEY:
        send_mail(subject=subject, message=message, from_email=None, recipient_list=recipient_list)
        return

    try:
        connection = get_connection(
            backend="django.core.mail.backends.smtp.EmailBackend",
            host=settings.RESEND_SMTP_HOST,
            port=settings.RESEND_SMTP_PORT,
            username="resend",
            password=settings.RESEND_API_KEY,
            use_tls=True,
        )
        send_mail(
            subject=subject, message=message, from_email=settings.RESEND_FROM_EMAIL,
            recipient_list=recipient_list, connection=connection,
        )
    except Exception:
        logger.exception("send_admin_mail via Resend failed — subject=%r", subject)
