from django.db import OperationalError, ProgrammingError

from .services import obtener_configuracion_negocio, estado_licencia


def business_settings(request):
    try:
        business = obtener_configuracion_negocio()
    except (OperationalError, ProgrammingError):
        from django.conf import settings
        business = settings.BUSINESS_CONFIG

    try:
        licencia = estado_licencia()
    except (OperationalError, ProgrammingError):
        licencia = {'activa': True, 'mensaje': '', 'suscripcion': None}

    return {
        'business': business,
        'licencia': licencia,
    }
