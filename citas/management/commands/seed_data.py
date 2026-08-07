from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from citas.models import Servicio, Mascota, PerfilCliente, Cita
import datetime

class Command(BaseCommand):
    help = 'Crea datos iniciales de prueba para PetCare Loja'

    def handle(self, *args, **options):
        # 1. Admin Superuser
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser('admin', 'admin@petcareloja.ec', 'admin123')
            admin_user.first_name = 'Administrador'
            admin_user.last_name = 'Loja'
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Superusuario admin / admin123 creado.'))
        else:
            admin_user = User.objects.get(username='admin')

        # 2. Demo Customer
        if not User.objects.filter(username='juanperez').exists():
            cliente = User.objects.create_user('juanperez', 'juan@ejemplo.ec', 'cliente123')
            cliente.first_name = 'Juan'
            cliente.last_name = 'Pérez'
            cliente.save()
            self.stdout.write(self.style.SUCCESS('Cliente demo juanperez / cliente123 creado.'))
        else:
            cliente = User.objects.get(username='juanperez')

        PerfilCliente.objects.get_or_create(
            usuario=cliente,
            defaults={
                'telefono': '+593 99 123 4567',
                'direccion': 'Av. Universitaria y 10 de Agosto',
                'barrio': 'Centro de Loja',
                'contacto_preferido': 'whatsapp',
            }
        )

        # 3. Servicios Iniciales
        servicios_data = [
            {
                'nombre': 'Baño & Spa Canino Pro',
                'descripcion': 'Baño relajante con champú hipoalergénico, secado profesional con aire tibio, cepillado de manto, limpieza de oídos y corte de uñas.',
                'categoria': 'bano',
                'precio': 18.00,
                'duracion_minutos': 45,
                'icono': 'soap',
                'destacado': True,
            },
            {
                'nombre': 'Corte de Raza & Estilo',
                'descripcion': 'Corte especializado según estándar de raza o estilo comercial a tijera/máquina, despunte, acabado impecable y perfume suave.',
                'categoria': 'peluqueria',
                'precio': 25.00,
                'duracion_minutos': 60,
                'icono': 'content_cut',
                'destacado': True,
            },
            {
                'nombre': 'Peluquería Integral Completa',
                'descripcion': 'Servicio VIP que incluye baño nutritivo, mascarilla de keratina, corte de pelo completo, vaciado de glándulas y pedicura canina.',
                'categoria': 'peluqueria',
                'precio': 32.00,
                'duracion_minutos': 75,
                'icono': 'pets',
                'destacado': True,
            },
            {
                'nombre': 'Higiénico & Limpieza de Oídos',
                'descripcion': 'Recorte de zonas higiénicas (plantares, vientre y zona perianal) más limpieza profunda y desinfección de conducto auditivo.',
                'categoria': 'salud',
                'precio': 12.00,
                'duracion_minutos': 30,
                'icono': 'health_and_safety',
                'destacado': False,
            },
            {
                'nombre': 'Tratamiento Deslanado Profundo',
                'descripcion': 'Técnica especial para razas de doble capa (Husky, Golden, Pastor) que retira hasta el 90% del pelo muerto reduciendo caídas.',
                'categoria': 'especial',
                'precio': 28.00,
                'duracion_minutos': 60,
                'icono': 'dry_cleaning',
                'destacado': False,
            },
            {
                'nombre': 'Pedicura & Limpieza Dental',
                'descripcion': 'Corte y limado de uñas sin dolor más cepillado dental enzimático con spray refrescante de aliento.',
                'categoria': 'salud',
                'precio': 10.00,
                'duracion_minutos': 20,
                'icono': 'clean_hands',
                'destacado': False,
            },
        ]

        for s_data in servicios_data:
            Servicio.objects.get_or_create(nombre=s_data['nombre'], defaults=s_data)

        self.stdout.write(self.style.SUCCESS('Servicios del catálogo registrados.'))

        # 4. Mascotas de Prueba
        m1, _ = Mascota.objects.get_or_create(
            propietario=cliente,
            nombre='Toby',
            defaults={
                'especie': 'Canino',
                'raza': 'Schnauzer Miniatura',
                'edad': 3,
                'peso_kg': 6.5,
                'notas_medicas': 'Piel algo sensible, usar champú neutro.',
                'foto_url': 'https://images.unsplash.com/photo-1537151625747-768eb6cf92b2?w=500&q=80',
            }
        )

        m2, _ = Mascota.objects.get_or_create(
            propietario=cliente,
            nombre='Luna',
            defaults={
                'especie': 'Canino',
                'raza': 'Golden Retriever',
                'edad': 2,
                'peso_kg': 26.0,
                'notas_medicas': 'Requiere deslanado de temporada.',
                'foto_url': 'https://images.unsplash.com/photo-1552053831-71594a27632d?w=500&q=80',
            }
        )

        self.stdout.write(self.style.SUCCESS('Mascotas de prueba registradas.'))

        # 5. Citas de Prueba
        s_corte = Servicio.objects.filter(nombre__icontains='Corte').first()
        s_bano = Servicio.objects.filter(nombre__icontains='Baño').first()

        hoy = datetime.date.today()
        manana = hoy + datetime.timedelta(days=1)
        pasado = hoy + datetime.timedelta(days=2)

        if not Cita.objects.filter(propietario=cliente).exists():
            Cita.objects.create(
                propietario=cliente,
                mascota=m1,
                servicio=s_corte or Servicio.objects.first(),
                fecha=manana,
                hora=datetime.time(10, 0),
                estado='CONFIRMADA',
                notas='Favor mantener las barbas tradicionales de Schnauzer.'
            )

            Cita.objects.create(
                propietario=cliente,
                mascota=m2,
                servicio=s_bano or Servicio.objects.first(),
                fecha=pasado,
                hora=datetime.time(15, 30),
                estado='PENDIENTE',
                notas='Atender con cuidado en oídos.'
            )

            self.stdout.write(self.style.SUCCESS('Citas iniciales creadas.'))

        self.stdout.write(self.style.SUCCESS('¡Base de datos cargada exitosamente para PetCare Loja!'))
