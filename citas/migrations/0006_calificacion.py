import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0005_cita_referencias_pago'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Calificacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('puntuacion', models.PositiveSmallIntegerField(choices=[(1, '1 estrella - Mala'), (2, '2 estrellas - Regular'), (3, '3 estrellas - Buena'), (4, '4 estrellas - Muy buena'), (5, '5 estrellas - Excelente')], verbose_name='Puntuación')),
                ('comentario', models.TextField(blank=True, verbose_name='Comentario')),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('cita', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='calificacion', to='citas.cita', verbose_name='Cita')),
                ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='calificaciones', to=settings.AUTH_USER_MODEL, verbose_name='Cliente')),
            ],
            options={
                'verbose_name': 'Calificación',
                'verbose_name_plural': 'Calificaciones',
                'ordering': ['-creado_en'],
            },
        ),
    ]
