from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import OperationalError, ProgrammingError
from django.utils import timezone

from .models import ConfiguracionNegocio, Negocio, SuscripcionNegocio


def _negocio_cache_id(negocio):
    return getattr(negocio, 'pk', None) or 'publico'


def invalidar_cache_negocio(negocio_id=None):
    negocio_id = negocio_id or 'publico'
    cache.delete_many([
        f'negocio:config:{negocio_id}',
        f'negocio:home-metrics:{negocio_id}',
    ])


def obtener_negocio_usuario(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    if user.is_superuser:
        return None
    return Negocio.objects.filter(propietario=user, activo=True).first()


def obtener_negocio_publico():
    return Negocio.objects.filter(activo=True).order_by('id').first()


def obtener_configuracion_negocio(negocio=None):
    cache_key = f'negocio:config:{_negocio_cache_id(negocio)}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    config = ConfiguracionNegocio.actual(negocio=negocio)
    if config:
        business = config.as_business_dict()
    else:
        business = settings.BUSINESS_CONFIG.copy()
    cache.set(cache_key, business, timeout=settings.CACHE_DEFAULT_TIMEOUT)
    return business


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


def obtener_suscripcion_negocio(negocio=None):
    try:
        return SuscripcionNegocio.actual(negocio=negocio)
    except (OperationalError, ProgrammingError):
        return None


def estado_licencia(negocio=None):
    suscripcion = obtener_suscripcion_negocio(negocio=negocio)
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
