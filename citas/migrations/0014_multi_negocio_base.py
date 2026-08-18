from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def crear_negocio_inicial(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Negocio = apps.get_model('citas', 'Negocio')
    ConfiguracionNegocio = apps.get_model('citas', 'ConfiguracionNegocio')
    Servicio = apps.get_model('citas', 'Servicio')
    Sucursal = apps.get_model('citas', 'Sucursal')
    PerfilCliente = apps.get_model('citas', 'PerfilCliente')
    Cita = apps.get_model('citas', 'Cita')
    SuscripcionNegocio = apps.get_model('citas', 'SuscripcionNegocio')

    config = ConfiguracionNegocio.objects.order_by('id').first()
    propietario = User.objects.filter(is_staff=True, is_superuser=False).order_by('id').first()
    nombre = getattr(config, 'nombre', '') or getattr(settings, 'BUSINESS_NAME', 'PetNexo Local')

    negocio, _ = Negocio.objects.get_or_create(
        nombre=nombre,
        defaults={'propietario': propietario, 'activo': True},
    )
    if propietario and negocio.propietario_id != propietario.id:
        negocio.propietario = propietario
        negocio.save(update_fields=['propietario'])

    if config and not config.negocio_id:
        config.negocio = negocio
        config.save(update_fields=['negocio'])

    Servicio.objects.filter(negocio__isnull=True).update(negocio=negocio)
    Sucursal.objects.filter(negocio__isnull=True).update(negocio=negocio)
    PerfilCliente.objects.filter(negocio__isnull=True).update(negocio=negocio)
    Cita.objects.filter(negocio__isnull=True).update(negocio=negocio)
    SuscripcionNegocio.objects.filter(negocio__isnull=True).update(negocio=negocio)


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0013_actualizar_precios_planes'),
    ]

    operations = [
        migrations.CreateModel(
            name='Negocio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=120, verbose_name='Nombre del negocio')),
                ('activo', models.BooleanField(default=True, verbose_name='Activo')),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('propietario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='negocios_administrados', to=settings.AUTH_USER_MODEL, verbose_name='Administrador del local')),
            ],
            options={
                'verbose_name': 'Negocio',
                'verbose_name_plural': 'Negocios',
                'ordering': ['nombre'],
            },
        ),
        migrations.AddField(
            model_name='configuracionnegocio',
            name='negocio',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='configuracion', to='citas.negocio', verbose_name='Negocio'),
        ),
        migrations.AddField(
            model_name='servicio',
            name='negocio',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='servicios', to='citas.negocio', verbose_name='Negocio'),
        ),
        migrations.AddField(
            model_name='sucursal',
            name='negocio',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sucursales', to='citas.negocio', verbose_name='Negocio'),
        ),
        migrations.AddField(
            model_name='perfilcliente',
            name='negocio',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='clientes', to='citas.negocio', verbose_name='Negocio principal'),
        ),
        migrations.AddField(
            model_name='cita',
            name='negocio',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='citas', to='citas.negocio', verbose_name='Negocio'),
        ),
        migrations.AddField(
            model_name='suscripcionnegocio',
            name='negocio',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='suscripciones', to='citas.negocio', verbose_name='Negocio'),
        ),
        migrations.RunPython(crear_negocio_inicial, migrations.RunPython.noop),
    ]
