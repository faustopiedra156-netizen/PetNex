import re
import datetime
from decimal import Decimal, ROUND_HALF_UP

import requests
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import connection, DatabaseError, OperationalError, ProgrammingError
from django.db.models import Sum, Count, Q, Avg
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Servicio, Mascota, PerfilCliente, Cita, Calificacion, ConfiguracionNegocio, Sucursal, PlanSuscripcion, SuscripcionNegocio, PagoSuscripcion, Negocio
from .forms import MascotaForm, PerfilClienteForm, CitaForm, CalificacionForm, RegistroForm, ConfiguracionNegocioForm, ServicioForm, AdminUsuarioForm
from .services import obtener_configuracion_negocio, obtener_negocio_usuario, obtener_negocio_publico, enviar_notificacion, estado_licencia

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


def es_staff(user):
    return user.is_staff or user.is_superuser


def es_dueno_petnexo(user):
    return user.is_authenticated and user.is_superuser


def es_admin_local(user):
    return user.is_authenticated and user.is_staff and not user.is_superuser


def es_responsable_suscripcion(user):
    return es_admin_local(user)


def negocio_para_request(request):
    if request.user.is_authenticated:
        negocio = obtener_negocio_usuario(request.user)
        if negocio:
            return negocio
    return obtener_negocio_publico()


def negocio_admin_o_redirect(request):
    negocio = obtener_negocio_usuario(request.user)
    if negocio:
        return negocio, None
    if request.user.is_superuser:
        negocio = obtener_negocio_publico()
        return negocio, None
    messages.error(request, "Tu cuenta administrativa aun no tiene un negocio asignado.")
    return None, redirect('home')


def redirect_si_no_staff(request):
    if es_staff(request.user):
        return None
    messages.error(request, "Acceso no autorizado.")
    return redirect('home')


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
        checks['error'] = str(exc)
        status = 503
    return JsonResponse(checks, status=status)


def home_view(request):
    negocio = negocio_para_request(request)
    try:
        servicios_destacados = Servicio.objects.filter(negocio=negocio, activo=True, destacado=True).only(
            'nombre', 'descripcion', 'precio', 'duracion_minutos', 'icono'
        )[:settings.HOME_FEATURED_SERVICES_LIMIT]
        servicios_todos = Servicio.objects.filter(negocio=negocio, activo=True).only(
            'nombre', 'descripcion', 'precio', 'duracion_minutos', 'icono'
        )[:settings.HOME_SERVICES_LIMIT]
        mascotas_atendidas = Cita.objects.filter(negocio=negocio, estado='ATENDIDA').values('mascota_id').distinct().count()
        total_citas_operativas = Cita.objects.filter(negocio=negocio).exclude(estado='CANCELADA').count()
        citas_atendidas = Cita.objects.filter(negocio=negocio, estado='ATENDIDA').count()
        tasa_atencion = round((citas_atendidas / total_citas_operativas) * 100) if total_citas_operativas else 0
        resumen_resenas = Calificacion.objects.filter(cita__negocio=negocio).aggregate(promedio=Avg('puntuacion'), total=Count('id'))
        promedio_resenas = resumen_resenas['promedio'] or 0
        total_resenas = resumen_resenas['total']
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
    if request.method == 'POST':
        messages.success(request, "Mensaje recibido. Te responderemos por WhatsApp o correo lo antes posible.")
        return redirect('contacto')
    return render(request, 'contacto.html')


def chatbot_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Metodo no permitido.'}, status=405)

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
        respuesta = f"Nuestro horario de atencion es: {negocio['opening_hours']}. En la agenda veras solo horarios disponibles por sucursal."
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
            "Prueba escribiendo: quiero agendar una cita, cuanto cuesta un baño, o como va mi mascota."
        )

    return JsonResponse({'respuesta': respuesta})


@login_required
def disponibilidad_horarios_view(request):
    negocio = negocio_para_request(request)
    sucursal_id = request.GET.get('sucursal')
    fecha = request.GET.get('fecha')
    if not sucursal_id or not fecha:
        return JsonResponse({'horarios': []})

    try:
        fecha_obj = datetime.date.fromisoformat(fecha)
    except ValueError:
        return JsonResponse({'horarios': []}, status=400)

    ocupadas = set(
        Cita.objects.filter(
            negocio=negocio,
            sucursal_id=sucursal_id,
            fecha=fecha_obj,
        ).exclude(estado='CANCELADA').values_list('hora', flat=True)
    )
    horarios = [
        {
            'hora': hora.strftime('%H:%M'),
            'ocupado': hora in ocupadas,
        }
        for hora in generar_horarios_disponibilidad()
    ]
    return JsonResponse({'horarios': horarios})


@login_required
def agendar_cita_view(request):
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
    mascotas_usuario = Mascota.objects.filter(propietario=request.user).only('nombre', 'raza')
    if not mascotas_usuario.exists():
        messages.info(request, "Primero registra a tu mascota para poder agendar una cita de peluquería.")
        return redirect('nueva_mascota')

    if request.method == 'POST':
        form = CitaForm(request.user, request.POST, negocio=negocio)
        if form.is_valid():
            cita = form.save(commit=False)
            cita.negocio = negocio
            cita.propietario = request.user
            cita.save()
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
    citas = Cita.objects.select_related('sucursal', 'mascota', 'servicio', 'calificacion').filter(propietario=request.user).order_by('-fecha', '-hora')
    context = {
        'citas': citas,
    }
    return render(request, 'mis_citas.html', context)


@login_required
def calificar_cita_view(request, cita_id):
    cita = get_object_or_404(
        Cita.objects.select_related('mascota', 'servicio'),
        id=cita_id,
        propietario=request.user,
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
    cita = get_object_or_404(Cita, id=cita_id, propietario=request.user)
    if cita.estado in ESTADOS_EDITABLES_CLIENTE:
        cita.estado = 'CANCELADA'
        cita.save()
        messages.warning(request, f"La cita para {cita.mascota.nombre} ha sido cancelada.")
    else:
        messages.error(request, "Esta cita no se puede cancelar.")
    return redirect('mis_citas')


@login_required
def pagar_cita_view(request, cita_id):
    negocio = negocio_para_request(request)
    licencia = estado_licencia(negocio)
    if not licencia['activa'] and not request.user.is_superuser:
        messages.error(request, licencia['mensaje'])
        return redirect('mis_citas')
    if licencia['suscripcion'] and not licencia['suscripcion'].plan.permite_pagos and not request.user.is_superuser:
        messages.error(request, "Tu plan actual de PetNexo no incluye gestion de pagos.")
        return redirect('mis_citas')

    cita = get_object_or_404(Cita, id=cita_id, negocio=negocio, propietario=request.user)
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
            cita.save()
            messages.success(request, f"Transferencia registrada. {obtener_configuracion_negocio(cita.negocio)['name']} confirmara el pago en el panel administrativo.")
            return redirect('mis_citas')

        if metodo_pago == 'EFECTIVO':
            cita.metodo_pago = 'EFECTIVO'
            cita.estado_pago = 'PENDIENTE'
            cita.referencia_pago = 'Pago en local'
            cita.save()
            messages.info(request, "Tu cita quedó marcada para pago físico en el local.")
            return redirect('mis_citas')

        if metodo_pago == 'TARJETA':
            if not datafast_configurado():
                messages.error(request, "El pago con tarjeta aún no tiene credenciales Datafast configuradas.")
                return redirect('pagar_cita', cita_id=cita.id)

            checkout_id = crear_checkout_datafast(request, cita)
            if checkout_id:
                cita.metodo_pago = 'TARJETA'
                cita.datafast_checkout_id = checkout_id
                cita.save()
                return redirect('datafast_widget', cita_id=cita.id)

            messages.error(request, "No se pudo iniciar el pago con tarjeta. Intenta nuevamente.")
            return redirect('pagar_cita', cita_id=cita.id)

        messages.error(request, "Selecciona un método de pago válido.")

    return render(request, 'pagar_cita.html', {
        'cita': cita,
        'transferencia': transferencia,
        'tarjeta_configurada': datafast_configurado(),
    })


def crear_checkout_datafast(request, cita):
    url = f"{settings.DATAFAST_BASE_URL}/v1/checkouts"
    user = request.user
    negocio = obtener_configuracion_negocio(cita.negocio)
    amount = f"{float(cita.servicio.precio):.2f}"
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
        response = requests.post(url, data=data, headers=headers, timeout=settings.DATAFAST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json().get('id')
    except requests.RequestException:
        return None


def calcular_monto_suscripcion(plan, ciclo_facturacion):
    if ciclo_facturacion == 'ANUAL':
        return (plan.precio_mensual * Decimal('12') * Decimal('0.85')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return plan.precio_mensual.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def normalizar_ciclo_facturacion(valor):
    return 'ANUAL' if str(valor).strip().upper() == 'ANUAL' else 'MENSUAL'


def crear_checkout_suscripcion_datafast(request, pago):
    url = f"{settings.DATAFAST_BASE_URL}/v1/checkouts"
    user = request.user
    negocio = obtener_configuracion_negocio()
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
        response = requests.post(url, data=data, headers=headers, timeout=settings.DATAFAST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json().get('id')
    except requests.RequestException:
        return None


@login_required
def datafast_widget_view(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id, negocio=negocio_para_request(request), propietario=request.user)
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
    cita = get_object_or_404(Cita, id=cita_id, negocio=negocio_para_request(request), propietario=request.user)
    resource_path = request.GET.get('resourcePath', '')
    if not resource_path:
        messages.error(request, "No se recibió la respuesta del pago.")
        return redirect('mis_citas')

    url = f"{settings.DATAFAST_BASE_URL}{resource_path}"
    params = {'entityId': settings.DATAFAST_ENTITY_ID}
    headers = {'Authorization': f"Bearer {settings.DATAFAST_AUTHORIZATION}"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=settings.DATAFAST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        messages.error(request, "No se pudo verificar el pago con Datafast.")
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

    cita.save()
    return redirect('mis_citas')


@login_required
def mis_mascotas_view(request):
    mascotas = Mascota.objects.filter(propietario=request.user).only(
        'nombre', 'especie', 'raza', 'edad', 'peso_kg', 'notas_medicas', 'foto_url'
    )
    context = {
        'mascotas': mascotas,
    }
    return render(request, 'mascotas.html', context)


@login_required
def perfil_cliente_view(request):
    perfil, _ = PerfilCliente.objects.get_or_create(usuario=request.user)
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
    negocio = negocio_para_request(request)
    if request.method == 'POST':
        form = MascotaForm(request.POST)
        if form.is_valid():
            mascota = form.save(commit=False)
            mascota.propietario = request.user
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
    mascota = get_object_or_404(Mascota, id=mascota_id, propietario=request.user)
    if request.method == 'POST':
        form = MascotaForm(request.POST, instance=mascota)
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
    mascota = get_object_or_404(Mascota, id=mascota_id, propietario=request.user)
    nombre = mascota.nombre
    mascota.delete()
    messages.info(request, f"El registro de {nombre} fue eliminado.")
    return redirect('mis_mascotas')


# Staff / Admin Panel View
@login_required
def gestion_admin_view(request):
    if not es_staff(request.user):
        messages.error(request, "Acceso restringido a administradores.")
        return redirect('home')
    negocio, redirect_response = negocio_admin_o_redirect(request)
    if redirect_response:
        return redirect_response

    estado_filtro = request.GET.get('estado', 'TODOS')
    citas_base = Cita.objects.select_related('sucursal', 'propietario', 'mascota', 'servicio').filter(negocio=negocio)
    if estado_filtro and estado_filtro != 'TODOS':
        citas = citas_base.filter(estado=estado_filtro).order_by('-fecha', '-hora')
    else:
        citas = citas_base.order_by('-fecha', '-hora')

    sucursal_filtro = request.GET.get('sucursal', 'TODAS')
    if sucursal_filtro and sucursal_filtro != 'TODAS' and sucursal_filtro.isdigit():
        citas = citas.filter(sucursal_id=sucursal_filtro)

    servicios = Servicio.objects.filter(negocio=negocio).only('nombre', 'categoria', 'precio', 'duracion_minutos', 'activo')
    sucursales = Sucursal.objects.filter(negocio=negocio, activa=True).only('nombre', 'ciudad')
    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)
    
    resumen = Cita.objects.filter(negocio=negocio).aggregate(
        total=Count('id'),
        pendientes=Count('id', filter=Q(estado='PENDIENTE')),
        confirmadas=Count('id', filter=Q(estado='CONFIRMADA')),
        atendidas=Count('id', filter=Q(estado='ATENDIDA')),
        hoy=Count('id', filter=Q(fecha=hoy)),
        pagos_pendientes=Count('id', filter=Q(estado_pago__in=['PENDIENTE', 'ABONADO'])),
    )
    ingresos = Cita.objects.filter(negocio=negocio, estado='ATENDIDA').aggregate(total=Sum('servicio__precio'))['total'] or 0
    ingresos_mes = Cita.objects.filter(negocio=negocio, estado='ATENDIDA', fecha__gte=inicio_mes).aggregate(total=Sum('servicio__precio'))['total'] or 0
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
        'pagos_pendientes': resumen['pagos_pendientes'],
        'ingresos': ingresos,
        'ingresos_mes': ingresos_mes,
        'promedio_calificacion': round(promedio_calificacion, 1),
        'licencia_actual': licencia,
    }
    return render(request, 'gestion.html', context)


@login_required
def configuracion_negocio_view(request):
    redirect_response = redirect_si_no_staff(request)
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

    pago = get_object_or_404(PagoSuscripcion, id=pago_id, usuario=request.user, suscripcion__negocio=negocio)
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

    pago = get_object_or_404(PagoSuscripcion, id=pago_id, usuario=request.user, suscripcion__negocio=negocio)
    resource_path = request.GET.get('resourcePath', '')
    if not resource_path:
        messages.error(request, "No se recibio la respuesta del pago.")
        return redirect('suscripcion_negocio')

    url = f"{settings.DATAFAST_BASE_URL}{resource_path}"
    params = {'entityId': settings.DATAFAST_ENTITY_ID}
    headers = {'Authorization': f"Bearer {settings.DATAFAST_AUTHORIZATION}"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=settings.DATAFAST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        messages.error(request, "No se pudo verificar el pago con Datafast.")
        return redirect('suscripcion_negocio')

    result_code = payload.get('result', {}).get('code', '')
    pago.datafast_resource_path = resource_path
    pago.datafast_result_code = result_code
    pago.referencia = payload.get('id', '')

    if DATAFAST_RESULT_OK_PATTERN.match(result_code):
        hoy = timezone.localdate()
        dias = 365 if pago.ciclo_facturacion == 'ANUAL' else 30
        suscripcion = pago.suscripcion or SuscripcionNegocio.actual(negocio=negocio)
        if suscripcion:
            suscripcion.plan = pago.plan
            suscripcion.estado = 'ACTIVA'
            suscripcion.fecha_inicio = hoy
            suscripcion.fecha_vencimiento = hoy + datetime.timedelta(days=dias)
            suscripcion.contacto_pago = pago.contacto_pago
            suscripcion.notas = f"Pago Datafast aprobado: {pago.referencia}"
            suscripcion.save()
        pago.estado = 'APROBADO'
        messages.success(request, "Pago aprobado. Tu plan PetNexo fue actualizado correctamente.")
    else:
        pago.estado = 'RECHAZADO'
        messages.error(request, f"Pago no aprobado. Codigo Datafast: {result_code}")

    pago.save()
    return redirect('suscripcion_negocio')


@login_required
@require_POST
def cambiar_estado_cita_view(request, cita_id):
    redirect_response = redirect_si_no_staff(request)
    if redirect_response:
        return redirect_response
    negocio, redirect_response = negocio_admin_o_redirect(request)
    if redirect_response:
        return redirect_response
    if licencia_bloqueada_para_operar(request.user):
        messages.error(request, estado_licencia(negocio)['mensaje'])
        return redirect('gestion_admin')

    cita = get_object_or_404(Cita, id=cita_id, negocio=negocio)
    nuevo_estado = request.POST.get('nuevo_estado')
    if nuevo_estado in ['PENDIENTE', 'CONFIRMADA', 'ATENDIDA', 'CANCELADA']:
        cita.estado = nuevo_estado
        cita.save()
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
    redirect_response = redirect_si_no_staff(request)
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
        cita.save()
        messages.success(request, f"Pago de cita #{cita.id} actualizado.")
    else:
        messages.error(request, "Datos de pago inválidos.")

    return redirect('gestion_admin')


@login_required
@require_POST
def actualizar_seguimiento_cita_view(request, cita_id):
    redirect_response = redirect_si_no_staff(request)
    if redirect_response:
        return redirect_response
    negocio, redirect_response = negocio_admin_o_redirect(request)
    if redirect_response:
        return redirect_response
    if licencia_bloqueada_para_operar(request.user):
        messages.error(request, estado_licencia(negocio)['mensaje'])
        return redirect('gestion_admin')

    cita = get_object_or_404(Cita, id=cita_id, negocio=negocio)
    etapa = request.POST.get('etapa_seguimiento')
    nota = request.POST.get('nota_seguimiento', '').strip()

    etapas_validas = dict(Cita.ETAPAS_SEGUIMIENTO)
    if etapa in etapas_validas:
        cita.etapa_seguimiento = etapa
        cita.progreso = PROGRESO_POR_ETAPA.get(etapa, cita.progreso)
        cita.nota_seguimiento = nota
        if etapa == 'ENTREGADA':
            cita.estado = 'ATENDIDA'
        cita.save()
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
    redirect_response = redirect_si_no_staff(request)
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
    redirect_response = redirect_si_no_staff(request)
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


# Auth Views
def registro_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
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
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Hola de nuevo, {user.first_name or user.username}.")
                next_page = request.GET.get('next', 'home')
                if next_page == 'home' and es_staff(user):
                    return redirect('gestion_admin')
                return redirect(next_page)
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})


def logout_usuario_view(request):
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('home')
