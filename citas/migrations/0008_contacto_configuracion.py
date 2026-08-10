from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0007_configuracionnegocio'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracionnegocio',
            name='contacto_titulo',
            field=models.CharField(default='Estamos listos para atender a tu mascota', max_length=180),
        ),
        migrations.AddField(
            model_name='configuracionnegocio',
            name='contacto_descripcion',
            field=models.TextField(default='Escribenos para consultar disponibilidad, servicios especiales o cuidados antes de una cita.'),
        ),
    ]
