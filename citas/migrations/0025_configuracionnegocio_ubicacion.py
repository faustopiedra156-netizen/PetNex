from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0024_usuario_negocio_roles'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracionnegocio',
            name='latitud',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name='Latitud del local'),
        ),
        migrations.AddField(
            model_name='configuracionnegocio',
            name='longitud',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name='Longitud del local'),
        ),
    ]
