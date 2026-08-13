from django.contrib import admin
from .models import (
    Servicio, Mascota, PerfilCliente, Cita, Calificacion, ConfiguracionNegocio,
    Sucursal, PlanSuscripcion, SuscripcionNegocio, PagoSuscripcion,
)


@admin.register(PlanSuscripcion)
class PlanSuscripcionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio_mensual', 'max_sucursales', 'max_citas_mes', 'permite_pagos', 'permite_chatbot', 'activo')
    list_filter = ('activo', 'permite_pagos', 'permite_chatbot', 'permite_reportes')
    search_fields = ('nombre',)


@admin.register(SuscripcionNegocio)
class SuscripcionNegocioAdmin(admin.ModelAdmin):
    list_display = ('plan', 'estado', 'fecha_inicio', 'fecha_vencimiento', 'dias_restantes', 'actualizado_en')
    list_filter = ('estado', 'plan')
    search_fields = ('plan__nombre', 'contacto_pago')


@admin.register(PagoSuscripcion)
class PagoSuscripcionAdmin(admin.ModelAdmin):
    list_display = ('id', 'plan', 'ciclo_facturacion', 'monto', 'estado', 'usuario', 'creado_en')
    list_filter = ('estado', 'ciclo_facturacion', 'plan', 'metodo')
    search_fields = ('usuario__username', 'usuario__email', 'contacto_pago', 'checkout_id', 'referencia')
    readonly_fields = ('checkout_id', 'datafast_resource_path', 'datafast_result_code', 'referencia', 'creado_en', 'actualizado_en')


@admin.register(ConfiguracionNegocio)
class ConfiguracionNegocioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ciudad', 'telefono', 'email', 'actualizado_en')
    fieldsets = (
        ('Identidad', {'fields': ('nombre', 'nombre_corto', 'categoria', 'slogan')}),
        ('Ubicacion y contacto', {'fields': ('ciudad', 'pais', 'codigo_pais', 'direccion', 'telefono', 'email', 'horario')}),
        ('Pagina publica', {'fields': ('hero_badge', 'hero_titulo', 'hero_descripcion', 'descripcion_footer', 'etiqueta_resenas', 'etiqueta_ubicacion', 'texto_boton_principal')}),
        ('Operacion', {'fields': ('moneda', 'simbolo_moneda', 'prefijo_transaccion', 'mostrar_cuentas_demo', 'google_login_activo')}),
    )

@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio', 'duracion_minutos', 'destacado', 'activo')
    list_filter = ('categoria', 'destacado', 'activo')
    search_fields = ('nombre', 'descripcion')


@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ciudad', 'direccion', 'telefono', 'activa')
    list_filter = ('activa', 'ciudad')
    search_fields = ('nombre', 'ciudad', 'direccion')


@admin.register(Mascota)
class MascotaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'especie', 'raza', 'propietario', 'edad', 'peso_kg')
    list_filter = ('especie', 'raza')
    search_fields = ('nombre', 'raza', 'propietario__username', 'propietario__first_name')


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ('id', 'sucursal', 'mascota', 'servicio', 'propietario', 'fecha', 'hora', 'estado', 'etapa_seguimiento', 'progreso', 'estado_pago')
    list_filter = ('sucursal', 'estado', 'etapa_seguimiento', 'estado_pago', 'fecha', 'servicio')
    search_fields = ('mascota__nombre', 'propietario__username', 'servicio__nombre', 'sucursal__nombre')
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
