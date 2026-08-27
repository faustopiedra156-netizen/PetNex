"""Django email backend backed by Brevo's HTTPS transactional API."""

import base64
import html
import logging
from email.utils import parseaddr

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class BrevoEmailBackend(BaseEmailBackend):
    """Send Django EmailMessage instances through Brevo without SMTP."""

    def _get_configuration(self):
        api_key = settings.BREVO_API_KEY
        sender_email = settings.BREVO_SENDER_EMAIL
        sender_name = settings.BREVO_SENDER_NAME
        timeout = max(int(settings.BREVO_TIMEOUT_SECONDS), 1)
        return api_key, sender_email, sender_name, timeout

    def _handle_error(self, error):
        logger.warning(
            'No se pudo enviar un correo mediante Brevo (%s).',
            type(error).__name__,
        )
        if not self._fail_silently:
            raise error
        return 0

    @staticmethod
    def _recipient(value, recipient_class):
        name, email = parseaddr(value)
        return recipient_class(email=email or value, name=name or None)

    @staticmethod
    def _html_content(message):
        for alternative in getattr(message, 'alternatives', []):
            content, mimetype = alternative
            if mimetype.lower() == 'text/html':
                return content
        return '<html><body><p>%s</p></body></html>' % html.escape(message.body).replace('\n', '<br>')

    @staticmethod
    def _attachments(message, attachment_class):
        attachments = []
        for attachment in getattr(message, 'attachments', []):
            if not isinstance(attachment, tuple) or len(attachment) < 2:
                logger.warning('Se omitio un adjunto no compatible con Brevo.')
                continue
            filename, content = attachment[:2]
            if isinstance(content, str):
                content = content.encode('utf-8')
            attachments.append(
                attachment_class(
                    name=str(filename),
                    content=base64.b64encode(content).decode('ascii'),
                )
            )
        return attachments or None

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        api_key, sender_email, sender_name, timeout = self._get_configuration()
        if not api_key:
            return self._handle_error(RuntimeError('BREVO_API_KEY no esta configurada.'))
        if not sender_email:
            return self._handle_error(RuntimeError('BREVO_SENDER_EMAIL no esta configurada.'))

        try:
            from brevo import Brevo
            from brevo.transactional_emails import (
                SendTransacEmailRequestAttachmentItem,
                SendTransacEmailRequestBccItem,
                SendTransacEmailRequestCcItem,
                SendTransacEmailRequestReplyTo,
                SendTransacEmailRequestSender,
                SendTransacEmailRequestToItem,
            )
        except ImportError as error:
            return self._handle_error(error)

        try:
            client = Brevo(api_key=api_key, timeout=float(timeout))
        except Exception as error:
            return self._handle_error(error)
        sent = 0
        for message in email_messages:
            recipients = [
                self._recipient(value, SendTransacEmailRequestToItem)
                for value in message.to
                if value
            ]
            if not recipients:
                continue

            sender_name_from_header, _ = parseaddr(message.from_email)
            sender = SendTransacEmailRequestSender(
                email=sender_email,
                name=sender_name or sender_name_from_header or None,
            )
            payload = {
                'subject': str(message.subject),
                'text_content': message.body,
                'html_content': self._html_content(message),
                'sender': sender,
                'to': recipients,
                'request_options': {
                    'timeout_in_seconds': timeout,
                    'max_retries': 1,
                },
            }

            if message.cc:
                payload['cc'] = [
                    self._recipient(value, SendTransacEmailRequestCcItem)
                    for value in message.cc
                    if value
                ]
            if message.bcc:
                payload['bcc'] = [
                    self._recipient(value, SendTransacEmailRequestBccItem)
                    for value in message.bcc
                    if value
                ]
            if message.reply_to:
                reply_name, reply_email = parseaddr(message.reply_to[0])
                if reply_email:
                    payload['reply_to'] = SendTransacEmailRequestReplyTo(
                        email=reply_email,
                        name=reply_name or None,
                    )
            attachments = self._attachments(
                message,
                SendTransacEmailRequestAttachmentItem,
            )
            if attachments:
                payload['attachment'] = attachments

            try:
                client.transactional_emails.send_transac_email(**payload)
                sent += 1
            except Exception as error:
                return self._handle_error(error)

        return sent


# Compatibility for deployments that still have the previous backend path in
# EMAIL_BACKEND. The implementation and credentials are now consistently
# managed through the Brevo settings above.
ResendEmailBackend = BrevoEmailBackend
