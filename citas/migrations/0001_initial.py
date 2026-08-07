# Generated for PetCare Loja

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Servicio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, verbose_name='Nombre del Servicio')),
                ('descripcion', models.TextField(verbose_name='Descripcion detallada')),
                ('categoria', models.CharField(choices=[('peluqueria', 'Peluqueria & Estetica'), ('bano', 'Bano & Spa'), ('salud', 'Salud & Higiene'), ('especial', 'Tratamientos Especiales')], default='peluqueria', max_length=50, verbose_name='Categoria')),
                ('precio', models.DecimalField(decimal_places=2, max_digits=6, verbose_name='Precio ($ USD)')),
                ('duracion_minutos', models.PositiveIntegerField(default=45, verbose_name='Duracion estimada (minutos)')),
                ('icono', models.CharField(default='content_cut', max_length=50, verbose_name='Icono')),
                ('destacado', models.BooleanField(default=False, verbose_name='Servicio Destacado')),
                ('activo', models.BooleanField(default=True, verbose_name='Activo en catalogo')),
            ],
            options={
                'verbose_name': 'Servicio',
                'verbose_name_plural': 'Servicios',
                'ordering': ['-destacado', 'nombre'],
            },
        ),
        migrations.CreateModel(
            name='Mascota',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=50, verbose_name='Nombre de la mascota')),
                ('especie', models.CharField(default='Canino (Perro)', max_length=30, verbose_name='Especie')),
                ('raza', models.CharField(max_length=50, verbose_name='Raza')),
                ('edad', models.PositiveIntegerField(default=2, verbose_name='Edad (anos)')),
                ('peso_kg', models.DecimalField(decimal_places=1, default=5.0, max_digits=4, verbose_name='Peso (kg)')),
                ('notas_medicas', models.TextField(blank=True, null=True, verbose_name='Alergias o Cuidados Especiales')),
                ('foto_url', models.URLField(blank=True, null=True, verbose_name='URL de Imagen / Foto')),
                ('fecha_registro', models.DateTimeField(auto_now_add=True)),
                ('propietario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mascotas', to=settings.AUTH_USER_MODEL, verbose_name='Dueno/Propietario')),
            ],
            options={
                'verbose_name': 'Mascota',
                'verbose_name_plural': 'Mascotas',
                'ordering': ['nombre'],
            },
        ),
        migrations.CreateModel(
            name='Cita',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField(verbose_name='Fecha de Atencion')),
                ('hora', models.TimeField(verbose_name='Hora de Atencion')),
                ('estado', models.CharField(choices=[('PENDIENTE', 'Pendiente de Confirmacion'), ('CONFIRMADA', 'Confirmada'), ('ATENDIDA', 'Servicio Atendido'), ('CANCELADA', 'Cancelada')], default='PENDIENTE', max_length=20, verbose_name='Estado de la Cita')),
                ('notas', models.TextField(blank=True, null=True, verbose_name='Observaciones o Requerimientos')),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('propietario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='citas', to=settings.AUTH_USER_MODEL, verbose_name='Cliente')),
                ('mascota', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='citas', to='citas.mascota', verbose_name='Mascota')),
                ('servicio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='citas', to='citas.servicio', verbose_name='Servicio Requerido')),
            ],
            options={
                'verbose_name': 'Cita',
                'verbose_name_plural': 'Citas',
                'ordering': ['-fecha', '-hora'],
            },
        ),
    ]
