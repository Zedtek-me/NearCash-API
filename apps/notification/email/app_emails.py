from typing import List, Optional

from celery import shared_task

from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings

from dtos.generics import EmailArgsDto

from utils.helpers.logs import logger


class EmailService:

    def __init__(self, *args, **kwargs):...


    def construct_message(
        self, subject: str, body: str, recipients: list,
        context: dict | None = None, attachments: list | None = None
    ) -> EmailMessage:
        """Constructs an email message."""
        body = self._parse_msg_body(body, context=context)
        email = EmailMessage(
            from_email=settings.DEFAULT_FROM_EMAIL,
            subject=subject,
            body=body,
            to=recipients
        )
        if attachments:
            self._update_email(email, attachments=attachments)
        return email


    @shared_task(bind=True, name="send.email")
    def send_email(self, **kwargs: EmailArgsDto) -> None:
        mail = self.construct_message(**kwargs)
        status_int = mail.send(False)
        logger.debug(f"email result status int... {status_int}")

    def _parse_msg_body(
        self, body: str, **kwargs
    ) -> str:
        """Parses the message body with given kwargs."""

        context = kwargs.get("context", {})
        raw = kwargs.get("raw", False)
        if not raw:
            body = render_to_string(body, context)
        return body


    def _update_email(
        self, email: EmailMessage, attachments: List[dict] | None = None
    ) -> EmailMessage:
        """Updates the email with attachments."""
        if attachments:
            for attachment in attachments:
                email.attach(
                    filename=attachment.get("filename"),
                    content=attachment.get("content"),
                    mimetype=attachment.get("mimetype")
                )
        return email
