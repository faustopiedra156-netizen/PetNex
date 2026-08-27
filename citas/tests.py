import re

from django.contrib.auth import authenticate, get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import CodigoRecuperacionContrasena


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
