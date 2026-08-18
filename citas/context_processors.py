from django.db import OperationalError, ProgrammingError

from .services import obtener_configuracion_negocio, obtener_negocio_usuario, obtener_negocio_publico, estado_licencia


def business_settings(request):
    negocio_actual = None
    try:
        negocio_actual = obtener_negocio_usuario(request.user) or obtener_negocio_publico()
        business = obtener_configuracion_negocio(negocio_actual)
    except (OperationalError, ProgrammingError):
        from django.conf import settings
        business = settings.BUSINESS_CONFIG

    try:
        licencia = estado_licencia(negocio_actual)
    except (OperationalError, ProgrammingError):
        licencia = {'activa': True, 'mensaje': '', 'suscripcion': None}

    return {
        'business': business,
        'licencia': licencia,
        'negocio_actual': negocio_actual,
    }
