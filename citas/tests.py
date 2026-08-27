import re
from unittest.mock import MagicMock, patch

from django.contrib.auth import authenticate, get_user_model
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .email_backend import ResendEmailBackend
from .models import CodigoRecuperacionContrasena
from .services import enviar_notificacion


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class RecuperacionConCodigoTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='cliente_prueba',
            email='cliente@example.com',
            password='clave-anterior-segura',
        )

    def test_codigo_permite_cambiar_la_contrasena(self):
        response = self.client.post(
            reverse('password_reset'),
            {'email': self.user.email},
        )
        self.assertRedirects(response, reverse('password_reset_verify'))
        self.assertEqual(len(mail.outbox), 1)

        codigo = re.search(r'\b(\d{6})\b', mail.outbox[0].body).group(1)
        registro = CodigoRecuperacionContrasena.objects.get(usuario=self.user)
        self.assertTrue(registro.esta_vigente)

        response = self.client.post(
            reverse('password_reset_verify'),
            {'codigo': codigo},
        )
        self.assertRedirects(response, reverse('password_reset_confirm'))

        response = self.client.post(
            reverse('password_reset_confirm'),
            {
                'nueva_contrasena': 'nueva-clave-segura',
                'confirmar_contrasena': 'nueva-clave-segura',
            },
        )
        self.assertRedirects(response, reverse('password_reset_complete'))
        self.assertIsNotNone(
            authenticate(username=self.user.username, password='nueva-clave-segura')
        )


class ResendEmailBackendTests(SimpleTestCase):
    @override_settings(
        RESEND_API_KEY='',
        RESEND_SENDER_EMAIL='',
        RESEND_SENDER_NAME='PetNexo',
        RESEND_TIMEOUT_SECONDS=10,
    )
    def test_sin_api_key_no_rompe_si_se_pide_silencio(self):
        message = EmailMultiAlternatives(
            'Prueba',
            'Mensaje de prueba',
            'noreply@example.com',
            ['cliente@example.com'],
        )
        backend = ResendEmailBackend(fail_silently=True)

        self.assertEqual(backend.send_messages([message]), 0)

    @override_settings(
        RESEND_API_KEY='test-key',
        RESEND_SENDER_EMAIL='noreply@example.com',
        RESEND_SENDER_NAME='PetNexo',
        RESEND_TIMEOUT_SECONDS=10,
    )
    @patch('citas.email_backend.import_module')
    def test_envia_texto_y_html_a_resend(self, import_module_mock):
        resend_module = MagicMock()
        import_module_mock.return_value = resend_module
        message = EmailMultiAlternatives(
            'Asunto de prueba',
            'Texto de prueba',
            'noreply@example.com',
            ['cliente@example.com'],
        )
        message.attach_alternative('<p>Texto <strong>HTML</strong></p>', 'text/html')
        backend = ResendEmailBackend()

        self.assertEqual(backend.send_messages([message]), 1)
        resend_module.RequestsClient.assert_called_once_with(timeout=10)
        resend_module.Emails.send.assert_called_once()
        params = resend_module.Emails.send.call_args.args[0]
        self.assertEqual(params['from'], 'PetNexo <noreply@example.com>')
        self.assertEqual(params['to'], ['cliente@example.com'])
        self.assertEqual(params['text'], 'Texto de prueba')
        self.assertEqual(params['html'], '<p>Texto <strong>HTML</strong></p>')

    @override_settings(
        EMAIL_BACKEND='citas.email_backend.ResendEmailBackend',
        RESEND_API_KEY='test-key',
        RESEND_SENDER_EMAIL='noreply@example.com',
        RESEND_SENDER_NAME='PetNexo',
        RESEND_TIMEOUT_SECONDS=10,
    )
    @patch('citas.email_backend.import_module')
    def test_fallo_de_resend_no_rompe_notificacion_y_no_expone_la_clave(
        self,
        import_module_mock,
    ):
        resend_module = MagicMock()
        resend_module.Emails.send.side_effect = RuntimeError('fallo de prueba')
        import_module_mock.return_value = resend_module

        with self.assertLogs('citas.email_backend', level='WARNING') as logs:
            result = enviar_notificacion(
                'Asunto',
                'Mensaje',
                ['cliente@example.com'],
            )

        self.assertEqual(result, 0)
        self.assertNotIn('test-key', '\n'.join(logs.output))
