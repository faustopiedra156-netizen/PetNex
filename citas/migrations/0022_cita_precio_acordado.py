from django.db import migrations, models


def copiar_precios_actuales(apps, schema_editor):
    Cita = apps.get_model('citas', 'Cita')
    for cita in Cita.objects.select_related('servicio').filter(precio_acordado__isnull=True).iterator():
        cita.precio_acordado = cita.servicio.precio
        cita.save(update_fields=['precio_acordado'])


class Migration(migrations.Migration):
    dependencies = [
        ('citas', '0021_mascota_foto'),
    ]

    operations = [
        migrations.AddField(
            model_name='cita',
            name='precio_acordado',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=6,
                null=True,
                verbose_name='Precio acordado',
            ),
        ),
        migrations.RunPython(copiar_precios_actuales, migrations.RunPython.noop),
    ]
