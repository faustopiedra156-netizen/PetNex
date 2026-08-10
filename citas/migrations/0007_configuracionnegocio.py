from django.db import migrations, models


def crear_configuracion_inicial(apps, schema_editor):
    ConfiguracionNegocio = apps.get_model('citas', 'ConfiguracionNegocio')
    ConfiguracionNegocio.objects.get_or_create(
        id=1,
        defaults={
            'nombre': 'Happy Pets Quito',
            'nombre_corto': 'Happy Pets',
            'ciudad': 'Quito',
            'pais': 'Ecuador',
            'codigo_pais': 'EC',
            'categoria': 'peluqueria y estetica para mascotas',
            'slogan': 'Cuidado profesional para mascotas',
            'hero_badge': 'Peluqueria y estetica para mascotas en Quito, Ecuador',
            'hero_titulo': 'Bano, corte y carino para tu mascota.',
            'hero_descripcion': 'Ofrecemos banos, cortes, tratamientos de higiene y cuidado estetico con atencion personalizada.',
            'descripcion_footer': 'Centro especializado en estetica, peluqueria y spa para mascotas.',
            'email': 'contacto@happypets.com',
            'telefono': '+593 99 999 9999',
            'direccion': 'Av. Principal, Quito, Ecuador',
            'horario': 'Lun - Sab: 08:30 - 18:30',
            'moneda': 'USD',
            'simbolo_moneda': '$',
            'etiqueta_resenas': 'Resenas en Quito',
            'etiqueta_ubicacion': 'Quito Centro',
            'texto_boton_principal': 'Agendar cita',
            'prefijo_transaccion': 'HAPPYPETS',
            'mostrar_cuentas_demo': False,
            'google_login_activo': False,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0006_calificacion'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfiguracionNegocio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(default='PetCare Loja', max_length=120)),
                ('nombre_corto', models.CharField(default='PetCare', max_length=80)),
                ('ciudad', models.CharField(default='Loja', max_length=80)),
                ('pais', models.CharField(default='Ecuador', max_length=80)),
                ('codigo_pais', models.CharField(default='EC', max_length=2)),
                ('categoria', models.CharField(default='peluqueria y estetica para mascotas', max_length=120)),
                ('slogan', models.CharField(default='Cuidado profesional para mascotas', max_length=160)),
                ('hero_badge', models.CharField(default='Peluqueria y estetica para mascotas', max_length=180)),
                ('hero_titulo', models.CharField(default='Bano, corte y carino para tu mascota.', max_length=180)),
                ('hero_descripcion', models.TextField(default='Servicios de higiene y cuidado estetico con atencion personalizada.')),
                ('descripcion_footer', models.TextField(default='Centro especializado en estetica, peluqueria y spa para mascotas.')),
                ('email', models.EmailField(default='contacto@negocio.com', max_length=254)),
                ('telefono', models.CharField(default='+593 99 999 9999', max_length=30)),
                ('direccion', models.CharField(default='Direccion del local', max_length=180)),
                ('horario', models.CharField(default='Lun - Sab: 08:30 - 18:30', max_length=120)),
                ('moneda', models.CharField(default='USD', max_length=10)),
                ('simbolo_moneda', models.CharField(default='$', max_length=5)),
                ('etiqueta_resenas', models.CharField(default='Resenas de clientes', max_length=80)),
                ('etiqueta_ubicacion', models.CharField(default='Centro', max_length=80)),
                ('texto_boton_principal', models.CharField(default='Agendar cita', max_length=80)),
                ('prefijo_transaccion', models.CharField(default='NEGOCIO', max_length=30)),
                ('mostrar_cuentas_demo', models.BooleanField(default=False)),
                ('google_login_activo', models.BooleanField(default=False)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Configuracion del negocio',
                'verbose_name_plural': 'Configuracion del negocio',
            },
        ),
        migrations.RunPython(crear_configuracion_inicial, migrations.RunPython.noop),
    ]
