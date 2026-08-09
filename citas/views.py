import re

import requests
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.db.models import Sum, Count, Q
from .models import Servicio, Mascota, PerfilCliente, Cita
from .forms import MascotaForm, PerfilClienteForm, CitaForm, RegistroForm

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
DATAFAST_RESULT_OK_PATTERN = re.compile(r'^(000\.000\.|000\.100\.1|000\.[36])')


def es_staff(user):
    return user.is_staff or user.is_superuser


def redirect_si_no_staff(request):
    if es_staff(request.user):
        return None
    messages.error(request, "Acceso no autorizado.")
    return redirect('home')


def datos_transferencia():
    return {
        'banco': settings.TRANSFER_BANK_NAME,
        'cuenta': settings.TRANSFER_ACCOUNT_NUMBER,
        'titular': settings.TRANSFER_ACCOUNT_OWNER,
        'identificacion': settings.TRANSFER_ACCOUNT_ID,
    }


def datafast_configurado():
    return bool(settings.DATAFAST_ENTITY_ID and settings.DATAFAST_AUTHORIZATION)


def csrf_failure(request, reason=""):
    return render(request, 'csrf_error.html', {'reason': reason}, status=403)


def home_view(request):
    servicios_destacados = Servicio.objects.filter(activo=True, destacado=True).only(
        'nombre', 'descripcion', 'precio', 'duracion_minutos', 'icono'
    )[:4]
    servicios_todos = Servicio.objects.filter(activo=True).only(
        'nombre', 'descripcion', 'precio', 'duracion_minutos', 'icono'
    )[:6]
    total_mascotas = Mascota.objects.count()
    total_citas = Cita.objects.filter(estado='ATENDIDA').count()
    
    context = {
        'servicios_destacados': servicios_destacados,
        'servicios_todos': servicios_todos,
        'total_mascotas': total_mascotas,
        'total_citas': total_citas,
    }
    return render(request, 'home.html', context)


def servicios_view(request):
    categoria = request.GET.get('categoria', 'todas')
    servicios = Servicio.objects.filter(activo=True).only(
        'nombre', 'descripcion', 'categoria', 'precio', 'duracion_minutos', 'icono'
    )
    if categoria and categoria != 'todas':
        servicios = servicios.filter(categoria=categoria)

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
    return render(request, 'contacto.html', {
        'contact_phone': settings.PETCARE_CONTACT_PHONE,
        'contact_email': settings.PETCARE_CONTACT_EMAIL,
        'contact_address': settings.PETCARE_ADDRESS,
    })


@login_required
def agendar_cita_view(request):
    servicio_id = request.GET.get('servicio_id')
    servicio_preseleccionado = None
    if servicio_id:
        servicio_preseleccionado = Servicio.objects.filter(id=servicio_id, activo=True).first()

    # Verify user has at least one pet registered
    mascotas_usuario = Mascota.objects.filter(propietario=request.user).only('nombre', 'raza')
    if not mascotas_usuario.exists():
        messages.info(request, "Primero registra a tu mascota para poder agendar una cita de peluquería.")
        return redirect('nueva_mascota')

    if request.method == 'POST':
        form = CitaForm(request.user, request.POST)
        if form.is_valid():
            cita = form.save(commit=False)
            cita.propietario = request.user
            cita.save()
            messages.success(request, f"Cita agendada para {cita.mascota.nombre} en {cita.servicio.nombre} el {cita.fecha}. Te contactaremos para confirmar.")
            return redirect('mis_citas')
        else:
            messages.error(request, "Por favor revisa los campos ingresados.")
    else:
        initial = {}
        if servicio_preseleccionado:
            initial['servicio'] = servicio_preseleccionado
        form = CitaForm(request.user, initial=initial)

    context = {
        'form': form,
        'servicio_preseleccionado': servicio_preseleccionado,
        'mascotas': mascotas_usuario,
    }
    return render(request, 'agendar.html', context)


@login_required
def mis_citas_view(request):
    citas = Cita.objects.select_related('mascota', 'servicio').filter(propietario=request.user).order_by('-fecha', '-hora')
    context = {
        'citas': citas,
    }
    return render(request, 'mis_citas.html', context)


@login_required
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
    cita = get_object_or_404(Cita, id=cita_id, propietario=request.user)
    if cita.estado == 'CANCELADA':
        messages.error(request, "No puedes pagar una cita cancelada.")
        return redirect('mis_citas')

    if cita.estado_pago == 'PAGADO':
        messages.info(request, "Esta cita ya se encuentra pagada.")
        return redirect('mis_citas')

    transferencia = datos_transferencia()

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
            messages.success(request, "Transferencia registrada. PetCare confirmará el pago en el panel administrativo.")
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
    amount = f"{float(cita.servicio.precio):.2f}"
    data = {
        'entityId': settings.DATAFAST_ENTITY_ID,
        'amount': amount,
        'currency': 'USD',
        'paymentType': 'DB',
        'merchantTransactionId': f"PETCARE-CITA-{cita.id}",
        'customer.email': user.email or 'cliente@petcareloja.ec',
        'customer.givenName': user.first_name or user.username,
        'customer.surname': user.last_name or 'Cliente',
        'billing.street1': getattr(getattr(user, 'perfil_cliente', None), 'direccion', '') or 'Loja',
        'billing.city': 'Loja',
        'billing.country': 'EC',
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
    cita = get_object_or_404(Cita, id=cita_id, propietario=request.user)
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
    cita = get_object_or_404(Cita, id=cita_id, propietario=request.user)
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
    if request.method == 'POST':
        form = MascotaForm(request.POST)
        if form.is_valid():
            mascota = form.save(commit=False)
            mascota.propietario = request.user
            mascota.save()
            messages.success(request, f"{mascota.nombre} fue registrado con éxito en PetCare Loja.")
            
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

    estado_filtro = request.GET.get('estado', 'TODOS')
    if estado_filtro and estado_filtro != 'TODOS':
        citas = Cita.objects.select_related('propietario', 'mascota', 'servicio').filter(estado=estado_filtro).order_by('-fecha', '-hora')
    else:
        citas = Cita.objects.select_related('propietario', 'mascota', 'servicio').all().order_by('-fecha', '-hora')

    servicios = Servicio.objects.only('nombre', 'precio', 'duracion_minutos', 'activo')
    
    # Stats
    resumen = Cita.objects.aggregate(
        total=Count('id'),
        pendientes=Count('id', filter=Q(estado='PENDIENTE')),
        confirmadas=Count('id', filter=Q(estado='CONFIRMADA')),
        atendidas=Count('id', filter=Q(estado='ATENDIDA')),
    )
    ingresos = Cita.objects.filter(estado='ATENDIDA').aggregate(total=Sum('servicio__precio'))['total'] or 0

    context = {
        'citas': citas,
        'servicios': servicios,
        'estado_filtro': estado_filtro,
        'total_citas': resumen['total'],
        'pendientes': resumen['pendientes'],
        'confirmadas': resumen['confirmadas'],
        'atendidas': resumen['atendidas'],
        'ingresos': ingresos,
    }
    return render(request, 'gestion.html', context)


@login_required
def cambiar_estado_cita_view(request, cita_id):
    redirect_response = redirect_si_no_staff(request)
    if redirect_response:
        return redirect_response

    cita = get_object_or_404(Cita, id=cita_id)
    nuevo_estado = request.POST.get('nuevo_estado')
    if nuevo_estado in ['PENDIENTE', 'CONFIRMADA', 'ATENDIDA', 'CANCELADA']:
        cita.estado = nuevo_estado
        cita.save()
        messages.success(request, f"Estado de cita #{cita.id} actualizado a '{cita.get_estado_display()}'.")
    
    return redirect('gestion_admin')


@login_required
def actualizar_pago_cita_view(request, cita_id):
    redirect_response = redirect_si_no_staff(request)
    if redirect_response:
        return redirect_response

    cita = get_object_or_404(Cita, id=cita_id)
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
def actualizar_seguimiento_cita_view(request, cita_id):
    redirect_response = redirect_si_no_staff(request)
    if redirect_response:
        return redirect_response

    cita = get_object_or_404(Cita, id=cita_id)
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
        messages.success(request, f"Seguimiento de {cita.mascota.nombre} actualizado: {etapas_validas[etapa]}.")
    else:
        messages.error(request, "La etapa seleccionada no es válida.")

    return redirect('gestion_admin')


@login_required
def toggle_servicio_view(request, servicio_id):
    redirect_response = redirect_si_no_staff(request)
    if redirect_response:
        return redirect_response

    servicio = get_object_or_404(Servicio, id=servicio_id)
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
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            login(request, user)
            messages.success(request, f"Bienvenido a PetCare Loja, {user.first_name or user.username}.")
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
