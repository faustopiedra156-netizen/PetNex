import datetime

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Negocio(models.Model):
    nombre = models.CharField(max_length=120, verbose_name="Nombre del negocio")
    propietario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='negocios_administrados',
        verbose_name="Administrador del local",
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Negocio"
        verbose_name_plural = "Negocios"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class UsuarioNegocio(models.Model):
    ROLES = [
        ('ADMIN_LOCAL', 'Administrador del local'),
        ('EMPLEADO', 'Empleado'),
    ]

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='asignaciones_negocio',
        verbose_name='Usuario',
    )
    negocio = models.ForeignKey(
        Negocio,
        on_delete=models.CASCADE,
        related_name='usuarios_asignados',
        verbose_name='Negocio',
    )
    rol = models.CharField(max_length=20, choices=ROLES, default='ADMIN_LOCAL')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Usuario del negocio'
        verbose_name_plural = 'Usuarios de los negocios'
        constraints = [
            models.UniqueConstraint(
                fields=['usuario', 'negocio'],
                name='usuario_negocio_unico',
            ),
        ]
        indexes = [
            models.Index(fields=['negocio', 'activo'], name='usuario_negocio_activo_idx'),
            models.Index(fields=['usuario', 'activo'], name='usuario_negocio_usuario_idx'),
        ]

    def __str__(self):
        return f'{self.usuario} - {self.negocio} ({self.get_rol_display()})'


class PlanSuscripcion(models.Model):
    nombre = models.CharField(max_length=80, unique=True, verbose_name="Nombre del plan")
    precio_mensual = models.DecimalField(max_digits=7, decimal_places=2, default=0, verbose_name="Precio mensual")
    max_sucursales = models.PositiveIntegerField(default=1, verbose_name="Maximo de sucursales")
    max_citas_mes = models.PositiveIntegerField(default=100, verbose_name="Maximo de citas por mes")
    permite_pagos = models.BooleanField(default=False, verbose_name="Permite pagos")
    permite_chatbot = models.BooleanField(default=True, verbose_name="Permite chatbot")
    permite_reportes = models.BooleanField(default=False, verbose_name="Permite reportes avanzados")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Plan de suscripcion"
        verbose_name_plural = "Planes de suscripcion"
        ordering = ['precio_mensual', 'nombre']

    def __str__(self):
        return f"{self.nombre} (${self.precio_mensual}/mes)"


class SuscripcionNegocio(models.Model):
    ESTADOS = [
        ('ACTIVA', 'Activa'),
        ('VENCIDA', 'Vencida'),
        ('SUSPENDIDA', 'Suspendida'),
        ('DEMO', 'Demo'),
    ]

    negocio = models.ForeignKey(
        Negocio,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='suscripciones',
        verbose_name="Negocio",
    )
    plan = models.ForeignKey(PlanSuscripcion, on_delete=models.PROTECT, related_name='suscripciones')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='DEMO', verbose_name="Estado")
    fecha_inicio = models.DateField(default=timezone.localdate, verbose_name="Fecha de inicio")
    fecha_vencimiento = models.DateField(verbose_name="Fecha de vencimiento")
    contacto_pago = models.CharField(max_length=120, blank=True, default='', verbose_name="Contacto para pago")
    notas = models.TextField(blank=True, default='', verbose_name="Notas internas")
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Suscripcion del negocio"
        verbose_name_plural = "Suscripcion del negocio"

    def __str__(self):
        return f"{self.plan.nombre} - {self.estado} hasta {self.fecha_vencimiento}"

    @classmethod
    def actual(cls, negocio=None):
        queryset = cls.objects.select_related('plan', 'negocio')
        if negocio:
            queryset = queryset.filter(negocio=negocio)
        return queryset.order_by('-fecha_vencimiento', '-actualizado_en').first()

    @property
    def dias_restantes(self):
        return (self.fecha_vencimiento - timezone.localdate()).days

    @property
    def esta_activa(self):
        return self.estado in {'ACTIVA', 'DEMO'} and self.fecha_vencimiento >= timezone.localdate()

    @property
    def esta_por_vencer(self):
        return self.esta_activa and self.dias_restantes <= 7


class PagoSuscripcion(models.Model):
    CICLOS = [
        ('MENSUAL', 'Mensual'),
        ('ANUAL', 'Anual'),
    ]
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
    ]

    suscripcion = models.ForeignKey(
        SuscripcionNegocio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pagos',
        verbose_name="Suscripcion",
    )
    plan = models.ForeignKey(PlanSuscripcion, on_delete=models.PROTECT, related_name='pagos', verbose_name="Plan")
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pagos_suscripcion')
    ciclo_facturacion = models.CharField(max_length=20, choices=CICLOS, default='MENSUAL')
    monto = models.DecimalField(max_digits=8, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    metodo = models.CharField(max_length=20, default='TARJETA')
    contacto_pago = models.CharField(max_length=120, blank=True, default='')
    checkout_id = models.CharField(max_length=180, blank=True, default='')
    datafast_resource_path = models.CharField(max_length=255, blank=True, default='')
    datafast_result_code = models.CharField(max_length=60, blank=True, default='')
    referencia = models.CharField(max_length=180, blank=True, default='')
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pago de suscripcion"
        verbose_name_plural = "Pagos de suscripcion"
        ordering = ['-creado_en']

    def __str__(self):
        return f"{self.plan.nombre} {self.ciclo_facturacion} - {self.estado} (${self.monto})"


class ConfiguracionNegocio(models.Model):
    negocio = models.OneToOneField(
        Negocio,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='configuracion',
        verbose_name="Negocio",
    )
    nombre = models.CharField(max_length=120, default='PetCare Loja')
    nombre_corto = models.CharField(max_length=80, default='PetCare')
    ciudad = models.CharField(max_length=80, default='Loja')
    pais = models.CharField(max_length=80, default='Ecuador')
    codigo_pais = models.CharField(max_length=2, default='EC')
    categoria = models.CharField(max_length=120, default='peluquer\u00eda y est\u00e9tica para mascotas')
    slogan = models.CharField(max_length=160, default='Cuidado profesional para mascotas')
    hero_badge = models.CharField(max_length=180, default='Peluquer\u00eda y est\u00e9tica para mascotas')
    hero_titulo = models.CharField(max_length=180, default='Ba\u00f1o, corte y cari\u00f1o para tu mascota.')
    hero_descripcion = models.TextField(default='Servicios de higiene y cuidado est\u00e9tico con atenci\u00f3n personalizada.')
    contacto_titulo = models.CharField(max_length=180, default='Estamos listos para atender a tu mascota')
    contacto_descripcion = models.TextField(default='Escribenos para consultar disponibilidad, servicios especiales o cuidados antes de una cita.')
    descripcion_footer = models.TextField(default='Centro especializado en est\u00e9tica, peluquer\u00eda y spa para mascotas.')
    email = models.EmailField(default='contacto@negocio.com')
    telefono = models.CharField(max_length=30, default='+593 99 999 9999')
    direccion = models.CharField(max_length=180, default='Direccion del local')
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Latitud del local')
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Longitud del local')
    horario = models.CharField(max_length=120, default='Lun - Sab: 08:30 - 18:30')
    moneda = models.CharField(max_length=10, default='USD')
    simbolo_moneda = models.CharField(max_length=5, default='$')
    etiqueta_resenas = models.CharField(max_length=80, default='Rese\u00f1as de clientes')
    etiqueta_ubicacion = models.CharField(max_length=80, default='Centro')
    texto_boton_principal = models.CharField(max_length=80, default='Agendar cita')
    prefijo_transaccion = models.CharField(max_length=30, default='NEGOCIO')
    mostrar_cuentas_demo = models.BooleanField(default=False)
    google_login_activo = models.BooleanField(default=False)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuracion del negocio"
        verbose_name_plural = "Configuracion del negocio"

    def __str__(self):
        return self.nombre

    @classmethod
    def actual(cls, negocio=None):
        queryset = cls.objects.select_related('negocio')
        if negocio:
            queryset = queryset.filter(negocio=negocio)
        config = queryset.order_by('id').first()
        return config

    def as_business_dict(self):
        return {
            'app_name': 'PetNexo',
            'name': self.nombre,
            'short_name': self.nombre_corto,
            'city': self.ciudad,
            'country': self.pais,
            'country_code': self.codigo_pais,
            'category': self.categoria,
            'tagline': self.slogan,
            'hero_badge': self.hero_badge,
            'hero_title': self.hero_titulo,
            'hero_description': self.hero_descripcion,
            'contact_title': self.contacto_titulo,
            'contact_description': self.contacto_descripcion,
            'footer_description': self.descripcion_footer,
            'email': self.email,
            'phone': self.telefono,
            'address': self.direccion,
            'latitude': self.latitud,
            'longitude': self.longitud,
            'opening_hours': self.horario,
            'currency': self.moneda,
            'currency_symbol': self.simbolo_moneda,
            'review_label': self.etiqueta_resenas,
            'location_label': self.etiqueta_ubicacion,
            'primary_cta': self.texto_boton_principal,
            'show_demo_accounts': self.mostrar_cuentas_demo,
            'google_login_enabled': (self.google_login_activo or settings.GOOGLE_LOGIN_ENABLED) and settings.GOOGLE_LOGIN_CONFIGURED,
            'transaction_prefix': self.prefijo_transaccion,
        }

class Servicio(models.Model):
    CATEGORIAS = [
        ('peluqueria', 'Peluquer\u00eda & Est\u00e9tica'),
        ('bano', 'Ba\u00f1o & Spa'),
        ('salud', 'Salud & Higiene'),
        ('especial', 'Tratamientos Especiales'),
    ]
    negocio = models.ForeignKey(
        Negocio,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='servicios',
        verbose_name="Negocio",
    )
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Servicio")
    descripcion = models.TextField(verbose_name="Descripci\u00f3n detallada")
    categoria = models.CharField(max_length=50, choices=CATEGORIAS, default='peluqueria', verbose_name="Categor\u00eda")
    precio = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Precio ($ USD)")
    duracion_minutos = models.PositiveIntegerField(default=45, verbose_name="Duraci\u00f3n estimada (minutos)")
    icono = models.CharField(max_length=50, default='content_cut', verbose_name="Icono")
    destacado = models.BooleanField(default=False, verbose_name="Servicio Destacado")
    activo = models.BooleanField(default=True, verbose_name="Activo en cat\u00e1logo")

    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"
        ordering = ['-destacado', 'nombre']
        indexes = [
            models.Index(fields=['negocio', 'activo', 'categoria'], name='servicio_catalogo_idx'),
        ]

    def __str__(self):
        return f"{self.nombre} (${self.precio})"


class Sucursal(models.Model):
    DIAS_SEMANA = [
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miercoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sabado'),
        (6, 'Domingo'),
    ]

    negocio = models.ForeignKey(
        Negocio,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sucursales',
        verbose_name="Negocio",
    )
    nombre = models.CharField(max_length=120, verbose_name="Nombre de la sucursal")
    ciudad = models.CharField(max_length=80, verbose_name="Ciudad")
    direccion = models.CharField(max_length=180, verbose_name="Direccion")
    telefono = models.CharField(max_length=30, blank=True, verbose_name="Telefono")
    hora_apertura = models.TimeField(default='08:30', verbose_name="Hora de apertura")
    hora_cierre = models.TimeField(default='18:30', verbose_name="Hora de cierre")
    intervalo_turnos = models.PositiveIntegerField(default=30, verbose_name="Intervalo de turnos en minutos")
    dias_cerrados = models.CharField(
        max_length=30,
        default='6',
        blank=True,
        verbose_name="Dias cerrados",
        help_text="Numeros separados por coma: 0=lunes, 1=martes, 2=miercoles, 3=jueves, 4=viernes, 5=sabado, 6=domingo.",
    )
    activa = models.BooleanField(default=True, verbose_name="Activa")
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sucursal"
        verbose_name_plural = "Sucursales"
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['negocio', 'activa'], name='sucursal_negocio_activa_idx'),
        ]

    def __str__(self):
        return f"{self.nombre} - {self.ciudad}"

    def dias_cerrados_set(self):
        dias = set()
        for item in str(self.dias_cerrados or '').split(','):
            item = item.strip()
            if not item:
                continue
            try:
                dias.add(int(item))
            except ValueError:
                continue
        return dias

    def atiende_en_fecha(self, fecha):
        return fecha.weekday() not in self.dias_cerrados_set()

    def generar_horarios(self):
        horarios = []
        intervalo = max(int(self.intervalo_turnos or 30), 1)
        hora = datetime.datetime.combine(datetime.date.today(), self.hora_apertura)
        cierre = datetime.datetime.combine(datetime.date.today(), self.hora_cierre)
        while hora <= cierre:
            horarios.append(hora.time())
            hora += datetime.timedelta(minutes=intervalo)
        return horarios


class Mascota(models.Model):
    negocio = models.ForeignKey(
        Negocio,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='mascotas',
        verbose_name="Negocio",
    )
    propietario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mascotas', verbose_name="Due\u00f1o/Propietario")
    nombre = models.CharField(max_length=50, verbose_name="Nombre de la mascota")
    especie = models.CharField(max_length=30, default='Canino (Perro)', verbose_name="Especie")
    raza = models.CharField(max_length=50, verbose_name="Raza")
    edad = models.PositiveIntegerField(default=2, verbose_name="Edad (a\u00f1os)")
    peso_kg = models.DecimalField(max_digits=4, decimal_places=1, default=5.0, verbose_name="Peso (kg)")
    notas_medicas = models.TextField(blank=True, null=True, verbose_name="Alergias o Cuidados Especiales")
    foto = models.ImageField(
        upload_to='mascotas/%Y/%m/',
        blank=True,
        null=True,
        verbose_name="Foto de la mascota",
    )
    # Se conserva para no romper registros antiguos creados con una URL.
    foto_url = models.URLField(blank=True, null=True, verbose_name="URL de Imagen / Foto")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mascota"
        verbose_name_plural = "Mascotas"
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['negocio', 'propietario'], name='mascota_negocio_prop_idx'),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.raza}) - Due\u00f1o: {self.propietario.get_full_name() or self.propietario.username}"


class PerfilCliente(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_cliente', verbose_name="Usuario")
    negocio = models.ForeignKey(
        Negocio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clientes',
        verbose_name="Negocio principal",
    )
    telefono = models.CharField(max_length=20, blank=True, verbose_name="Tel\u00e9fono")
    direccion = models.CharField(max_length=180, blank=True, verbose_name="Direcci\u00f3n")
    barrio = models.CharField(max_length=80, blank=True, verbose_name="Barrio o sector")
    contacto_preferido = models.CharField(
        max_length=20,
        choices=[('whatsapp', 'WhatsApp'), ('llamada', 'Llamada'), ('email', 'Email')],
        default='whatsapp',
        verbose_name="Contacto preferido",
    )

    class Meta:
        verbose_name = "Perfil de cliente"
        verbose_name_plural = "Perfiles de clientes"

    def __str__(self):
        return self.usuario.get_full_name() or self.usuario.username


class Cita(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente de Confirmaci\u00f3n'),
        ('CONFIRMADA', 'Confirmada'),
        ('ATENDIDA', 'Servicio Atendido'),
        ('CANCELADA', 'Cancelada'),
    ]

    ETAPAS_SEGUIMIENTO = [
        ('AGENDADA', 'Cita agendada'),
        ('RECIBIDA', 'Mascota recibida'),
        ('BANO', 'Ba\u00f1o y limpieza'),
        ('SECADO', 'Secado y cepillado'),
        ('CORTE', 'Corte y estilizado'),
        ('REVISION', 'Revisi\u00f3n final'),
        ('LISTA', 'Lista para retirar'),
        ('ENTREGADA', 'Entregada'),
    ]

    negocio = models.ForeignKey(
        Negocio,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='citas',
        verbose_name="Negocio",
    )
    propietario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='citas', verbose_name="Cliente")
    sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, related_name='citas', verbose_name="Sucursal")
    mascota = models.ForeignKey(Mascota, on_delete=models.CASCADE, related_name='citas', verbose_name="Mascota")
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='citas', verbose_name="Servicio Requerido")
    precio_acordado = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Precio acordado",
    )
    fecha = models.DateField(verbose_name="Fecha de Atenci\u00f3n")
    hora = models.TimeField(verbose_name="Hora de Atenci\u00f3n")
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE', verbose_name="Estado de la Cita")
    etapa_seguimiento = models.CharField(max_length=20, choices=ETAPAS_SEGUIMIENTO, default='AGENDADA', verbose_name="Etapa de seguimiento")
    progreso = models.PositiveIntegerField(default=0, verbose_name="Progreso (%)")
    nota_seguimiento = models.TextField(blank=True, null=True, verbose_name="Nota visible para el cliente")
    actualizado_seguimiento = models.DateTimeField(auto_now=True, verbose_name="\u00daltima actualizaci\u00f3n de seguimiento")
    estado_pago = models.CharField(
        max_length=20,
        choices=[('PENDIENTE', 'Pendiente'), ('ABONADO', 'Abonado'), ('PAGADO', 'Pagado')],
        default='PENDIENTE',
        verbose_name="Estado de pago",
    )
    metodo_pago = models.CharField(
        max_length=20,
        choices=[('EFECTIVO', 'Efectivo'), ('TRANSFERENCIA', 'Transferencia'), ('TARJETA', 'Tarjeta')],
        default='EFECTIVO',
        verbose_name="M\u00e9todo de pago",
    )
    referencia_pago = models.CharField(max_length=120, blank=True, verbose_name="Referencia de pago")
    datafast_checkout_id = models.CharField(max_length=180, blank=True, verbose_name="Checkout ID Datafast")
    datafast_resource_path = models.CharField(max_length=255, blank=True, verbose_name="Resource path Datafast")
    datafast_result_code = models.CharField(max_length=60, blank=True, verbose_name="C\u00f3digo de respuesta Datafast")
    notas = models.TextField(blank=True, null=True, verbose_name="Observaciones o Requerimientos")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cita"
        verbose_name_plural = "Citas"
        ordering = ['-fecha', '-hora']
        constraints = [
            models.UniqueConstraint(
                fields=['sucursal', 'fecha', 'hora'],
                condition=~models.Q(estado='CANCELADA'),
                name='cita_horario_activo_unico_por_sucursal',
            ),
        ]
        indexes = [
            models.Index(fields=['negocio', 'fecha'], name='cita_negocio_fecha_idx'),
            models.Index(fields=['negocio', 'estado', 'fecha'], name='cita_estado_fecha_idx'),
            models.Index(fields=['propietario', 'fecha'], name='cita_cliente_fecha_idx'),
            models.Index(fields=['negocio', 'creado_en'], name='cita_negocio_creada_idx'),
        ]

    def __str__(self):
        return f"Cita #{self.id} - {self.mascota.nombre} ({self.servicio.nombre}) - {self.fecha} {self.hora}"


class Calificacion(models.Model):
    ESCALA = [
        (1, '1 estrella - Mala'),
        (2, '2 estrellas - Regular'),
        (3, '3 estrellas - Buena'),
        (4, '4 estrellas - Muy buena'),
        (5, '5 estrellas - Excelente'),
    ]

    cita = models.OneToOneField(Cita, on_delete=models.CASCADE, related_name='calificacion', verbose_name="Cita")
    cliente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calificaciones', verbose_name="Cliente")
    puntuacion = models.PositiveSmallIntegerField(choices=ESCALA, verbose_name="Puntuaci\u00f3n")
    comentario = models.TextField(blank=True, verbose_name="Comentario")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Calificaci\u00f3n"
        verbose_name_plural = "Calificaciones"
        ordering = ['-creado_en']

    def __str__(self):
        return f"{self.puntuacion}/5 - Cita #{self.cita_id}"


class CodigoRecuperacionContrasena(models.Model):
    """One-time reset code persisted as a password hash."""

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='codigos_recuperacion_contrasena',
        verbose_name="Usuario",
    )
    codigo_hash = models.CharField(max_length=128, verbose_name="Codigo cifrado")
    expira_en = models.DateTimeField(verbose_name="Expira en")
    intentos = models.PositiveSmallIntegerField(default=0, verbose_name="Intentos realizados")
    usado_en = models.DateTimeField(null=True, blank=True, verbose_name="Usado en")
    creado_en = models.DateTimeField(auto_now_add=True, verbose_name="Creado en")

    class Meta:
        verbose_name = "Codigo de recuperacion de contrasena"
        verbose_name_plural = "Codigos de recuperacion de contrasena"
        ordering = ['-creado_en']
        indexes = [
            models.Index(
                fields=['usuario', 'expira_en'],
                name='citas_codig_usuario_9be51c_idx',
            )
        ]

    def __str__(self):
        return f"Codigo de recuperacion para {self.usuario}"

    @property
    def esta_vigente(self):
        return self.usado_en is None and self.expira_en > timezone.now()


class MensajeContacto(models.Model):
    negocio = models.ForeignKey(Negocio, on_delete=models.CASCADE, related_name='mensajes_contacto')
    nombre = models.CharField(max_length=120)
    telefono = models.CharField(max_length=30)
    mensaje = models.TextField(max_length=1500)
    atendido = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Mensaje de contacto'
        verbose_name_plural = 'Mensajes de contacto'
        ordering = ['atendido', '-creado_en']
        indexes = [
            models.Index(fields=['negocio', 'atendido', 'creado_en'], name='mensaje_contacto_estado_idx'),
        ]

    def __str__(self):
        return f'{self.nombre} - {self.negocio.nombre}'
