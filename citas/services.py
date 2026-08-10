from django.conf import settings
from django.core.mail import send_mail

from .models import ConfiguracionNegocio


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
