from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Calificacion, Cita, ConfiguracionNegocio, Servicio, Sucursal
from .services import invalidar_cache_negocio


@receiver([post_save, post_delete], sender=ConfiguracionNegocio)
@receiver([post_save, post_delete], sender=Servicio)
@receiver([post_save, post_delete], sender=Sucursal)
@receiver([post_save, post_delete], sender=Cita)
def invalidar_cache_por_negocio(sender, instance, **kwargs):
    invalidar_cache_negocio(getattr(instance, 'negocio_id', None))


@receiver([post_save, post_delete], sender=Calificacion)
def invalidar_cache_por_calificacion(sender, instance, **kwargs):
    try:
        negocio_id = instance.cita.negocio_id
    except Cita.DoesNotExist:
        return
    invalidar_cache_negocio(negocio_id)
