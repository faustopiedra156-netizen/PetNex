import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from citas.models import Cita, Mascota, Negocio, PerfilCliente, Servicio, Sucursal


class Command(BaseCommand):
    help = 'Crea datos iniciales de prueba para el negocio configurado'

    def handle(self, *args, **options):
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                'admin',
                f"admin@{settings.BUSINESS_SHORT_NAME.lower().replace(' ', '')}.local",
                'admin123',
            )
            admin_user.first_name = 'Administrador'
            admin_user.last_name = settings.BUSINESS_CITY
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Superusuario admin / admin123 creado.'))
        else:
            admin_user = User.objects.get(username='admin')

        if not User.objects.filter(username='juanperez').exists():
            cliente = User.objects.create_user('juanperez', 'juan@ejemplo.ec', 'cliente123')
            cliente.first_name = 'Juan'
            cliente.last_name = 'Perez'
            cliente.save()
            self.stdout.write(self.style.SUCCESS('Cliente demo juanperez / cliente123 creado.'))
        else:
            cliente = User.objects.get(username='juanperez')

        negocio, _ = Negocio.objects.get_or_create(
            nombre=settings.BUSINESS_NAME,
            defaults={'activo': True},
        )

        PerfilCliente.objects.get_or_create(
            usuario=cliente,
            defaults={
                'negocio': negocio,
                'telefono': settings.BUSINESS_CONTACT_PHONE,
                'direccion': settings.BUSINESS_ADDRESS,
                'barrio': settings.BUSINESS_LOCATION_LABEL,
                'contacto_preferido': 'whatsapp',
            },
        )

        sucursal, _ = Sucursal.objects.get_or_create(
            negocio=negocio,
            nombre=f"{settings.BUSINESS_SHORT_NAME} Principal",
            defaults={
                'ciudad': settings.BUSINESS_CITY,
                'direccion': settings.BUSINESS_ADDRESS,
                'telefono': settings.BUSINESS_CONTACT_PHONE,
                'activa': True,
            },
        )

        servicios_data = [
            {
                'nombre': 'Bano y spa para mascotas',
                'descripcion': 'Bano relajante con shampoo hipoalergenico, secado profesional, cepillado, limpieza de oidos y corte de unas.',
                'categoria': 'bano',
                'precio': 18.00,
                'duracion_minutos': 45,
                'icono': 'soap',
                'destacado': True,
            },
            {
                'nombre': 'Corte de raza y estilo',
                'descripcion': 'Corte especializado segun raza o estilo comercial, acabado prolijo y perfume suave.',
                'categoria': 'peluqueria',
                'precio': 25.00,
                'duracion_minutos': 60,
                'icono': 'content_cut',
                'destacado': True,
            },
            {
                'nombre': 'Peluqueria integral completa',
                'descripcion': 'Servicio completo con bano nutritivo, corte, limpieza, pedicura y acabado estetico.',
                'categoria': 'peluqueria',
                'precio': 32.00,
                'duracion_minutos': 75,
                'icono': 'pets',
                'destacado': True,
            },
            {
                'nombre': 'Higiene y limpieza de oidos',
                'descripcion': 'Recorte de zonas higienicas, limpieza de oidos y cuidados basicos de higiene.',
                'categoria': 'salud',
                'precio': 12.00,
                'duracion_minutos': 30,
                'icono': 'health_and_safety',
                'destacado': False,
            },
            {
                'nombre': 'Tratamiento deslanado',
                'descripcion': 'Tecnica para retirar pelo muerto y reducir caida en mascotas con manto abundante.',
                'categoria': 'especial',
                'precio': 28.00,
                'duracion_minutos': 60,
                'icono': 'dry_cleaning',
                'destacado': False,
            },
            {
                'nombre': 'Pedicura y limpieza dental',
                'descripcion': 'Corte y limado de unas, mas cepillado dental con producto especializado.',
                'categoria': 'salud',
                'precio': 10.00,
                'duracion_minutos': 20,
                'icono': 'clean_hands',
                'destacado': False,
            },
        ]

        for servicio_data in servicios_data:
            Servicio.objects.get_or_create(negocio=negocio, nombre=servicio_data['nombre'], defaults=servicio_data)

        self.stdout.write(self.style.SUCCESS('Servicios del catalogo registrados.'))

        mascota_1, _ = Mascota.objects.get_or_create(
            propietario=cliente,
            nombre='Toby',
            defaults={
                'especie': 'Canino',
                'raza': 'Schnauzer Miniatura',
                'edad': 3,
                'peso_kg': 6.5,
                'notas_medicas': 'Piel sensible, usar shampoo neutro.',
                'foto_url': 'https://images.unsplash.com/photo-1537151625747-768eb6cf92b2?w=500&q=80',
            },
        )

        mascota_2, _ = Mascota.objects.get_or_create(
            propietario=cliente,
            nombre='Luna',
            defaults={
                'especie': 'Canino',
                'raza': 'Golden Retriever',
                'edad': 2,
                'peso_kg': 26.0,
                'notas_medicas': 'Requiere deslanado de temporada.',
                'foto_url': 'https://images.unsplash.com/photo-1552053831-71594a27632d?w=500&q=80',
            },
        )

        self.stdout.write(self.style.SUCCESS('Mascotas de prueba registradas.'))

        servicio_corte = Servicio.objects.filter(negocio=negocio, nombre__icontains='Corte').first()
        servicio_bano = Servicio.objects.filter(negocio=negocio, nombre__icontains='Bano').first()

        hoy = datetime.date.today()
        manana = hoy + datetime.timedelta(days=1)
        pasado = hoy + datetime.timedelta(days=2)

        if not Cita.objects.filter(negocio=negocio, propietario=cliente).exists():
            Cita.objects.create(
                negocio=negocio,
                sucursal=sucursal,
                propietario=cliente,
                mascota=mascota_1,
                servicio=servicio_corte or Servicio.objects.filter(negocio=negocio).first(),
                fecha=manana,
                hora=datetime.time(10, 0),
                estado='CONFIRMADA',
                notas='Favor mantener el estilo tradicional.',
            )

            Cita.objects.create(
                negocio=negocio,
                sucursal=sucursal,
                propietario=cliente,
                mascota=mascota_2,
                servicio=servicio_bano or Servicio.objects.filter(negocio=negocio).first(),
                fecha=pasado,
                hora=datetime.time(15, 30),
                estado='PENDIENTE',
                notas='Atender con cuidado en oidos.',
            )

            self.stdout.write(self.style.SUCCESS('Citas iniciales creadas.'))

        self.stdout.write(self.style.SUCCESS(f'Base de datos cargada exitosamente para {settings.BUSINESS_NAME}.'))
