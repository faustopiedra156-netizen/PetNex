from django.db import migrations, models
import django.db.models.deletion


def crear_sucursal_principal(apps, schema_editor):
    ConfiguracionNegocio = apps.get_model('citas', 'ConfiguracionNegocio')
    Sucursal = apps.get_model('citas', 'Sucursal')
    Cita = apps.get_model('citas', 'Cita')

    config = ConfiguracionNegocio.objects.order_by('id').first()
    nombre = f"{config.nombre_corto} Principal" if config else "Sucursal Principal"
    ciudad = config.ciudad if config else "Quito"
    direccion = config.direccion if config else "Direccion principal"
    telefono = config.telefono if config else ""

    sucursal, _ = Sucursal.objects.get_or_create(
        nombre=nombre,
        defaults={
            'ciudad': ciudad,
            'direccion': direccion,
            'telefono': telefono,
            'activa': True,
        },
    )
    Cita.objects.filter(sucursal__isnull=True).update(sucursal=sucursal)


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0008_contacto_configuracion'),
    ]

    operations = [
        migrations.CreateModel(
            name='Sucursal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=120, verbose_name='Nombre de la sucursal')),
                ('ciudad', models.CharField(max_length=80, verbose_name='Ciudad')),
                ('direccion', models.CharField(max_length=180, verbose_name='Direccion')),
                ('telefono', models.CharField(blank=True, max_length=30, verbose_name='Telefono')),
                ('activa', models.BooleanField(default=True, verbose_name='Activa')),
                ('creada_en', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Sucursal',
                'verbose_name_plural': 'Sucursales',
                'ordering': ['nombre'],
            },
        ),
        migrations.AddField(
            model_name='cita',
            name='sucursal',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='citas', to='citas.sucursal', verbose_name='Sucursal'),
        ),
        migrations.RunPython(crear_sucursal_principal, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='cita',
            name='sucursal',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='citas', to='citas.sucursal', verbose_name='Sucursal'),
        ),
    ]
