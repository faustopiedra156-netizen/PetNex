import datetime

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def crear_planes_iniciales(apps, schema_editor):
    PlanSuscripcion = apps.get_model('citas', 'PlanSuscripcion')
    SuscripcionNegocio = apps.get_model('citas', 'SuscripcionNegocio')

    basico, _ = PlanSuscripcion.objects.get_or_create(
        nombre='Basico',
        defaults={
            'precio_mensual': 25,
            'max_sucursales': 1,
            'max_citas_mes': 120,
            'permite_pagos': False,
            'permite_chatbot': True,
            'permite_reportes': False,
            'activo': True,
        },
    )
    PlanSuscripcion.objects.get_or_create(
        nombre='Pro',
        defaults={
            'precio_mensual': 45,
            'max_sucursales': 3,
            'max_citas_mes': 500,
            'permite_pagos': True,
            'permite_chatbot': True,
            'permite_reportes': True,
            'activo': True,
        },
    )
    PlanSuscripcion.objects.get_or_create(
        nombre='Premium',
        defaults={
            'precio_mensual': 75,
            'max_sucursales': 10,
            'max_citas_mes': 1500,
            'permite_pagos': True,
            'permite_chatbot': True,
            'permite_reportes': True,
            'activo': True,
        },
    )

    if not SuscripcionNegocio.objects.exists():
        hoy = django.utils.timezone.localdate()
        SuscripcionNegocio.objects.create(
            plan=basico,
            estado='DEMO',
            fecha_inicio=hoy,
            fecha_vencimiento=hoy + datetime.timedelta(days=30),
            contacto_pago='Administrador PetNexo',
            notas='Suscripcion demo creada automaticamente por migracion.',
        )


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0010_reparar_tabla_calificacion'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlanSuscripcion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=80, unique=True, verbose_name='Nombre del plan')),
                ('precio_mensual', models.DecimalField(decimal_places=2, default=0, max_digits=7, verbose_name='Precio mensual')),
                ('max_sucursales', models.PositiveIntegerField(default=1, verbose_name='Maximo de sucursales')),
                ('max_citas_mes', models.PositiveIntegerField(default=100, verbose_name='Maximo de citas por mes')),
                ('permite_pagos', models.BooleanField(default=False, verbose_name='Permite pagos')),
                ('permite_chatbot', models.BooleanField(default=True, verbose_name='Permite chatbot')),
                ('permite_reportes', models.BooleanField(default=False, verbose_name='Permite reportes avanzados')),
                ('activo', models.BooleanField(default=True, verbose_name='Activo')),
            ],
            options={
                'verbose_name': 'Plan de suscripcion',
                'verbose_name_plural': 'Planes de suscripcion',
                'ordering': ['precio_mensual', 'nombre'],
            },
        ),
        migrations.CreateModel(
            name='SuscripcionNegocio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estado', models.CharField(choices=[('ACTIVA', 'Activa'), ('VENCIDA', 'Vencida'), ('SUSPENDIDA', 'Suspendida'), ('DEMO', 'Demo')], default='DEMO', max_length=20, verbose_name='Estado')),
                ('fecha_inicio', models.DateField(default=django.utils.timezone.localdate, verbose_name='Fecha de inicio')),
                ('fecha_vencimiento', models.DateField(verbose_name='Fecha de vencimiento')),
                ('contacto_pago', models.CharField(blank=True, default='', max_length=120, verbose_name='Contacto para pago')),
                ('notas', models.TextField(blank=True, default='', verbose_name='Notas internas')),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='suscripciones', to='citas.plansuscripcion')),
            ],
            options={
                'verbose_name': 'Suscripcion del negocio',
                'verbose_name_plural': 'Suscripcion del negocio',
            },
        ),
        migrations.RunPython(crear_planes_iniciales, migrations.RunPython.noop),
    ]
