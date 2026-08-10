from django.db import OperationalError, ProgrammingError

from .services import obtener_configuracion_negocio


def business_settings(request):
    try:
        business = obtener_configuracion_negocio()
    except (OperationalError, ProgrammingError):
        from django.conf import settings
        business = settings.BUSINESS_CONFIG

    return {
        'business': business,
    }
