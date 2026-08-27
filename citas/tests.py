import datetime
import re
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import authenticate, get_user_model
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .email_backend import BrevoEmailBackend
from .models import (
    Cita,
    CodigoRecuperacionContrasena,
    Mascota,
    Negocio,
    PlanSuscripcion,
    Servicio,
    Sucursal,
    SuscripcionNegocio,
)
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


class BrevoEmailBackendTests(SimpleTestCase):
    @override_settings(
        BREVO_API_KEY='',
        BREVO_SENDER_EMAIL='',
        BREVO_SENDER_NAME='PetNexo',
        BREVO_TIMEOUT_SECONDS=10,
    )
    def test_sin_api_key_no_rompe_si_se_pide_silencio(self):
        message = EmailMultiAlternatives(
            'Prueba',
            'Mensaje de prueba',
            'noreply@example.com',
            ['cliente@example.com'],
        )
        backend = BrevoEmailBackend(fail_silently=True)

        self.assertEqual(backend.send_messages([message]), 0)

    @override_settings(
        BREVO_API_KEY='test-key',
        BREVO_SENDER_EMAIL='noreply@example.com',
        BREVO_SENDER_NAME='PetNexo',
        BREVO_TIMEOUT_SECONDS=10,
    )
    @patch('brevo.Brevo')
    def test_envia_texto_y_html_a_brevo(self, brevo_client):
        message = EmailMultiAlternatives(
            'Asunto de prueba',
            'Texto de prueba',
            'noreply@example.com',
            ['cliente@example.com'],
        )
        message.attach_alternative('<p>Texto <strong>HTML</strong></p>', 'text/html')
        backend = BrevoEmailBackend()

        self.assertEqual(backend.send_messages([message]), 1)
        brevo_client.assert_called_once_with(api_key='test-key', timeout=10.0)
        brevo_client.return_value.transactional_emails.send_transac_email.assert_called_once()

    @patch('citas.services.send_mail', side_effect=AttributeError('configuracion antigua'))
    def test_falla_del_correo_no_interrumpe_el_flujo(self, send_mail):
        self.assertFalse(
            enviar_notificacion(
                'Nueva cita',
                'Mensaje de prueba',
                ['cliente@example.com'],
            )
        )
        send_mail.assert_called_once()


@override_settings(SIMULATE_PAYMENTS=True)
class PagoSimuladoTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='cliente_pago',
            email='cliente-pago@example.com',
            password='clave-segura-para-pruebas',
        )
        self.other_user = get_user_model().objects.create_user(
            username='otro_cliente',
            email='otro-cliente@example.com',
            password='clave-segura-para-pruebas',
        )
        self.negocio = Negocio.objects.create(
            nombre='Local de pruebas',
            propietario=self.user,
        )
        self.plan = PlanSuscripcion.objects.create(
            nombre='Plan sin pagos para pruebas',
            precio_mensual=Decimal('0.00'),
            permite_pagos=False,
        )
        SuscripcionNegocio.objects.create(
            negocio=self.negocio,
            plan=self.plan,
            estado='ACTIVA',
            fecha_vencimiento=datetime.date.today() + datetime.timedelta(days=30),
        )
        self.sucursal = Sucursal.objects.create(
            negocio=self.negocio,
            nombre='Sucursal principal',
            ciudad='Loja',
            direccion='Direccion de pruebas',
        )
        self.servicio = Servicio.objects.create(
            negocio=self.negocio,
            nombre='Bano de prueba',
            descripcion='Servicio usado en pruebas automatizadas.',
            precio=Decimal('25.00'),
        )
        self.mascota = Mascota.objects.create(
            propietario=self.user,
            nombre='Luna',
            raza='Mestiza',
        )
        self.cita = Cita.objects.create(
            negocio=self.negocio,
            propietario=self.user,
            sucursal=self.sucursal,
            mascota=self.mascota,
            servicio=self.servicio,
            precio_acordado=Decimal('25.00'),
            fecha=datetime.date.today() + datetime.timedelta(days=1),
            hora=datetime.time(10, 0),
        )
        self.client.login(username='cliente_pago', password='clave-segura-para-pruebas')

    def test_pago_simulado_aprobado_no_llama_datafast(self):
        pagar_url = reverse('pagar_cita', args=[self.cita.id])
        simulacion_url = reverse('simular_pago_cita', args=[self.cita.id])

        with patch('citas.views.requests.post') as datafast_request:
            response = self.client.post(pagar_url, {'metodo_pago': 'TARJETA'})

        self.assertRedirects(response, simulacion_url)
        datafast_request.assert_not_called()

        response = self.client.post(simulacion_url, {'accion': 'aprobar'})
        self.assertRedirects(response, reverse('mis_citas'))

        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado_pago, 'PAGADO')
        self.assertEqual(self.cita.metodo_pago, 'TARJETA')
        self.assertRegex(self.cita.referencia_pago, rf'^SIM-{self.cita.id}-\d+$')

    def test_pago_simulado_rechazado_mantiene_pendiente(self):
        simulacion_url = reverse('simular_pago_cita', args=[self.cita.id])

        response = self.client.get(simulacion_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Modo simulaci')
        self.assertContains(response, 'Simular pago aprobado')
        self.assertContains(response, 'Simular pago rechazado')
        self.assertNotContains(response, 'N&uacute;mero de tarjeta')

        response = self.client.post(simulacion_url, {'accion': 'rechazar'})

        self.assertRedirects(response, reverse('mis_citas'))
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado_pago, 'PENDIENTE')
        self.assertEqual(self.cita.referencia_pago, '')

    @override_settings(SIMULATE_PAYMENTS=False)
    def test_plan_sin_pagos_bloquea_el_flujo_real(self):
        response = self.client.get(reverse('pagar_cita', args=[self.cita.id]))

        self.assertRedirects(response, reverse('mis_citas'))
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado_pago, 'PENDIENTE')

    def test_cita_ajena_no_puede_ser_modificada(self):
        self.client.logout()
        self.client.login(username='otro_cliente', password='clave-segura-para-pruebas')

        response = self.client.post(
            reverse('simular_pago_cita', args=[self.cita.id]),
            {'accion': 'aprobar'},
        )

        self.assertEqual(response.status_code, 404)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado_pago, 'PENDIENTE')
        self.assertEqual(self.cita.referencia_pago, '')

    @override_settings(SIMULATE_PAYMENTS=False)
    def test_desactivado_conserva_el_flujo_datafast(self):
        self.plan.permite_pagos = True
        self.plan.save(update_fields=['permite_pagos'])
        with patch('citas.views.datafast_configurado', return_value=True), patch(
            'citas.views.crear_checkout_datafast', return_value='checkout-de-prueba'
        ) as checkout_mock:
            response = self.client.post(
                reverse('pagar_cita', args=[self.cita.id]),
                {'metodo_pago': 'TARJETA'},
            )

        self.assertRedirects(response, reverse('datafast_widget', args=[self.cita.id]))
        checkout_mock.assert_called_once()
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.datafast_checkout_id, 'checkout-de-prueba')
        self.assertEqual(self.cita.estado_pago, 'PENDIENTE')
