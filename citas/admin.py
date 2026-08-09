from django.contrib import admin
from .models import Servicio, Mascota, PerfilCliente, Cita, Calificacion

@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio', 'duracion_minutos', 'destacado', 'activo')
    list_filter = ('categoria', 'destacado', 'activo')
    search_fields = ('nombre', 'descripcion')


@admin.register(Mascota)
class MascotaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'especie', 'raza', 'propietario', 'edad', 'peso_kg')
    list_filter = ('especie', 'raza')
    search_fields = ('nombre', 'raza', 'propietario__username', 'propietario__first_name')


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ('id', 'mascota', 'servicio', 'propietario', 'fecha', 'hora', 'estado', 'etapa_seguimiento', 'progreso', 'estado_pago')
    list_filter = ('estado', 'etapa_seguimiento', 'estado_pago', 'fecha', 'servicio')
    search_fields = ('mascota__nombre', 'propietario__username', 'servicio__nombre')
    date_hierarchy = 'fecha'


@admin.register(PerfilCliente)
class PerfilClienteAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'telefono', 'barrio', 'contacto_preferido')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name', 'telefono', 'barrio')


@admin.register(Calificacion)
class CalificacionAdmin(admin.ModelAdmin):
    list_display = ('cita', 'cliente', 'puntuacion', 'creado_en')
    list_filter = ('puntuacion', 'creado_en')
    search_fields = ('cliente__username', 'cliente__first_name', 'cliente__last_name', 'comentario')
