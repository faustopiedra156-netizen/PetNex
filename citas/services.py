from django.conf import settings
from django.core.mail import send_mail
from django.db import OperationalError, ProgrammingError
from django.utils import timezone

from .models import ConfiguracionNegocio, SuscripcionNegocio


def obtener_configuracion_negocio():
    config = ConfiguracionNegocio.actual()
    if config:
        return config.as_business_dict()
    return settings.BUSINESS_CONFIG


def enviar_notificacion(asunto, mensaje, destinatarios):
    destinatarios = [correo for correo in destinatarios if correo]
    if not destinatarios:
        return False
    return send_mail(
        asunto,
        mensaje,
        settings.DEFAULT_FROM_EMAIL,
        destinatarios,
        fail_silently=True,
    )


def obtener_suscripcion_negocio():
    try:
        return SuscripcionNegocio.actual()
    except (OperationalError, ProgrammingError):
        return None


def estado_licencia():
    suscripcion = obtener_suscripcion_negocio()
    if not suscripcion:
        return {
            'existe': False,
            'activa': True,
            'por_vencer': False,
            'dias_restantes': None,
            'mensaje': '',
            'suscripcion': None,
        }

    activa = suscripcion.esta_activa
    por_vencer = suscripcion.esta_por_vencer
    mensaje = ''
    if not activa:
        mensaje = 'La suscripcion de PetNexo esta vencida o suspendida. Renueva el servicio para seguir usando las funciones operativas.'
    elif por_vencer:
        mensaje = f'La suscripcion de PetNexo vence en {suscripcion.dias_restantes} dias.'

    return {
        'existe': True,
        'activa': activa,
        'por_vencer': por_vencer,
        'dias_restantes': suscripcion.dias_restantes,
        'vence_hoy': suscripcion.fecha_vencimiento == timezone.localdate(),
        'mensaje': mensaje,
        'suscripcion': suscripcion,
    }
