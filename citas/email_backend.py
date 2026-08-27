"""Django email backend backed by Resend's HTTPS API."""

import html
import logging
from email.utils import parseaddr
from importlib import import_module

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class ResendEmailBackend(BaseEmailBackend):
    """Send Django email messages through Resend without using SMTP."""

    def _get_configuration(self):
        api_key = settings.RESEND_API_KEY
        sender_email = settings.RESEND_SENDER_EMAIL
        sender_name = settings.RESEND_SENDER_NAME
        timeout = max(int(settings.RESEND_TIMEOUT_SECONDS), 1)
        return api_key, sender_email, sender_name, timeout

    def _handle_error(self, error):
        # Do not include exception text because third-party errors can contain
        # request details. The exception class is enough for diagnostics.
        logger.warning(
            'No se pudo enviar un correo mediante Resend (%s).',
            type(error).__name__,
        )
        if not self._fail_silently:
            raise error
        return 0

    @staticmethod
    def _address(value):
        name, email = parseaddr(value)
        return f'{name} <{email}>' if name and email else (email or value)

    @staticmethod
    def _html_content(message):
        for alternative in getattr(message, 'alternatives', []):
            content, mimetype = alternative[:2]
            if mimetype.lower() == 'text/html':
                return content
        body = html.escape(message.body or '').replace('\n', '<br>')
        return f'<html><body><p>{body}</p></body></html>'

    @staticmethod
    def _attachments(message):
        attachments = []
        for attachment in getattr(message, 'attachments', []):
            if not isinstance(attachment, tuple) or len(attachment) < 2:
                logger.warning('Se omitio un adjunto no compatible con Resend.')
                continue

            filename, content = attachment[:2]
            item = {
                'filename': str(filename),
                'content': (
                    list(content)
                    if isinstance(content, (bytes, bytearray))
                    else str(content)
                ),
            }
            if len(attachment) >= 3 and attachment[2]:
                item['content_type'] = str(attachment[2])
            attachments.append(item)
        return attachments

    def _resend_module(self, api_key, timeout):
        resend = import_module('resend')
        resend.api_key = api_key
        resend.default_http_client = resend.RequestsClient(timeout=timeout)
        return resend

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        api_key, sender_email, sender_name, timeout = self._get_configuration()
        if not api_key:
            return self._handle_error(RuntimeError('RESEND_API_KEY no esta configurada.'))
        if not sender_email:
            return self._handle_error(RuntimeError('RESEND_SENDER_EMAIL no esta configurada.'))

        try:
            resend = self._resend_module(api_key, timeout)
        except Exception as error:
            return self._handle_error(error)

        sent = 0
        from_header_name, _ = parseaddr(sender_email)
        sender = (
            f'{sender_name or from_header_name} <{sender_email}>'
            if (sender_name or from_header_name)
            else sender_email
        )

        for message in email_messages:
            recipients = [self._address(value) for value in message.to if value]
            if not recipients:
                continue

            params = {
                'from': sender,
                'to': recipients,
                'subject': str(message.subject),
                'text': message.body or '',
                'html': self._html_content(message),
            }
            if message.cc:
                params['cc'] = [self._address(value) for value in message.cc if value]
            if message.bcc:
                params['bcc'] = [self._address(value) for value in message.bcc if value]
            if message.reply_to:
                params['reply_to'] = [
                    self._address(value) for value in message.reply_to if value
                ]
            attachments = self._attachments(message)
            if attachments:
                params['attachments'] = attachments

            try:
                resend.Emails.send(params)
                sent += 1
            except Exception as error:
                if not self._fail_silently:
                    return self._handle_error(error)
                self._handle_error(error)

        return sent
