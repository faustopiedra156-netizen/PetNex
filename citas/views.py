import re
import datetime
import logging
import secrets
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import requests
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import connection, DatabaseError, IntegrityError, OperationalError, ProgrammingError, transaction
from django.db.models import Sum, Count, Q, Avg
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from .models import Servicio, Mascota, PerfilCliente, Cita, Calificacion, ConfiguracionNegocio, Sucursal, PlanSuscripcion, SuscripcionNegocio, PagoSuscripcion, Negocio, CodigoRecuperacionContrasena
from .forms import MascotaForm, PerfilClienteForm, CitaForm, CalificacionForm, RegistroForm, ConfiguracionNegocioForm, ServicioForm, AdminUsuarioForm, SucursalForm, SolicitarCodigoRecuperacionForm, VerificarCodigoRecuperacionForm, NuevaContrasenaRecuperacionForm, ContactoForm
from .services import obtener_configuracion_negocio, obtener_negocio_usuario, obtener_negocio_cliente, obtener_negocio_publico, obtener_rol_usuario, enviar_notificacion, estado_licencia

ESTADOS_EDITABLES_CLIENTE = {'PENDIENTE', 'CONFIRMADA'}
PROGRESO_POR_ETAPA = {
    'AGENDADA': 0,
    'RECIBIDA': 15,
    'BANO': 35,
    'SECADO': 55,
    'CORTE': 75,
    'REVISION': 90,
    'LISTA': 100,
    'ENTREGADA': 100,
}
ESCALA_CALIFICACION = [
    {'valor': 1, 'texto': 'Mala', 'detalle': 'No cumplió lo esperado.'},
    {'valor': 2, 'texto': 'Regular', 'detalle': 'Hubo varios detalles por mejorar.'},
    {'valor': 3, 'texto': 'Buena', 'detalle': 'Cumplió de forma aceptable.'},
    {'valor': 4, 'texto': 'Muy buena', 'detalle': 'Buen servicio con detalles menores.'},
    {'valor': 5, 'texto': 'Excelente', 'detalle': 'Servicio completo y muy satisfactorio.'},
]
DATAFAST_RESULT_OK_PATTERN = re.compile(r'^(000\.000\.|000\.100\.1|000\.[36])')
logger = logging.getLogger(__name__)


def client_ip(request):
    if settings.TRUST_X_FORWARDED_FOR:
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if forwarded:
            return forwarded.split(',', 1)[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def rate_limit_exceeded(request, scope, limit, window_seconds):
    """Small cache-based throttle; Redis makes it shared by every Gunicorn worker."""
    cache_key = f'rate-limit:{scope}:{client_ip(request)}'
    if cache.add(cache_key, 1, timeout=window_seconds):
        return False
    try:
        attempts = cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, timeout=window_seconds)
        return False
    return attempts > limit


def parse_hora_config(valor, default):
    try:
        return datetime.time.fromisoformat(str(valor))
    except (TypeError, ValueError):
        return default


def generar_horarios_disponibilidad():
    horarios = []
    apertura = parse_hora_config(settings.APPOINTMENT_OPEN_TIME, datetime.time(8, 30))
    cierre_config = parse_hora_config(settings.APPOINTMENT_CLOSE_TIME, datetime.time(18, 30))
    slot_minutos = max(int(settings.APPOINTMENT_SLOT_MINUTES or 30), 1)
    hora = datetime.datetime.combine(datetime.date.today(), apertura)
    cierre = datetime.datetime.combine(datetime.date.today(), cierre_config)
    while hora <= cierre:
        horarios.append(hora.time())
        hora += datetime.timedelta(minutes=slot_minutos)
    return horarios


def es_dueno_petnexo(user):
    return user.is_authenticated and user.is_superuser


def es_admin_local(user):
    return obtener_rol_usuario(user) == 'ADMIN_LOCAL'


def es_empleado_local(user):
    return obtener_rol_usuario(user) == 'EMPLEADO'


def es_personal_local(user):
    return es_admin_local(user) or es_empleado_local(user)


def es_cliente_final(user):
    return obtener_rol_usuario(user) == 'CLIENTE'


def es_responsable_suscripcion(user):
    return es_admin_local(user)


def negocio_para_request(request):
    if hasattr(request, '_petnexo_negocio_actual'):
        return request._petnexo_negocio_actual

    if request.user.is_authenticated:
        negocio = obtener_negocio_usuario(request.user)
        if not negocio and es_cliente_final(request.user):
            negocio = obtener_negocio_cliente(request.user)
        if negocio:
            request._petnexo_negocio_actual = negocio
            return negocio
    request._petnexo_negocio_actual = obtener_negocio_publico()
    return request._petnexo_negocio_actual


def negocio_admin_o_redirect(request):
    negocio = obtener_negocio_usuario(request.user)
    if negocio:
        return negocio, None
    messages.error(request, "Tu cuenta administrativa aun no tiene un negocio asignado.")
    return None, redirect('home')


def redirect_si_no_admin_local(request):
    if es_personal_local(request.user):
        return None
    messages.error(request, "Esta accion corresponde al personal autorizado del local.")
    if request.user.is_superuser:
        return redirect('cuentas_admin')
    return redirect('home')


def redirect_si_no_admin_principal(request):
    if es_admin_local(request.user):
        return None
    messages.error(request, "Esta accion corresponde al administrador principal del local.")
    if request.user.is_superuser:
        return redirect('cuentas_admin')
    if es_personal_local(request.user):
        return redirect('gestion_admin')
    return redirect('home')


def redirect_si_no_cliente_final(request):
    if es_cliente_final(request.user):
        return None
    messages.error(request, "Esta seccion corresponde al cliente final.")
    if request.user.is_superuser:
        return redirect('cuentas_admin')
    return redirect('gestion_admin')


def licencia_bloqueada_para_operar(user):
    negocio = obtener_negocio_usuario(user)
    licencia = estado_licencia(negocio)
    return not licencia['activa'] and not user.is_superuser


def datos_transferencia(negocio_obj=None):
    negocio = obtener_configuracion_negocio(negocio_obj)
    return {
        'banco': settings.TRANSFER_BANK_NAME,
        'cuenta': settings.TRANSFER_ACCOUNT_NUMBER,
        'titular': settings.TRANSFER_ACCOUNT_OWNER or negocio['name'],
        'identificacion': settings.TRANSFER_ACCOUNT_ID,
    }


def datafast_configurado():
    return bool(settings.DATAFAST_ENTITY_ID and settings.DATAFAST_AUTHORIZATION)


def datafast_payload_valido(payload, expected_transaction, expected_amount):
    provider_transaction = payload.get('merchantTransactionId') or payload.get('merchantTransactionID')
    if provider_transaction and provider_transaction != expected_transaction:
        return False
    provider_amount = payload.get('amount')
    if provider_amount is None:
        return True
    try:
        return Decimal(str(provider_amount)).quantize(Decimal('0.01')) == expected_amount.quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError, TypeError):
        return False


def csrf_failure(request, reason=""):
    return render(request, 'csrf_error.html', {'reason': reason}, status=403)


def health_check_view(request):
    checks = {
        'app': 'ok',
        'database': 'unknown',
        'migrations_hint': 'Ejecuta py manage.py migrate si la base de datos falla.',
    }
    status = 200
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        checks['database'] = 'ok'
    except DatabaseError as exc:
        checks['database'] = 'error'
        logger.error('Health check de base de datos fallido.', exc_info=True)
        if settings.DEBUG:
            checks['error'] = str(exc)
        status = 503
    return JsonResponse(checks, status=status)


def politica_privacidad_view(request):
    return render(request, 'politica_privacidad.html')


def terminos_condiciones_view(request):
    return render(request, 'terminos_condiciones.html')


def soporte_view(request):
    return render(request, 'soporte.html')


def home_view(request):
    negocio = negocio_para_request(request)
    cache_key = f'negocio:home-metrics:{getattr(negocio, "pk", None) or "publico"}'
    try:
        servicios_destacados = Servicio.objects.filter(negocio=negocio, activo=True, destacado=True).only(
            'nombre', 'descripcion', 'precio', 'duracion_minutos', 'icono'
        )[:settings.HOME_FEATURED_SERVICES_LIMIT]
        servicios_todos = Servicio.objects.filter(negocio=negocio, activo=True).only(
            'nombre', 'descripcion', 'precio', 'duracion_minutos', 'icono'
        )[:settings.HOME_SERVICES_LIMIT]
        metricas = cache.get(cache_key)
        if metricas is None:
            resumen_citas = Cita.objects.filter(negocio=negocio).aggregate(
                mascotas_atendidas=Count(
                    'mascota',
                    distinct=True,
                    filter=Q(estado='ATENDIDA'),
                ),
                total_citas_operativas=Count(
                    'id',
                    filter=~Q(estado='CANCELADA'),
                ),
                citas_atendidas=Count('id', filter=Q(estado='ATENDIDA')),
            )
            resumen_resenas = Calificacion.objects.filter(cita__negocio=negocio).aggregate(promedio=Avg('puntuacion'), total=Count('id'))
            total_citas_operativas = resumen_citas['total_citas_operativas']
            metricas = {
                'mascotas_atendidas': resumen_citas['mascotas_atendidas'],
                'tasa_atencion': round((resumen_citas['citas_atendidas'] / total_citas_operativas) * 100) if total_citas_operativas else 0,
                'promedio_resenas': round(resumen_resenas['promedio'] or 0, 1),
                'total_resenas': resumen_resenas['total'],
            }
            cache.set(cache_key, metricas, timeout=120)
        mascotas_atendidas = metricas['mascotas_atendidas']
        tasa_atencion = metricas['tasa_atencion']
        promedio_resenas = metricas['promedio_resenas']
        total_resenas = metricas['total_resenas']
    except (OperationalError, ProgrammingError):
        servicios_destacados = []
        servicios_todos = []
        mascotas_atendidas = 0
        tasa_atencion = 0
        promedio_resenas = 0
        total_resenas = 0
    
    context = {
        'servicios_destacados': servicios_destacados,
        'servicios_todos': servicios_todos,
        'mascotas_atendidas': mascotas_atendidas,
        'tasa_atencion': tasa_atencion,
        'promedio_resenas': round(promedio_resenas, 1),
        'total_resenas': total_resenas,
        'hero_slides': settings.BUSINESS_CONFIG.get('hero_slides', []),
        'trust_features': settings.BUSINESS_CONFIG.get('trust_features', []),
    }
    return render(request, 'home.html', context)


def servicios_view(request):
    negocio = negocio_para_request(request)
    categoria = request.GET.get('categoria', 'todas')
    try:
        servicios = Servicio.objects.filter(negocio=negocio, activo=True).only(
            'nombre', 'descripcion', 'categoria', 'precio', 'duracion_minutos', 'icono'
        )
        if categoria and categoria != 'todas':
            servicios = servicios.filter(categoria=categoria)
    except (OperationalError, ProgrammingError):
        servicios = []

    categorias = Servicio.CATEGORIAS
    context = {
        'servicios': servicios,
        'categoria_activa': categoria,
        'categorias': categorias,
    }
    return render(request, 'servicios.html', context)


def contacto_view(request):
    negocio = negocio_para_request(request)
    if request.method == 'POST':
        if rate_limit_exceeded(request, 'contacto', limit=5, window_seconds=600):
            messages.error(request, 'Has enviado varios mensajes. Espera unos minutos antes de intentar nuevamente.')
            return redirect('contacto')
        form = ContactoForm(request.POST)
        if form.is_valid():
            mensaje = form.save(commit=False)
            mensaje.negocio = negocio
            mensaje.save()
            business = obtener_configuracion_negocio(negocio)
            enviar_notificacion(
                f'Nuevo mensaje de contacto: {mensaje.nombre}',
                f'Teléfono: {mensaje.telefono}\n\n{mensaje.mensaje}',
                [business['email']],
            )
            messages.success(request, 'Mensaje recibido. Te responderemos por WhatsApp o correo lo antes posible.')
            return redirect('contacto')
    else:
        form = ContactoForm()
    return render(request, 'contacto.html', {'form': form})


def chatbot_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Metodo no permitido.'}, status=405)
    if rate_limit_exceeded(request, 'chatbot', limit=30, window_seconds=60):
        return JsonResponse({'respuesta': 'Has enviado muchas consultas. Espera un minuto para continuar.'}, status=429)

    negocio_obj = negocio_para_request(request)
    licencia = estado_licencia(negocio_obj)
    if licencia['suscripcion'] and not licencia['suscripcion'].plan.permite_chatbot:
        return JsonResponse({'respuesta': 'El chatbot no esta disponible en el plan actual.'}, status=403)

    mensaje = (request.POST.get('mensaje') or '').strip()
    negocio = obtener_configuracion_negocio(negocio_obj)
    if not mensaje:
        return JsonResponse({
            'respuesta': 'Escribeme tu consulta y te ayudo con servicios, horarios, citas, pagos o seguimiento.'
        })

    texto = mensaje.lower()
    try:
        servicios = list(
            Servicio.objects.filter(negocio=negocio_obj, activo=True).only(
                'nombre', 'descripcion', 'categoria', 'precio', 'duracion_minutos'
            )[:6]
        )
    except (OperationalError, ProgrammingError):
        servicios = []

    def lista_servicios():
        if not servicios:
            return 'Todavia no hay servicios activos cargados en el sistema.'
        items = [
            f"{servicio.nombre}: {negocio['currency_symbol']}{servicio.precio} aprox., {servicio.duracion_minutos} min"
            for servicio in servicios
        ]
        return "Estos son algunos servicios disponibles: " + "; ".join(items) + "."

    if any(palabra in texto for palabra in ['hola', 'buenas', 'buenos dias', 'buenas tardes', 'buenas noches']):
        respuesta = (
            f"Hola, soy el asistente de {negocio['name']}. "
            "Puedo ayudarte con servicios, horarios, reservas, pagos y seguimiento de tu mascota."
        )
    elif any(palabra in texto for palabra in ['servicio', 'precio', 'costo', 'cuanto', 'baño', 'bano', 'corte', 'peluqueria']):
        respuesta = lista_servicios() + " Para reservar, entra en Agendar Cita y elige mascota, servicio, fecha y hora."
    elif any(palabra in texto for palabra in ['horario', 'hora', 'atienden', 'abren', 'cierran']):
        respuesta = f"Nuestro horario de atención es: {negocio['opening_hours']}. En la agenda verás solo horarios disponibles por sucursal."
    elif any(palabra in texto for palabra in ['cita', 'reservar', 'agendar', 'turno']):
        respuesta = (
            "Para agendar una cita debes iniciar sesion, registrar tu mascota y seleccionar sucursal, servicio, fecha y hora. "
            "Los horarios con check ya estan ocupados."
        )
    elif any(palabra in texto for palabra in ['pago', 'pagar', 'tarjeta', 'transferencia', 'efectivo', 'debito', 'credito']):
        respuesta = (
            "Puedes pagar una cita desde Mis Citas. El sistema contempla efectivo, transferencia y tarjeta, "
            "segun la configuracion activa del negocio."
        )
    elif any(palabra in texto for palabra in ['seguimiento', 'estado', 'progreso', 'mascota', 'haciendo']):
        respuesta = (
            "El seguimiento se consulta en Mis Citas. El administrador actualiza la etapa de la mascota: recibida, baño, secado, corte, revision y lista para retirar."
        )
    elif any(palabra in texto for palabra in ['contacto', 'telefono', 'whatsapp', 'correo', 'direccion', 'ubicacion']):
        respuesta = (
            f"Puedes contactarnos al {negocio['phone']}, escribir a {negocio['email']} "
            f"o visitarnos en {negocio['address']}."
        )
    elif any(palabra in texto for palabra in ['registro', 'cuenta', 'login', 'iniciar sesion']):
        respuesta = "Puedes crear tu cuenta en Registrarse. Luego podras guardar mascotas, agendar citas y revisar pagos o seguimiento."
    else:
        respuesta = (
            "Puedo ayudarte con servicios, precios, horarios, citas, pagos, contacto o seguimiento. "
            "Prueba escribiendo: quiero agendar una cita, cuánto cuesta un baño, o cómo va mi mascota."
        )

    return JsonResponse({'respuesta': respuesta})


@login_required
def disponibilidad_horarios_view(request):
    if not es_cliente_final(request.user):
        return JsonResponse({'horarios': [], 'estado': 'no_autorizado'}, status=403)
    negocio = negocio_para_request(request)
    sucursal_id = request.GET.get('sucursal')
    fecha = request.GET.get('fecha')
    if not sucursal_id or not fecha:
        return JsonResponse({'horarios': [], 'estado': 'incompleto'})

    try:
        fecha_obj = datetime.date.fromisoformat(fecha)
    except ValueError:
        return JsonResponse({'horarios': [], 'estado': 'fecha_invalida'}, status=400)

    sucursal = Sucursal.objects.filter(negocio=negocio, id=sucursal_id, activa=True).first()
    if not sucursal:
        return JsonResponse({'horarios': [], 'estado': 'sucursal_invalida'}, status=404)

    if fecha_obj < timezone.localdate():
        return JsonResponse({
            'horarios': [],
            'estado': 'fecha_pasada',
            'mensaje': 'La fecha seleccionada ya paso. Elige una fecha desde hoy en adelante.',
        })

    if not sucursal.atiende_en_fecha(fecha_obj):
        return JsonResponse({
            'horarios': [],
            'estado': 'dia_cerrado',
            'mensaje': 'La sucursal no atiende en la fecha seleccionada.',
        })

    ocupadas = set(
        Cita.objects.filter(
            negocio=negocio,
            sucursal=sucursal,
            fecha=fecha_obj,
        ).exclude(estado='CANCELADA').values_list('hora', flat=True)
    )
    horarios = [
        {
            'hora': hora.strftime('%H:%M'),
            'ocupado': hora in ocupadas,
        }
        for hora in sucursal.generar_horarios()
    ]
    return JsonResponse({
        'horarios': horarios,
        'estado': 'ok',
        'sucursal': sucursal.nombre,
        'fecha': fecha_obj.isoformat(),
    })


@login_required
def agendar_cita_view(request):
    redirect_response = redirect_si_no_cliente_final(request)
    if redirect_response:
        return redirect_response
    negocio = negocio_para_request(request)
    licencia = estado_licencia(negocio)
    if not licencia['activa'] and not request.user.is_superuser:
        messages.error(request, licencia['mensaje'])
        return redirect('home')
    if licencia['suscripcion'] and not request.user.is_superuser:
        hoy = timezone.localdate()
        citas_mes = Cita.objects.filter(
            negocio=negocio,
            creado_en__year=hoy.year,
            creado_en__month=hoy.month,
        ).exclude(estado='CANCELADA').count()
        if citas_mes >= licencia['suscripcion'].plan.max_citas_mes:
            messages.error(request, "El plan actual alcanzo el limite de citas mensuales. Renueva o sube de plan para seguir agendando.")
            return redirect('home')

    servicio_id = request.GET.get('servicio_id')
    servicio_preseleccionado = None
    if servicio_id:
        servicio_preseleccionado = Servicio.objects.filter(negocio=negocio, id=servicio_id, activo=True).first()

    # Verify user has at least one pet registered
    mascotas_usuario = Mascota.objects.filter(
        propietario=request.user,
        negocio=negocio,
    ).only('nombre', 'raza')
    if not mascotas_usuario.exists():
        messages.info(request, "Primero registra a tu mascota para poder agendar una cita de peluquería.")
        return redirect('nueva_mascota')

    if request.method == 'POST':
        form = CitaForm(request.user, request.POST, negocio=negocio)
        if form.is_valid():
            cita = form.save(commit=False)
            cita.negocio = negocio
            cita.propietario = request.user
            cita.precio_acordado = cita.servicio.precio
            try:
                with transaction.atomic():
                    cita.save()
            except IntegrityError:
                form.add_error('hora', 'Ese horario acaba de ser ocupado. Elige otro disponible.')
                messages.error(request, 'El horario seleccionado ya no está disponible.')
                return render(request, 'agendar.html', {
                    'form': form,
                    'servicio_preseleccionado': servicio_preseleccionado,
                    'mascotas': mascotas_usuario,
                })
            negocio_datos = obtener_configuracion_negocio(negocio)
            enviar_notificacion(
                f"Nueva cita en {negocio_datos['name']}",
                f"Hola {request.user.first_name or request.user.username}, tu cita para {cita.mascota.nombre} fue registrada en {cita.sucursal.nombre} para el {cita.fecha} a las {cita.hora}.",
                [request.user.email],
            )
            enviar_notificacion(
                f"Nueva cita #{cita.id}",
                f"{cita.sucursal.nombre} - {cita.mascota.nombre} - {cita.servicio.nombre} - {cita.fecha} {cita.hora}. Cliente: {request.user.get_full_name() or request.user.username}",
                [settings.ADMIN_NOTIFICATION_EMAIL],
            )
            messages.success(request, f"Cita agendada para {cita.mascota.nombre} en {cita.sucursal.nombre} el {cita.fecha}. Te contactaremos para confirmar.")
            return redirect('mis_citas')
        else:
            messages.error(request, "Por favor revisa los campos ingresados.")
    else:
        initial = {}
        if servicio_preseleccionado:
            initial['servicio'] = servicio_preseleccionado
        form = CitaForm(request.user, initial=initial, negocio=negocio)

    context = {
        'form': form,
        'servicio_preseleccionado': servicio_preseleccionado,
        'mascotas': mascotas_usuario,
    }
    return render(request, 'agendar.html', context)


@login_required
def mis_citas_view(request):
    redirect_response = redirect_si_no_cliente_final(request)
    if redirect_response:
        return redirect_response
    negocio = negocio_para_request(request)
    citas_queryset = Cita.objects.select_related(
        'sucursal', 'mascota', 'servicio', 'calificacion'
    ).filter(propietario=request.user, negocio=negocio).order_by('-fecha', '-hora')
    citas = Paginator(citas_queryset, 20).get_page(request.GET.get('page'))
    context = {
        'citas': citas,
    }
    return render(request, 'mis_citas.html', context)


@login_required
def calificar_cita_view(request, cita_id):
    redirect_response = redirect_si_no_cliente_final(request)
    if redirect_response:
        return redirect_response
    negocio = negocio_para_request(request)
    cita = get_object_or_404(
        Cita.objects.select_related('mascota', 'servicio'),
        id=cita_id,
        propietario=request.user,
        negocio=negocio,
    )
    if cita.estado != 'ATENDIDA':
        messages.error(request, "Solo puedes calificar una cita atendida.")
        return redirect('mis_citas')

    calificacion = Calificacion.objects.filter(cita=cita, cliente=request.user).first()
    if request.method == 'POST':
        form = CalificacionForm(request.POST, instance=calificacion)
        if form.is_valid():
            nueva_calificacion = form.save(commit=False)
            nueva_calificacion.cita = cita
            nueva_calificacion.cliente = request.user
            nueva_calificacion.save()
            messages.success(request, f"Gracias por calificar el servicio de {obtener_configuracion_negocio(cita.negocio)['name']}.")
            return redirect('mis_citas')
    else:
        form = CalificacionForm(instance=calificacion)

    return render(request, 'calificar_cita.html', {
        'cita': cita,
        'form': form,
        'escala_calificacion': ESCALA_CALIFICACION,
        'puntuacion_actual': str(form['puntuacion'].value() or ''),
    })


@login_required
@require_POST
def cancelar_cita_view(request, cita_id):
    redirect_response = redirect_si_no_cliente_final(request)
    if redirect_response:
        return redirect_response
    negocio = negocio_para_request(request)
    cita = get_object_or_404(Cita, id=cita_id, propietario=request.user, negocio=negocio)
    if request.POST.get('confirmacion', '').strip().upper() != 'CANCELAR':
        messages.error(request, "Para cancelar la cita debes escribir CANCELAR.")
        return redirect('mis_citas')

    if cita.estado in ESTADOS_EDITABLES_CLIENTE:
        cita.estado = 'CANCELADA'
        cita.save(update_fields=['estado'])
        messages.warning(request, f"La cita para {cita.mascota.nombre} ha sido cancelada.")
    else:
        messages.error(request, "Esta cita no se puede cancelar.")
    return redirect('mis_citas')


@login_required
def pagar_cita_view(request, cita_id):
    redirect_response = redirect_si_no_cliente_final(request)
    if redirect_response:
        return redirect_response
    negocio = negocio_para_request(request)
    licencia = estado_licencia(negocio)
    if not licencia['activa'] and not request.user.is_superuser:
        messages.error(request, licencia['mensaje'])
        return redirect('mis_citas')
    if (
        not settings.SIMULATE_PAYMENTS
        and licencia['suscripcion']
        and not licencia['suscripcion'].plan.permite_pagos
        and not request.user.is_superuser
    ):
        messages.error(request, "Tu plan actual de PetNexo no incluye gestion de pagos.")
        return redirect('mis_citas')

    cita = get_object_or_404(
        Cita.objects.select_related('servicio', 'sucursal', 'mascota'),
        id=cita_id,
        negocio=negocio,
        propietario=request.user,
    )
    if cita.estado == 'CANCELADA':
        messages.error(request, "No puedes pagar una cita cancelada.")
        return redirect('mis_citas')

    if cita.estado_pago == 'PAGADO':
        messages.info(request, "Esta cita ya se encuentra pagada.")
        return redirect('mis_citas')

    transferencia = datos_transferencia(negocio)

    if request.method == 'POST':
        metodo_pago = request.POST.get('metodo_pago')

        if metodo_pago == 'TRANSFERENCIA':
            referencia = request.POST.get('referencia_pago', '').strip()
            if not referencia:
                messages.error(request, "Ingresa el número de comprobante o referencia de la transferencia.")
                return redirect('pagar_cita', cita_id=cita.id)
            cita.metodo_pago = 'TRANSFERENCIA'
            cita.estado_pago = 'ABONADO'
            cita.referencia_pago = referencia
            cita.save(update_fields=['metodo_pago', 'estado_pago', 'referencia_pago'])
            messages.success(request, f"Transferencia registrada. {obtener_configuracion_negocio(cita.negocio)['name']} confirmara el pago en el panel administrativo.")
            return redirect('mis_citas')

        if metodo_pago == 'EFECTIVO':
            cita.metodo_pago = 'EFECTIVO'
            cita.estado_pago = 'PENDIENTE'
            cita.referencia_pago = 'Pago en local'
            cita.save(update_fields=['metodo_pago', 'estado_pago', 'referencia_pago'])
            messages.info(request, "Tu cita quedó marcada para pago físico en el local.")
            return redirect('mis_citas')

        if metodo_pago == 'TARJETA':
            if settings.SIMULATE_PAYMENTS:
                return redirect('simular_pago_cita', cita_id=cita.id)

            if not datafast_configurado():
                messages.error(request, "El pago con tarjeta aún no tiene credenciales Datafast configuradas.")
                return redirect('pagar_cita', cita_id=cita.id)

            checkout_id = crear_checkout_datafast(request, cita)
            if checkout_id:
                cita.metodo_pago = 'TARJETA'
                cita.datafast_checkout_id = checkout_id
                cita.save(update_fields=['metodo_pago', 'datafast_checkout_id'])
                return redirect('datafast_widget', cita_id=cita.id)

            messages.error(request, "No se pudo iniciar el pago con tarjeta. Intenta nuevamente.")
            return redirect('pagar_cita', cita_id=cita.id)

        messages.error(request, "Selecciona un método de pago válido.")

    return render(request, 'pagar_cita.html', {
        'cita': cita,
        'transferencia': transferencia,
        'tarjeta_configurada': datafast_configurado(),
        'simulacion_pagos': settings.SIMULATE_PAYMENTS,
    })


@login_required
def simular_pago_cita_view(request, cita_id):
    """Run the non-financial payment demo for an owned appointment."""
    redirect_response = redirect_si_no_cliente_final(request)
    if redirect_response:
        return redirect_response
    negocio = negocio_para_request(request)
    licencia = estado_licencia(negocio)
    if not licencia['activa'] and not request.user.is_superuser:
        messages.error(request, licencia['mensaje'])
        return redirect('mis_citas')
    if (
        not settings.SIMULATE_PAYMENTS
        and licencia['suscripcion']
        and not licencia['suscripcion'].plan.permite_pagos
        and not request.user.is_superuser
    ):
        messages.error(request, "Tu plan actual de PetNexo no incluye gestion de pagos.")
        return redirect('mis_citas')

    cita_queryset = Cita.objects.select_related('servicio', 'sucursal', 'mascota')
    cita_filter = {
        'id': cita_id,
        'negocio': negocio,
        'propietario': request.user,
    }
    cita = get_object_or_404(cita_queryset, **cita_filter)

    if not settings.SIMULATE_PAYMENTS:
        messages.error(request, "El modo de simulacion de pagos no esta habilitado.")
        return redirect('pagar_cita', cita_id=cita.id)
    if cita.estado == 'CANCELADA':
        messages.error(request, "No puedes pagar una cita cancelada.")
        return redirect('mis_citas')
    if cita.estado_pago == 'PAGADO':
        messages.info(request, "Esta cita ya se encuentra pagada.")
        return redirect('mis_citas')

    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'rechazar':
            messages.warning(request, "Pago simulado rechazado. No se realizo ningun cobro.")
            return redirect('mis_citas')
        if accion != 'aprobar':
            messages.error(request, "Selecciona una respuesta de simulacion valida.")
            return redirect('simular_pago_cita', cita_id=cita.id)

        with transaction.atomic():
            cita = get_object_or_404(
                cita_queryset.select_for_update(),
                **cita_filter,
            )
            if cita.estado == 'CANCELADA':
                messages.error(request, "No puedes pagar una cita cancelada.")
                return redirect('mis_citas')
            if cita.estado_pago == 'PAGADO':
                messages.info(request, "Esta cita ya se encuentra pagada.")
                return redirect('mis_citas')

            referencia = f'SIM-{cita.id}-{timezone.now():%Y%m%d%H%M%S%f}'
            cita.estado_pago = 'PAGADO'
            cita.metodo_pago = 'TARJETA'
            cita.referencia_pago = referencia
            cita.save(update_fields=['estado_pago', 'metodo_pago', 'referencia_pago'])

        messages.success(request, "Pago simulado correctamente. No se realizo ningun cobro real.")
        return redirect('mis_citas')

    return render(request, 'simulacion_pago.html', {
        'cita': cita,
        'monto': cita.precio_acordado or cita.servicio.precio,
    })


def crear_checkout_datafast(request, cita):
    if settings.SIMULATE_PAYMENTS:
        return None

    url = f"{settings.DATAFAST_BASE_URL}/v1/checkouts"
    user = request.user
    negocio = obtener_configuracion_negocio(cita.negocio)
    amount = f"{(cita.precio_acordado or cita.servicio.precio):.2f}"
    data = {
        'entityId': settings.DATAFAST_ENTITY_ID,
        'amount': amount,
        'currency': negocio['currency'],
        'paymentType': 'DB',
        'merchantTransactionId': f"{negocio['transaction_prefix']}-CITA-{cita.id}",
        'customer.email': user.email or negocio['email'],
        'customer.givenName': user.first_name or user.username,
        'customer.surname': user.last_name or 'Cliente',
        'billing.street1': getattr(getattr(user, 'perfil_cliente', None), 'direccion', '') or negocio['city'],
        'billing.city': negocio['city'],
        'billing.country': negocio['country_code'],
    }
    headers = {'Authorization': f"Bearer {settings.DATAFAST_AUTHORIZATION}"}
    try:
        response = requests.post(url, data=data, headers=headers, timeout=(3.05, settings.DATAFAST_TIMEOUT_SECONDS))
        response.raise_for_status()
        return response.json().get('id')
    except requests.RequestException:
        logger.warning('No se pudo crear el checkout Datafast de la cita %s.', cita.id, exc_info=True)
        return None


def calcular_monto_suscripcion(plan, ciclo_facturacion):
    if ciclo_facturacion == 'ANUAL':
        return (plan.precio_mensual * Decimal('12') * Decimal('0.85')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return plan.precio_mensual.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def normalizar_ciclo_facturacion(valor):
    return 'ANUAL' if str(valor).strip().upper() == 'ANUAL' else 'MENSUAL'


def crear_checkout_suscripcion_datafast(request, pago):
    if settings.SIMULATE_PAYMENTS:
        return None

    url = f"{settings.DATAFAST_BASE_URL}/v1/checkouts"
    user = request.user
    negocio = obtener_configuracion_negocio(pago.suscripcion.negocio)
    data = {
        'entityId': settings.DATAFAST_ENTITY_ID,
        'amount': f"{pago.monto:.2f}",
        'currency': negocio['currency'],
        'paymentType': 'DB',
        'merchantTransactionId': f"{negocio['transaction_prefix']}-SUB-{pago.id}",
        'customer.email': user.email or negocio['email'],
        'customer.givenName': user.first_name or user.username,
        'customer.surname': user.last_name or 'Administrador',
        'billing.street1': negocio['address'],
        'billing.city': negocio['city'],
        'billing.country': negocio['country_code'],
    }
    headers = {'Authorization': f"Bearer {settings.DATAFAST_AUTHORIZATION}"}
    try:
        response = requests.post(url, data=data, headers=headers, timeout=(3.05, settings.DATAFAST_TIMEOUT_SECONDS))
        response.raise_for_status()
        return response.json().get('id')
    except requests.RequestException:
        logger.warning('No se pudo crear el checkout Datafast de la suscripción %s.', pago.id, exc_info=True)
        return None


@login_required
def datafast_widget_view(request, cita_id):
    redirect_response = redirect_si_no_cliente_final(request)
    if redirect_response:
        return redirect_response
    cita = get_object_or_404(
        Cita.objects.select_related('servicio', 'sucursal', 'mascota'),
        id=cita_id,
        negocio=negocio_para_request(request),
        propietario=request.user,
    )
    if settings.SIMULATE_PAYMENTS:
        messages.info(request, "El modo de simulacion esta activo para este entorno.")
        return redirect('simular_pago_cita', cita_id=cita.id)
    if not cita.datafast_checkout_id:
        messages.error(request, "Primero inicia el pago con tarjeta.")
        return redirect('pagar_cita', cita_id=cita.id)
    return render(request, 'datafast_widget.html', {
        'cita': cita,
        'datafast_base_url': settings.DATAFAST_BASE_URL,
        'datafast_brands': settings.DATAFAST_BRANDS,
    })


@login_required
def datafast_result_view(request, cita_id):
    redirect_response = redirect_si_no_cliente_final(request)
    if redirect_response:
        return redirect_response
    cita = get_object_or_404(
        Cita.objects.select_related('servicio', 'sucursal', 'mascota'),
        id=cita_id,
        negocio=negocio_para_request(request),
        propietario=request.user,
    )
    if settings.SIMULATE_PAYMENTS:
        messages.info(request, "El modo de simulacion esta activo para este entorno.")
        return redirect('simular_pago_cita', cita_id=cita.id)
    resource_path = request.GET.get('resourcePath', '')
    if (
        not cita.datafast_checkout_id
        or not re.fullmatch(r'/v1/checkouts/[A-Za-z0-9._/-]+', resource_path)
        or resource_path.rsplit('/', 1)[-1] != cita.datafast_checkout_id
    ):
        messages.error(request, "No se recibió la respuesta del pago.")
        return redirect('mis_citas')

    if cita.estado_pago == 'PAGADO':
        messages.info(request, "Esta cita ya se encuentra pagada.")
        return redirect('mis_citas')

    url = f"{settings.DATAFAST_BASE_URL}{resource_path}"
    params = {'entityId': settings.DATAFAST_ENTITY_ID}
    headers = {'Authorization': f"Bearer {settings.DATAFAST_AUTHORIZATION}"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=(3.05, settings.DATAFAST_TIMEOUT_SECONDS))
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        messages.error(request, "No se pudo verificar el pago con Datafast.")
        return redirect('mis_citas')

    expected_transaction = f"{obtener_configuracion_negocio(cita.negocio)['transaction_prefix']}-CITA-{cita.id}"
    expected_amount = cita.precio_acordado or cita.servicio.precio
    if not datafast_payload_valido(payload, expected_transaction, expected_amount):
        logger.warning('Respuesta Datafast no coincide con la cita %s.', cita.id)
        messages.error(request, 'La respuesta del pago no coincide con esta cita.')
        return redirect('mis_citas')

    result_code = payload.get('result', {}).get('code', '')
    cita.datafast_resource_path = resource_path
    cita.datafast_result_code = result_code
    cita.referencia_pago = payload.get('id', '')

    if DATAFAST_RESULT_OK_PATTERN.match(result_code):
        cita.estado_pago = 'PAGADO'
        messages.success(request, "Pago con tarjeta aprobado.")
    else:
        cita.estado_pago = 'PENDIENTE'
        messages.error(request, f"Pago no aprobado. Código Datafast: {result_code}")

    with transaction.atomic():
        cita_bloqueada = Cita.objects.select_for_update().get(pk=cita.pk)
        if cita_bloqueada.estado_pago == 'PAGADO':
            messages.info(request, 'Esta cita ya se encuentra pagada.')
            return redirect('mis_citas')
        cita_bloqueada.datafast_resource_path = cita.datafast_resource_path
        cita_bloqueada.datafast_result_code = cita.datafast_result_code
        cita_bloqueada.referencia_pago = cita.referencia_pago
        cita_bloqueada.estado_pago = cita.estado_pago
        cita_bloqueada.save(update_fields=[
            'datafast_resource_path', 'datafast_result_code', 'referencia_pago',
            'estado_pago',
        ])
    return redirect('mis_citas')


@login_required
def mis_mascotas_view(request):
    redirect_response = redirect_si_no_cliente_final(request)
    if redirect_response:
        return redirect_response
    negocio = negocio_para_request(request)
    mascotas = Mascota.objects.filter(propietario=request.user, negocio=negocio).only(
        'nombre', 'especie', 'raza', 'edad', 'peso_kg', 'notas_medicas', 'foto', 'foto_url'
    )
    context = {
        'mascotas': mascotas,
    }
    return render(request, 'mascotas.html', context)


@login_required
def perfil_cliente_view(request):
    redirect_response = redirect_si_no_cliente_final(request)
    if redirect_response:
        return redirect_response
    negocio = negocio_para_request(request)
    perfil, _ = PerfilCliente.objects.get_or_create(
        usuario=request.user,
        defaults={'negocio': negocio},
    )
    if not perfil.negocio_id and negocio:
        perfil.negocio = negocio
        perfil.save(update_fields=['negocio'])
    if request.method == 'POST':
        form = PerfilClienteForm(request.POST, instance=perfil, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Tus datos de contacto fueron actualizados.")
            return redirect('perfil_cliente')
    else:
        form = PerfilClienteForm(instance=perfil, user=request.user)

    return render(request, 'perfil.html', {'form': form})


@login_required
def nueva_mascota_view(request):
    redirect_response = redirect_si_no_cliente_final(request)
    if redirect_response:
        return redirect_response
    negocio = negocio_para_request(request)
    if request.method == 'POST':
        form = MascotaForm(request.POST, request.FILES)
        if form.is_valid():
            mascota = form.save(commit=False)
            mascota.propietario = request.user
            mascota.negocio = negocio
            mascota.save()
            messages.success(request, f"{mascota.nombre} fue registrado con exito en {obtener_configuracion_negocio(negocio)['name']}.")
            
            # If user came from booking flow, redirect back to agendar
            if request.GET.get('next') == 'agendar':
                return redirect('agendar_cita')
            return redirect('mis_mascotas')
    else:
        form = MascotaForm()

    context = {
        'form': form,
        'titulo': 'Registrar Nueva Mascota',
    }
    return render(request, 'mascota_form.html', context)


@login_required
def editar_mascota_view(request, mascota_id):
    redirect_response = redirect_si_no_cliente_final(request)
    if redirect_response:
        return redirect_response
    negocio = negocio_para_request(request)
    mascota = get_object_or_404(Mascota, id=mascota_id, propietario=request.user, negocio=negocio)
    if request.method == 'POST':
        form = MascotaForm(request.POST, request.FILES, instance=mascota)
        if form.is_valid():
            form.save()
            messages.success(request, f"Perfil de {mascota.nombre} actualizado.")
            return redirect('mis_mascotas')
    else:
        form = MascotaForm(instance=mascota)

    context = {
        'form': form,
        'mascota': mascota,
        'titulo': f'Editar a {mascota.nombre}',
    }
    return render(request, 'mascota_form.html', context)


@login_required
@require_POST
def eliminar_mascota_view(request, mascota_id):
    redirect_response = redirect_si_no_cliente_final(request)
    if redirect_response:
        return redirect_response
    negocio = negocio_para_request(request)
    mascota = get_object_or_404(Mascota, id=mascota_id, propietario=request.user, negocio=negocio)
    nombre = mascota.nombre
    mascota.delete()
    messages.info(request, f"El registro de {nombre} fue eliminado.")
    return redirect('mis_mascotas')


# Staff / Admin Panel View
@login_required
def gestion_admin_view(request):
    if request.user.is_superuser:
        messages.info(request, "La administracion del sistema se gestiona desde Cuentas y Django Admin.")
        return redirect('cuentas_admin')
    if not es_personal_local(request.user):
        messages.error(request, "Acceso restringido al personal autorizado del local.")
        return redirect('home')
    negocio, redirect_response = negocio_admin_o_redirect(request)
    if redirect_response:
        return redirect_response

    estado_filtro = request.GET.get('estado', 'TODOS')
    citas_base = Cita.objects.select_related('sucursal', 'propietario', 'mascota', 'servicio').filter(negocio=negocio)
    if estado_filtro and estado_filtro != 'TODOS':
        citas_queryset = citas_base.filter(estado=estado_filtro).order_by('-fecha', '-hora')
    else:
        citas_queryset = citas_base.order_by('-fecha', '-hora')

    sucursal_filtro = request.GET.get('sucursal', 'TODAS')
    if sucursal_filtro and sucursal_filtro != 'TODAS' and sucursal_filtro.isdigit():
        citas_queryset = citas_queryset.filter(sucursal_id=sucursal_filtro)
    citas = Paginator(citas_queryset, 50).get_page(request.GET.get('page'))

    servicios = Servicio.objects.filter(negocio=negocio).only('nombre', 'categoria', 'precio', 'duracion_minutos', 'activo')
    sucursales = Sucursal.objects.filter(negocio=negocio, activa=True).only('nombre', 'ciudad')
    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)
    
    resumen_campos = {
        'total': Count('id'),
        'pendientes': Count('id', filter=Q(estado='PENDIENTE')),
        'confirmadas': Count('id', filter=Q(estado='CONFIRMADA')),
        'atendidas': Count('id', filter=Q(estado='ATENDIDA')),
        'hoy': Count('id', filter=Q(fecha=hoy)),
    }
    if es_admin_local(request.user):
        resumen_campos.update({
            'pagos_pendientes': Count('id', filter=Q(estado_pago__in=['PENDIENTE', 'ABONADO'])),
            'ingresos': Sum('precio_acordado', filter=Q(estado='ATENDIDA')),
            'ingresos_mes': Sum(
                'precio_acordado',
                filter=Q(estado='ATENDIDA', fecha__gte=inicio_mes),
            ),
        })
    resumen = Cita.objects.filter(negocio=negocio).aggregate(**resumen_campos)
    promedio_calificacion = Calificacion.objects.filter(cita__negocio=negocio).aggregate(promedio=Avg('puntuacion'))['promedio'] or 0
    citas_hoy = Cita.objects.select_related('sucursal', 'propietario', 'mascota', 'servicio').filter(negocio=negocio, fecha=hoy).order_by('sucursal__nombre', 'hora')[:settings.ADMIN_TODAY_APPOINTMENTS_LIMIT]
    licencia = estado_licencia(negocio)

    context = {
        'citas': citas,
        'servicios': servicios,
        'sucursales': sucursales,
        'citas_hoy': citas_hoy,
        'estado_filtro': estado_filtro,
        'sucursal_filtro': sucursal_filtro,
        'total_citas': resumen['total'],
        'pendientes': resumen['pendientes'],
        'confirmadas': resumen['confirmadas'],
        'atendidas': resumen['atendidas'],
        'citas_de_hoy': resumen['hoy'],
        'pagos_pendientes': resumen.get('pagos_pendientes', 0),
        'ingresos': resumen.get('ingresos') or 0,
        'ingresos_mes': resumen.get('ingresos_mes') or 0,
        'promedio_calificacion': round(promedio_calificacion, 1),
        'licencia_actual': licencia,
    }
    return render(request, 'gestion.html', context)


@login_required
def configuracion_negocio_view(request):
    redirect_response = redirect_si_no_admin_principal(request)
    if redirect_response:
        return redirect_response
    negocio, redirect_response = negocio_admin_o_redirect(request)
    if redirect_response:
        return redirect_response

    config, _ = ConfiguracionNegocio.objects.get_or_create(
        negocio=negocio,
        defaults={'nombre': negocio.nombre},
    )
    if request.method == 'POST':
        form = ConfiguracionNegocioForm(request.POST, instance=config)
        if form.is_valid():
            config_guardada = form.save(commit=False)
            config_guardada.negocio = negocio
            config_guardada.save()
            negocio.nombre = config_guardada.nombre
            negocio.save(update_fields=['nombre'])
            Sucursal.objects.update_or_create(
                negocio=negocio,
                nombre=f"{negocio.nombre} Principal",
                defaults={
                    'ciudad': config_guardada.ciudad,
                    'direccion': config_guardada.direccion,
                    'telefono': config_guardada.telefono,
                    'activa': True,
                },
            )
            messages.success(request, "Configuracion del negocio actualizada.")
            return redirect('configuracion_negocio')
    else:
        form = ConfiguracionNegocioForm(instance=config)

    field_groups = [
        ('Identidad', ['nombre', 'nombre_corto', 'ciudad', 'pais', 'codigo_pais', 'categoria', 'slogan']),
        ('Pagina publica', ['hero_badge', 'hero_titulo', 'hero_descripcion', 'contacto_titulo', 'contacto_descripcion', 'descripcion_footer', 'etiqueta_resenas', 'etiqueta_ubicacion', 'texto_boton_principal']),
        ('Contacto y operacion', ['email', 'telefono', 'direccion', 'horario', 'moneda', 'simbolo_moneda', 'prefijo_transaccion']),
    ]
    grouped_fields = [
        {
            'title': title,
            'fields': [form[field_name] for field_name in field_names],
        }
        for title, field_names in field_groups
    ]

    return render(request, 'configuracion_negocio.html', {
        'form': form,
        'grouped_fields': grouped_fields,
    })


@login_required
def cuentas_admin_view(request):
    if not es_dueno_petnexo(request.user):
        messages.error(request, "Solo el dueño de PetNexo puede crear cuentas administrativas del sistema.")
        return redirect('gestion_admin')

    if request.method == 'POST':
        form = AdminUsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            negocio = obtener_negocio_usuario(usuario)
            if negocio:
                ConfiguracionNegocio.objects.get_or_create(
                    negocio=negocio,
                    defaults={'nombre': negocio.nombre, 'nombre_corto': negocio.nombre.split()[0]},
                )
                Sucursal.objects.get_or_create(
                    negocio=negocio,
                    nombre=f"{negocio.nombre} Principal",
                    defaults={
                        'ciudad': '',
                        'direccion': '',
                        'telefono': '',
                        'activa': True,
                    },
                )
                plan_base = PlanSuscripcion.objects.filter(activo=True).order_by('precio_mensual', 'nombre').first()
                if plan_base:
                    SuscripcionNegocio.objects.get_or_create(
                        negocio=negocio,
                        defaults={
                            'plan': plan_base,
                            'estado': 'DEMO',
                            'fecha_inicio': timezone.localdate(),
                            'fecha_vencimiento': timezone.localdate() + datetime.timedelta(days=30),
                            'contacto_pago': usuario.email or usuario.username,
                        },
                    )
            messages.success(request, f"Cuenta de administrador local creada para {usuario.get_full_name() or usuario.username}.")
            return redirect('cuentas_admin')
    else:
        form = AdminUsuarioForm()

    usuarios = User.objects.select_related('perfil_cliente').prefetch_related('negocios_administrados').order_by('-is_staff', 'first_name', 'username')
    duenos_petnexo = usuarios.filter(is_superuser=True)
    administradores = usuarios.filter(is_staff=True, is_superuser=False)
    clientes = usuarios.filter(is_staff=False, is_superuser=False)

    return render(request, 'cuentas_admin.html', {
        'form': form,
        'duenos_petnexo': duenos_petnexo,
        'administradores': administradores,
        'clientes': clientes,
    })


@login_required
@require_POST
def eliminar_cuenta_sistema_view(request, user_id):
    if not es_dueno_petnexo(request.user):
        messages.error(request, "Solo el dueño de PetNexo puede eliminar cuentas del sistema.")
        return redirect('gestion_admin')

    usuario = get_object_or_404(User, id=user_id)
    nombre_usuario = usuario.get_full_name() or usuario.username

    if usuario.id == request.user.id:
        messages.error(request, "No puedes eliminar tu propia cuenta desde este panel.")
        return redirect('cuentas_admin')

    if usuario.is_superuser and User.objects.filter(is_superuser=True).count() <= 1:
        messages.error(request, "Debe existir al menos un dueño de PetNexo activo.")
        return redirect('cuentas_admin')

    usuario.delete()
    messages.success(request, f"La cuenta de {nombre_usuario} fue eliminada correctamente.")
    return redirect('cuentas_admin')


@login_required
def suscripcion_negocio_view(request):
    if not es_responsable_suscripcion(request.user):
        messages.error(request, "Solo el administrador del local puede gestionar la suscripcion del negocio.")
        return redirect('gestion_admin')
    negocio, redirect_response = negocio_admin_o_redirect(request)
    if redirect_response:
        return redirect_response

    planes = PlanSuscripcion.objects.filter(activo=True).order_by('precio_mensual', 'nombre')
    plan_base = planes.first()
    suscripcion = SuscripcionNegocio.actual(negocio=negocio)
    if not suscripcion and plan_base:
        suscripcion = SuscripcionNegocio.objects.create(
            negocio=negocio,
            plan=plan_base,
            estado='DEMO',
            fecha_inicio=timezone.localdate(),
            fecha_vencimiento=timezone.localdate() + datetime.timedelta(days=30),
            contacto_pago=request.user.email or request.user.username,
        )

    return render(request, 'suscripcion_negocio.html', {
        'planes': planes,
        'suscripcion': suscripcion,
        'estado': estado_licencia(negocio),
        'tarjeta_configurada': datafast_configurado(),
    })


@login_required
def crear_pago_suscripcion_view(request):
    if not es_responsable_suscripcion(request.user):
        messages.error(request, "Solo el administrador del local puede cambiar la suscripcion del negocio.")
        return redirect('gestion_admin')
    negocio, redirect_response = negocio_admin_o_redirect(request)
    if redirect_response:
        return redirect_response

    if request.method != 'POST':
        return redirect('suscripcion_negocio')

    if settings.SIMULATE_PAYMENTS:
        messages.info(request, "La simulacion de pagos esta disponible para citas. No se inicio Datafast.")
        return redirect('suscripcion_negocio')

    if not datafast_configurado():
        messages.error(request, "Configura las credenciales Datafast de tu cuenta comercial para cobrar suscripciones con tarjeta.")
        return redirect('suscripcion_negocio')

    plan = get_object_or_404(PlanSuscripcion, id=request.POST.get('plan_id'), activo=True)
    ciclo = normalizar_ciclo_facturacion(request.POST.get('ciclo_facturacion', 'MENSUAL'))
    suscripcion = SuscripcionNegocio.actual(negocio=negocio)
    contacto = request.POST.get('contacto_pago', '').strip() or request.user.email or request.user.username
    pago = PagoSuscripcion.objects.create(
        suscripcion=suscripcion,
        plan=plan,
        usuario=request.user,
        ciclo_facturacion=ciclo,
        monto=calcular_monto_suscripcion(plan, ciclo),
        contacto_pago=contacto,
    )

    checkout_id = crear_checkout_suscripcion_datafast(request, pago)
    if not checkout_id:
        pago.estado = 'RECHAZADO'
        pago.referencia = 'No se pudo crear checkout Datafast'
        pago.save(update_fields=['estado', 'referencia', 'actualizado_en'])
        messages.error(request, "No se pudo iniciar el pago seguro con tarjeta. Revisa tus credenciales Datafast.")
        return redirect('suscripcion_negocio')

    pago.checkout_id = checkout_id
    pago.save(update_fields=['checkout_id', 'actualizado_en'])
    return redirect('datafast_suscripcion_widget', pago_id=pago.id)


@login_required
def datafast_suscripcion_widget_view(request, pago_id):
    if not es_responsable_suscripcion(request.user):
        messages.error(request, "Solo el administrador del local puede pagar la suscripcion del negocio.")
        return redirect('gestion_admin')
    negocio, redirect_response = negocio_admin_o_redirect(request)
    if redirect_response:
        return redirect_response

    if settings.SIMULATE_PAYMENTS:
        messages.info(request, "La simulacion de pagos esta activa. No se inicio Datafast.")
        return redirect('suscripcion_negocio')

    pago = get_object_or_404(
        PagoSuscripcion.objects.select_related('plan', 'suscripcion__negocio'),
        id=pago_id,
        usuario=request.user,
        suscripcion__negocio=negocio,
    )
    if not pago.checkout_id:
        messages.error(request, "Primero inicia el pago de la suscripcion.")
        return redirect('suscripcion_negocio')

    return render(request, 'datafast_suscripcion_widget.html', {
        'pago': pago,
        'datafast_base_url': settings.DATAFAST_BASE_URL,
        'datafast_brands': settings.DATAFAST_BRANDS,
    })


@login_required
def datafast_suscripcion_result_view(request, pago_id):
    if not es_responsable_suscripcion(request.user):
        messages.error(request, "Solo el administrador del local puede verificar pagos de suscripcion.")
        return redirect('gestion_admin')
    negocio, redirect_response = negocio_admin_o_redirect(request)
    if redirect_response:
        return redirect_response

    if settings.SIMULATE_PAYMENTS:
        messages.info(request, "La simulacion de pagos esta activa. No se verifico Datafast.")
        return redirect('suscripcion_negocio')

    pago = get_object_or_404(
        PagoSuscripcion.objects.select_related('plan', 'suscripcion__negocio'),
        id=pago_id,
        usuario=request.user,
        suscripcion__negocio=negocio,
    )
    resource_path = request.GET.get('resourcePath', '')
    if (
        not pago.checkout_id
        or not re.fullmatch(r'/v1/checkouts/[A-Za-z0-9._/-]+', resource_path)
        or resource_path.rsplit('/', 1)[-1] != pago.checkout_id
    ):
        messages.error(request, "No se recibio la respuesta del pago.")
        return redirect('suscripcion_negocio')

    if pago.estado == 'APROBADO':
        messages.info(request, "Este pago ya fue aprobado.")
        return redirect('suscripcion_negocio')

    url = f"{settings.DATAFAST_BASE_URL}{resource_path}"
    params = {'entityId': settings.DATAFAST_ENTITY_ID}
    headers = {'Authorization': f"Bearer {settings.DATAFAST_AUTHORIZATION}"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=(3.05, settings.DATAFAST_TIMEOUT_SECONDS))
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        messages.error(request, "No se pudo verificar el pago con Datafast.")
        return redirect('suscripcion_negocio')

    expected_transaction = f"{obtener_configuracion_negocio(negocio)['transaction_prefix']}-SUB-{pago.id}"
    if not datafast_payload_valido(payload, expected_transaction, pago.monto):
        logger.warning('Respuesta Datafast no coincide con el pago de suscripcion %s.', pago.id)
        messages.error(request, 'La respuesta del pago no coincide con esta suscripcion.')
        return redirect('suscripcion_negocio')

    result_code = payload.get('result', {}).get('code', '')
    with transaction.atomic():
        pago_bloqueado = PagoSuscripcion.objects.select_for_update().select_related('plan', 'suscripcion').get(pk=pago.pk)
        if pago_bloqueado.estado == 'APROBADO':
            messages.info(request, 'Este pago ya fue aprobado.')
            return redirect('suscripcion_negocio')
        pago_bloqueado.datafast_resource_path = resource_path
        pago_bloqueado.datafast_result_code = result_code
        pago_bloqueado.referencia = payload.get('id', '')
        if DATAFAST_RESULT_OK_PATTERN.match(result_code):
            hoy = timezone.localdate()
            dias = 365 if pago_bloqueado.ciclo_facturacion == 'ANUAL' else 30
            suscripcion = pago_bloqueado.suscripcion or SuscripcionNegocio.actual(negocio=negocio)
            if suscripcion:
                suscripcion.plan = pago_bloqueado.plan
                suscripcion.estado = 'ACTIVA'
                suscripcion.fecha_inicio = hoy
                suscripcion.fecha_vencimiento = hoy + datetime.timedelta(days=dias)
                suscripcion.contacto_pago = pago_bloqueado.contacto_pago
                suscripcion.notas = f"Pago Datafast aprobado: {pago_bloqueado.referencia}"
                suscripcion.save()
            pago_bloqueado.estado = 'APROBADO'
            messages.success(request, "Pago aprobado. Tu plan PetNexo fue actualizado correctamente.")
        else:
            pago_bloqueado.estado = 'RECHAZADO'
            messages.error(request, f"Pago no aprobado. Codigo Datafast: {result_code}")
        pago_bloqueado.save(update_fields=[
            'datafast_resource_path', 'datafast_result_code', 'referencia',
            'estado', 'actualizado_en',
        ])
    return redirect('suscripcion_negocio')


@login_required
@require_POST
def cambiar_estado_cita_view(request, cita_id):
    redirect_response = redirect_si_no_admin_local(request)
    if redirect_response:
        return redirect_response
    negocio, redirect_response = negocio_admin_o_redirect(request)
    if redirect_response:
        return redirect_response
    if licencia_bloqueada_para_operar(request.user):
        messages.error(request, estado_licencia(negocio)['mensaje'])
        return redirect('gestion_admin')

    cita = get_object_or_404(
        Cita.objects.select_related('mascota', 'sucursal', 'servicio', 'propietario'),
        id=cita_id,
        negocio=negocio,
    )
    nuevo_estado = request.POST.get('nuevo_estado')
    if nuevo_estado in ['PENDIENTE', 'CONFIRMADA', 'ATENDIDA', 'CANCELADA']:
        cita.estado = nuevo_estado
        cita.save(update_fields=['estado'])
        enviar_notificacion(
            f"Estado de cita actualizado: {cita.get_estado_display()}",
            f"La cita de {cita.mascota.nombre} en {cita.sucursal.nombre} para {cita.servicio.nombre} ahora esta en estado: {cita.get_estado_display()}.",
            [cita.propietario.email],
        )
        messages.success(request, f"Estado de cita #{cita.id} actualizado a '{cita.get_estado_display()}'.")
    
    return redirect('gestion_admin')


@login_required
@require_POST
def actualizar_pago_cita_view(request, cita_id):
    redirect_response = redirect_si_no_admin_principal(request)
    if redirect_response:
        return redirect_response
    negocio, redirect_response = negocio_admin_o_redirect(request)
    if redirect_response:
        return redirect_response
    if licencia_bloqueada_para_operar(request.user):
        messages.error(request, estado_licencia(negocio)['mensaje'])
        return redirect('gestion_admin')

    cita = get_object_or_404(Cita, id=cita_id, negocio=negocio)
    estado_pago = request.POST.get('estado_pago')
    metodo_pago = request.POST.get('metodo_pago')
    estados_validos = dict(Cita._meta.get_field('estado_pago').choices)
    metodos_validos = dict(Cita._meta.get_field('metodo_pago').choices)

    if estado_pago in estados_validos and metodo_pago in metodos_validos:
        cita.estado_pago = estado_pago
        cita.metodo_pago = metodo_pago
        cita.save(update_fields=['estado_pago', 'metodo_pago'])
        messages.success(request, f"Pago de cita #{cita.id} actualizado.")
    else:
        messages.error(request, "Datos de pago inválidos.")

    return redirect('gestion_admin')


@login_required
@require_POST
def actualizar_seguimiento_cita_view(request, cita_id):
    redirect_response = redirect_si_no_admin_local(request)
    if redirect_response:
        return redirect_response
    negocio, redirect_response = negocio_admin_o_redirect(request)
    if redirect_response:
        return redirect_response
    if licencia_bloqueada_para_operar(request.user):
        messages.error(request, estado_licencia(negocio)['mensaje'])
        return redirect('gestion_admin')

    cita = get_object_or_404(
        Cita.objects.select_related('mascota', 'propietario'),
        id=cita_id,
        negocio=negocio,
    )
    etapa = request.POST.get('etapa_seguimiento')
    nota = request.POST.get('nota_seguimiento', '').strip()

    etapas_validas = dict(Cita.ETAPAS_SEGUIMIENTO)
    if etapa in etapas_validas:
        cita.etapa_seguimiento = etapa
        cita.progreso = PROGRESO_POR_ETAPA.get(etapa, cita.progreso)
        cita.nota_seguimiento = nota
        if etapa == 'ENTREGADA':
            cita.estado = 'ATENDIDA'
        update_fields = [
            'etapa_seguimiento',
            'progreso',
            'nota_seguimiento',
            'actualizado_seguimiento',
        ]
        if etapa == 'ENTREGADA':
            update_fields.append('estado')
        cita.save(update_fields=update_fields)
        enviar_notificacion(
            f"Seguimiento actualizado: {cita.mascota.nombre}",
            f"Etapa actual: {etapas_validas[etapa]}. Nota: {nota or 'Sin nota adicional.'}",
            [cita.propietario.email],
        )
        messages.success(request, f"Seguimiento de {cita.mascota.nombre} actualizado: {etapas_validas[etapa]}.")
    else:
        messages.error(request, "La etapa seleccionada no es válida.")

    return redirect('gestion_admin')


@login_required
def servicio_form_view(request, servicio_id=None):
    redirect_response = redirect_si_no_admin_principal(request)
    if redirect_response:
        return redirect_response
    negocio, redirect_response = negocio_admin_o_redirect(request)
    if redirect_response:
        return redirect_response
    if licencia_bloqueada_para_operar(request.user):
        messages.error(request, estado_licencia(negocio)['mensaje'])
        return redirect('gestion_admin')

    servicio = get_object_or_404(Servicio, id=servicio_id, negocio=negocio) if servicio_id else None
    if request.method == 'POST':
        form = ServicioForm(request.POST, instance=servicio)
        if form.is_valid():
            servicio_guardado = form.save(commit=False)
            servicio_guardado.negocio = negocio
            servicio_guardado.save()
            accion = 'actualizado' if servicio else 'creado'
            messages.success(request, f"Servicio {servicio_guardado.nombre} {accion} correctamente.")
            return redirect('gestion_admin')
    else:
        form = ServicioForm(instance=servicio)

    return render(request, 'servicio_form.html', {
        'form': form,
        'servicio': servicio,
    })


@login_required
@require_POST
def toggle_servicio_view(request, servicio_id):
    redirect_response = redirect_si_no_admin_principal(request)
    if redirect_response:
        return redirect_response
    negocio, redirect_response = negocio_admin_o_redirect(request)
    if redirect_response:
        return redirect_response
    if licencia_bloqueada_para_operar(request.user):
        messages.error(request, estado_licencia(negocio)['mensaje'])
        return redirect('gestion_admin')

    servicio = get_object_or_404(Servicio, id=servicio_id, negocio=negocio)
    servicio.activo = not servicio.activo
    servicio.save()
    messages.info(request, f"Estado de {servicio.nombre} actualizado a {'Activo' if servicio.activo else 'Inactivo'}.")
    return redirect('gestion_admin')


@login_required
def sucursal_form_view(request, sucursal_id=None):
    redirect_response = redirect_si_no_admin_principal(request)
    if redirect_response:
        return redirect_response
    negocio, redirect_response = negocio_admin_o_redirect(request)
    if redirect_response:
        return redirect_response
    if licencia_bloqueada_para_operar(request.user):
        messages.error(request, estado_licencia(negocio)['mensaje'])
        return redirect('gestion_admin')

    sucursal = get_object_or_404(Sucursal, id=sucursal_id, negocio=negocio) if sucursal_id else None
    if request.method == 'POST':
        form = SucursalForm(request.POST, instance=sucursal)
        if form.is_valid():
            sucursal_guardada = form.save(commit=False)
            sucursal_guardada.negocio = negocio
            sucursal_guardada.save()
            accion = 'actualizada' if sucursal else 'creada'
            messages.success(request, f"Sucursal {sucursal_guardada.nombre} {accion} correctamente.")
            return redirect('gestion_admin')
    else:
        form = SucursalForm(instance=sucursal)

    return render(request, 'sucursal_form.html', {
        'form': form,
        'sucursal': sucursal,
    })


# Auth Views
def registro_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        if rate_limit_exceeded(request, 'registro', limit=5, window_seconds=900):
            messages.error(request, 'Has realizado varios intentos de registro. Espera unos minutos e intentalo nuevamente.')
            return redirect('registro')
        form = RegistroForm(request.POST)
        if form.is_valid():
            negocio = negocio_para_request(request)
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            PerfilCliente.objects.create(
                usuario=user,
                negocio=negocio,
                telefono=form.cleaned_data.get('telefono', ''),
                direccion=form.cleaned_data.get('direccion', ''),
            )
            login(request, user)
            messages.success(request, f"Bienvenido a {obtener_configuracion_negocio(negocio)['name']}, {user.first_name or user.username}.")
            return redirect('home')
    else:
        form = RegistroForm()

    return render(request, 'registro.html', {'form': form})


def login_usuario_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        if rate_limit_exceeded(request, 'login', limit=10, window_seconds=600):
            messages.error(request, 'Demasiados intentos de inicio de sesión. Espera unos minutos e inténtalo nuevamente.')
            return redirect('login')
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Hola de nuevo, {user.first_name or user.username}.")
                next_page = request.GET.get('next', 'home')
                if not url_has_allowed_host_and_scheme(
                    url=next_page,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    next_page = 'home'
                if next_page == 'home' and user.is_superuser:
                    return redirect('cuentas_admin')
                if next_page == 'home' and es_personal_local(user):
                    return redirect('gestion_admin')
                return redirect(next_page)
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})


def solicitar_codigo_recuperacion_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        if rate_limit_exceeded(request, 'password-reset', limit=5, window_seconds=900):
            messages.error(request, 'Has solicitado varios códigos. Espera unos minutos antes de intentarlo nuevamente.')
            return redirect('password_reset')
        form = SolicitarCodigoRecuperacionForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            users = list(User.objects.filter(email__iexact=email, is_active=True).order_by('id')[:2])
            user = users[0] if len(users) == 1 else None
            ahora = timezone.now()

            if user:
                ultimo = (
                    CodigoRecuperacionContrasena.objects.filter(
                        usuario=user,
                        usado_en__isnull=True,
                        expira_en__gt=ahora,
                    )
                    .order_by('-creado_en')
                    .first()
                )
                espera = datetime.timedelta(seconds=settings.PASSWORD_RESET_CODE_RESEND_SECONDS)
                codigo = None
                if ultimo and ultimo.creado_en >= ahora - espera:
                    registro = ultimo
                else:
                    CodigoRecuperacionContrasena.objects.filter(
                        usuario=user,
                        usado_en__isnull=True,
                    ).update(usado_en=ahora)
                    codigo = f"{secrets.randbelow(1_000_000):06d}"
                    registro = CodigoRecuperacionContrasena.objects.create(
                        usuario=user,
                        codigo_hash=make_password(codigo),
                        expira_en=ahora + datetime.timedelta(minutes=settings.PASSWORD_RESET_CODE_TTL_MINUTES),
                    )

                request.session['password_reset_code_id'] = registro.id
                request.session['password_reset_user_id'] = user.id
                request.session.pop('password_reset_verified_until', None)

                if codigo:
                    try:
                        send_mail(
                            subject=f"Codigo de recuperacion de {settings.APP_NAME}",
                            message=render_to_string(
                                'password_reset_email.html',
                                {
                                    'codigo': codigo,
                                    'minutos': settings.PASSWORD_RESET_CODE_TTL_MINUTES,
                                    'site_name': settings.APP_NAME,
                                },
                            ),
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[user.email],
                            fail_silently=False,
                        )
                    except Exception:
                        logger.exception("No se pudo enviar el codigo de recuperacion.")

            # Do not reveal whether a specific email has an account.
            return redirect('password_reset_verify')
    else:
        form = SolicitarCodigoRecuperacionForm()

    return render(request, 'password_reset.html', {'form': form})


def verificar_codigo_recuperacion_view(request):
    codigo_id = request.session.get('password_reset_code_id')
    user_id = request.session.get('password_reset_user_id')
    registro = None
    if codigo_id and user_id:
        registro = CodigoRecuperacionContrasena.objects.filter(
            id=codigo_id,
            usuario_id=user_id,
        ).first()

    if request.method == 'POST':
        form = VerificarCodigoRecuperacionForm(request.POST)
        if form.is_valid():
            if not registro or not registro.esta_vigente:
                messages.error(request, "El codigo expiro o ya fue utilizado. Solicita uno nuevo.")
                return redirect('password_reset')

            if registro.intentos >= settings.PASSWORD_RESET_CODE_MAX_ATTEMPTS:
                registro.usado_en = timezone.now()
                registro.save(update_fields=['usado_en'])
                messages.error(request, "Superaste el numero de intentos. Solicita un codigo nuevo.")
                return redirect('password_reset')

            if not check_password(form.cleaned_data['codigo'], registro.codigo_hash):
                registro.intentos += 1
                registro.save(update_fields=['intentos'])
                restantes = settings.PASSWORD_RESET_CODE_MAX_ATTEMPTS - registro.intentos
                if restantes <= 0:
                    registro.usado_en = timezone.now()
                    registro.save(update_fields=['intentos', 'usado_en'])
                    messages.error(request, "Superaste el numero de intentos. Solicita un codigo nuevo.")
                    return redirect('password_reset')
                form.add_error('codigo', f"Codigo incorrecto. Te quedan {restantes} intentos.")
            else:
                registro.usado_en = timezone.now()
                registro.save(update_fields=['usado_en'])
                request.session.cycle_key()
                request.session['password_reset_verified_user_id'] = user_id
                request.session['password_reset_verified_until'] = (
                    timezone.now().timestamp() + settings.PASSWORD_RESET_CODE_TTL_MINUTES * 60
                )
                request.session.pop('password_reset_code_id', None)
                request.session.pop('password_reset_user_id', None)
                return redirect('password_reset_confirm')
    else:
        form = VerificarCodigoRecuperacionForm()

    return render(
        request,
        'password_reset_verify.html',
        {
            'form': form,
            'codigo_activo': bool(registro and registro.esta_vigente),
            'minutos': settings.PASSWORD_RESET_CODE_TTL_MINUTES,
        },
    )


def establecer_nueva_contrasena_view(request):
    user_id = request.session.get('password_reset_verified_user_id')
    try:
        verificado_hasta = float(request.session.get('password_reset_verified_until', 0))
    except (TypeError, ValueError):
        verificado_hasta = 0
    if not user_id or verificado_hasta < timezone.now().timestamp():
        request.session.pop('password_reset_verified_user_id', None)
        request.session.pop('password_reset_verified_until', None)
        messages.error(request, "Primero verifica el codigo enviado a tu correo.")
        return redirect('password_reset')

    user = get_object_or_404(User, id=user_id, is_active=True)
    if request.method == 'POST':
        form = NuevaContrasenaRecuperacionForm(user, request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['nueva_contrasena'])
            user.save(update_fields=['password'])
            request.session.pop('password_reset_verified_user_id', None)
            request.session.pop('password_reset_verified_until', None)
            messages.success(request, "Tu contrasena fue actualizada. Ya puedes iniciar sesion.")
            return redirect('password_reset_complete')
    else:
        form = NuevaContrasenaRecuperacionForm(user)

    return render(request, 'password_reset_confirm.html', {'form': form})


def recuperacion_completada_view(request):
    return render(request, 'password_reset_complete.html')


def logout_usuario_view(request):
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('home')
