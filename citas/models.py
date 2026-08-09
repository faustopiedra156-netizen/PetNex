from django.db import models
from django.contrib.auth.models import User

class Servicio(models.Model):
    CATEGORIAS = [
        ('peluqueria', 'Peluquería & Estética'),
        ('bano', 'Baño & Spa'),
        ('salud', 'Salud & Higiene'),
        ('especial', 'Tratamientos Especiales'),
    ]

    nombre = models.CharField(max_length=100, verbose_name="Nombre del Servicio")
    descripcion = models.TextField(verbose_name="Descripción detallada")
    categoria = models.CharField(max_length=50, choices=CATEGORIAS, default='peluqueria', verbose_name="Categoría")
    precio = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Precio ($ USD)")
    duracion_minutos = models.PositiveIntegerField(default=45, verbose_name="Duración estimada (minutos)")
    icono = models.CharField(max_length=50, default='content_cut', verbose_name="Icono")
    destacado = models.BooleanField(default=False, verbose_name="Servicio Destacado")
    activo = models.BooleanField(default=True, verbose_name="Activo en catálogo")

    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"
        ordering = ['-destacado', 'nombre']

    def __str__(self):
        return f"{self.nombre} (${self.precio})"


class Mascota(models.Model):
    propietario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mascotas', verbose_name="Dueño/Propietario")
    nombre = models.CharField(max_length=50, verbose_name="Nombre de la mascota")
    especie = models.CharField(max_length=30, default='Canino (Perro)', verbose_name="Especie")
    raza = models.CharField(max_length=50, verbose_name="Raza")
    edad = models.PositiveIntegerField(default=2, verbose_name="Edad (años)")
    peso_kg = models.DecimalField(max_digits=4, decimal_places=1, default=5.0, verbose_name="Peso (kg)")
    notas_medicas = models.TextField(blank=True, null=True, verbose_name="Alergias o Cuidados Especiales")
    foto_url = models.URLField(blank=True, null=True, verbose_name="URL de Imagen / Foto")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mascota"
        verbose_name_plural = "Mascotas"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.raza}) - Dueño: {self.propietario.get_full_name() or self.propietario.username}"


class PerfilCliente(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_cliente', verbose_name="Usuario")
    telefono = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    direccion = models.CharField(max_length=180, blank=True, verbose_name="Dirección")
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
        ('PENDIENTE', 'Pendiente de Confirmación'),
        ('CONFIRMADA', 'Confirmada'),
        ('ATENDIDA', 'Servicio Atendido'),
        ('CANCELADA', 'Cancelada'),
    ]

    ETAPAS_SEGUIMIENTO = [
        ('AGENDADA', 'Cita agendada'),
        ('RECIBIDA', 'Mascota recibida'),
        ('BANO', 'Baño y limpieza'),
        ('SECADO', 'Secado y cepillado'),
        ('CORTE', 'Corte y estilizado'),
        ('REVISION', 'Revisión final'),
        ('LISTA', 'Lista para retirar'),
        ('ENTREGADA', 'Entregada'),
    ]

    propietario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='citas', verbose_name="Cliente")
    mascota = models.ForeignKey(Mascota, on_delete=models.CASCADE, related_name='citas', verbose_name="Mascota")
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='citas', verbose_name="Servicio Requerido")
    fecha = models.DateField(verbose_name="Fecha de Atención")
    hora = models.TimeField(verbose_name="Hora de Atención")
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE', verbose_name="Estado de la Cita")
    etapa_seguimiento = models.CharField(max_length=20, choices=ETAPAS_SEGUIMIENTO, default='AGENDADA', verbose_name="Etapa de seguimiento")
    progreso = models.PositiveIntegerField(default=0, verbose_name="Progreso (%)")
    nota_seguimiento = models.TextField(blank=True, null=True, verbose_name="Nota visible para el cliente")
    actualizado_seguimiento = models.DateTimeField(auto_now=True, verbose_name="Última actualización de seguimiento")
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
        verbose_name="Método de pago",
    )
    referencia_pago = models.CharField(max_length=120, blank=True, verbose_name="Referencia de pago")
    datafast_checkout_id = models.CharField(max_length=180, blank=True, verbose_name="Checkout ID Datafast")
    datafast_resource_path = models.CharField(max_length=255, blank=True, verbose_name="Resource path Datafast")
    datafast_result_code = models.CharField(max_length=60, blank=True, verbose_name="Código de respuesta Datafast")
    notas = models.TextField(blank=True, null=True, verbose_name="Observaciones o Requerimientos")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cita"
        verbose_name_plural = "Citas"
        ordering = ['-fecha', '-hora']

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
    puntuacion = models.PositiveSmallIntegerField(choices=ESCALA, verbose_name="Puntuación")
    comentario = models.TextField(blank=True, verbose_name="Comentario")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Calificación"
        verbose_name_plural = "Calificaciones"
        ordering = ['-creado_en']

    def __str__(self):
        return f"{self.puntuacion}/5 - Cita #{self.cita_id}"
