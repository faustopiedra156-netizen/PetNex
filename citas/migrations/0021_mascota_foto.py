# Generated manually for optional device photo uploads.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0020_mensajecontacto_optimizacion_indices'),
    ]

    operations = [
        migrations.AddField(
            model_name='mascota',
            name='foto',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='mascotas/%Y/%m/',
                verbose_name='Foto de la mascota',
            ),
        ),
    ]
