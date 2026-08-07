from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('servicios/', views.servicios_view, name='servicios'),
    path('contacto/', views.contacto_view, name='contacto'),
    path('citas/agendar/', views.agendar_cita_view, name='agendar_cita'),
    path('citas/mis-citas/', views.mis_citas_view, name='mis_citas'),
    path('citas/<int:cita_id>/pagar/', views.pagar_cita_view, name='pagar_cita'),
    path('citas/<int:cita_id>/tarjeta/', views.datafast_widget_view, name='datafast_widget'),
    path('citas/<int:cita_id>/tarjeta/resultado/', views.datafast_result_view, name='datafast_result'),
    path('citas/cancelar/<int:cita_id>/', views.cancelar_cita_view, name='cancelar_cita'),
    path('mascotas/', views.mis_mascotas_view, name='mis_mascotas'),
    path('mascotas/nueva/', views.nueva_mascota_view, name='nueva_mascota'),
    path('mascotas/editar/<int:mascota_id>/', views.editar_mascota_view, name='editar_mascota'),
    path('mascotas/eliminar/<int:mascota_id>/', views.eliminar_mascota_view, name='eliminar_mascota'),
    path('perfil/', views.perfil_cliente_view, name='perfil_cliente'),
    
    # Admin / Staff
    path('gestion/', views.gestion_admin_view, name='gestion_admin'),
    path('gestion/cita/<int:cita_id>/estado/', views.cambiar_estado_cita_view, name='cambiar_estado_cita'),
    path('gestion/cita/<int:cita_id>/pago/', views.actualizar_pago_cita_view, name='actualizar_pago_cita'),
    path('gestion/cita/<int:cita_id>/seguimiento/', views.actualizar_seguimiento_cita_view, name='actualizar_seguimiento_cita'),
    path('gestion/servicio/<int:servicio_id>/toggle/', views.toggle_servicio_view, name='toggle_servicio'),

    # Auth
    path('registro/', views.registro_view, name='registro'),
    path('login/', views.login_usuario_view, name='login'),
    path('logout/', views.logout_usuario_view, name='logout'),
]
