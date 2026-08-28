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
    PerfilCliente,
    PlanSuscripcion,
    Servicio,
    Sucursal,
    SuscripcionNegocio,
    UsuarioNegocio,
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

    @patch('citas.services.logger.exception')
    @patch('citas.services.send_mail', side_effect=AttributeError('configuracion antigua'))
    def test_falla_del_correo_no_interrumpe_el_flujo(self, send_mail, log_exception):
        self.assertFalse(
            enviar_notificacion(
                'Nueva cita',
                'Mensaje de prueba',
                ['cliente@example.com'],
            )
        )
        send_mail.assert_called_once()
        log_exception.assert_called_once()


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
        PerfilCliente.objects.create(usuario=self.user, negocio=self.negocio)
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
            negocio=self.negocio,
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

        with patch('django.core.handlers.exception.log_response'):
            response = self.client.post(
                reverse('simular_pago_cita', args=[self.cita.id]),
                {'accion': 'aprobar'},
            )

        self.assertEqual(response.status_code, 404)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado_pago, 'PENDIENTE')
        self.assertEqual(self.cita.referencia_pago, '')

    def test_agenda_no_muestra_mascotas_de_otro_negocio(self):
        otro_negocio = Negocio.objects.create(nombre='Otro local')
        Mascota.objects.create(
            negocio=otro_negocio,
            propietario=self.user,
            nombre='Mascota de otro local',
            raza='Mestiza',
        )

        response = self.client.get(reverse('agendar_cita'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.mascota.nombre)
        self.assertNotContains(response, 'Mascota de otro local')

    def test_mascota_de_otro_negocio_no_se_puede_editar(self):
        otro_negocio = Negocio.objects.create(nombre='Otro local')
        mascota_ajena = Mascota.objects.create(
            negocio=otro_negocio,
            propietario=self.user,
            nombre='Mascota protegida',
            raza='Mestiza',
        )

        response = self.client.get(reverse('editar_mascota', args=[mascota_ajena.id]))

        self.assertEqual(response.status_code, 404)

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


class RoleAccessTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_superuser(
            username='petnexo_owner',
            email='owner@petnexo.test',
            password='clave-segura-owner',
        )
        self.local_admin = user_model.objects.create_user(
            username='admin_local',
            email='admin@local.test',
            password='clave-segura-local',
            is_staff=True,
        )
        self.negocio = Negocio.objects.create(
            nombre='Local del administrador',
            propietario=self.local_admin,
        )

    def test_dueno_petnexo_solo_ve_la_administracion_del_sistema(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse('gestion_admin'))

        self.assertRedirects(response, reverse('cuentas_admin'))
        response = self.client.get(reverse('cuentas_admin'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Administración del sistema')
        self.assertNotContains(response, 'Mi Perfil')
        self.assertNotContains(response, 'Mis Citas')
        self.assertNotContains(response, 'Mis Mascotas')

        response = self.client.get(reverse('mis_citas'))
        self.assertRedirects(response, reverse('cuentas_admin'))

    def test_dueno_no_puede_editar_configuracion_operativa(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse('configuracion_negocio'))

        self.assertRedirects(response, reverse('cuentas_admin'))

    def test_admin_local_puede_operar_su_panel_pero_no_cuentas_del_sistema(self):
        self.client.force_login(self.local_admin)

        response = self.client.get(reverse('gestion_admin'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Administrador del local')

        response = self.client.get(reverse('cuentas_admin'))
        self.assertRedirects(response, reverse('gestion_admin'))

        response = self.client.get(reverse('mis_citas'))
        self.assertRedirects(response, reverse('gestion_admin'))

    def test_empleado_puede_operar_sin_administrar_configuracion_ni_pagos(self):
        empleado = get_user_model().objects.create_user(
            username='empleado_local',
            password='clave-segura-empleado',
            is_staff=True,
        )
        UsuarioNegocio.objects.create(
            usuario=empleado,
            negocio=self.negocio,
            rol='EMPLEADO',
        )
        self.client.force_login(empleado)

        response = self.client.get(reverse('gestion_admin'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Personal del local')
        self.assertNotContains(response, 'Configurar Local')
        self.assertNotContains(response, 'Suscrip')
        self.assertNotContains(response, 'Nueva sucursal')
        self.assertNotContains(response, 'Editar sucursal')
        self.assertNotContains(response, 'name="estado_pago"')
        self.assertNotContains(response, 'name="metodo_pago"')

        response = self.client.get(reverse('configuracion_negocio'))
        self.assertRedirects(response, reverse('gestion_admin'))
        response = self.client.get(reverse('suscripcion_negocio'))
        self.assertRedirects(response, reverse('gestion_admin'))
        response = self.client.post(
            reverse('actualizar_pago_cita', args=[999999]),
            {'estado_pago': 'PAGADO', 'metodo_pago': 'EFECTIVO'},
        )
        self.assertRedirects(response, reverse('gestion_admin'))


class MultiNegocioIsolationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.cliente = user_model.objects.create_user(
            username='cliente_multi_local',
            email='cliente-multi@example.com',
            password='clave-segura-cliente',
        )
        administrador_1 = user_model.objects.create_user(
            username='admin_local_uno',
            password='clave-segura-admin',
            is_staff=True,
        )
        administrador_2 = user_model.objects.create_user(
            username='admin_local_dos',
            password='clave-segura-admin',
            is_staff=True,
        )
        self.negocio_1 = Negocio.objects.create(
            nombre='Local Uno',
            propietario=administrador_1,
        )
        self.negocio_2 = Negocio.objects.create(
            nombre='Local Dos',
            propietario=administrador_2,
        )
        PerfilCliente.objects.create(usuario=self.cliente, negocio=self.negocio_1)
        Mascota.objects.create(
            negocio=self.negocio_1,
            propietario=self.cliente,
            nombre='Mascota visible',
            raza='Mestiza',
        )
        Mascota.objects.create(
            negocio=self.negocio_2,
            propietario=self.cliente,
            nombre='Mascota aislada',
            raza='Mestiza',
        )
        self.client.force_login(self.cliente)

    def test_cliente_solo_ve_mascotas_de_su_negocio_principal(self):
        response = self.client.get(reverse('mis_mascotas'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mascota visible')
        self.assertNotContains(response, 'Mascota aislada')
