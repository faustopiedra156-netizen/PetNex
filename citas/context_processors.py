from django.db import OperationalError, ProgrammingError

from .services import obtener_configuracion_negocio, obtener_negocio_usuario, obtener_negocio_publico, obtener_rol_usuario, estado_licencia


def business_settings(request):
    negocio_actual = getattr(request, '_petnexo_negocio_actual', None)
    rol_actual = 'DUENO_PETNEXO' if request.user.is_superuser else None
    try:
        if not hasattr(request, '_petnexo_negocio_actual'):
            negocio_actual = obtener_negocio_usuario(request.user) or obtener_negocio_publico()
            request._petnexo_negocio_actual = negocio_actual
        business = obtener_configuracion_negocio(negocio_actual)
        rol_actual = obtener_rol_usuario(request.user) or rol_actual
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
        'rol_actual': rol_actual,
    }
