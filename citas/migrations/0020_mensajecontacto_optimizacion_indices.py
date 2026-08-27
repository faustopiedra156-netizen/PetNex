import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0019_codigo_recuperacion_contrasena'),
    ]

    operations = [
        migrations.CreateModel(
            name='MensajeContacto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=120)),
                ('telefono', models.CharField(max_length=30)),
                ('mensaje', models.TextField(max_length=1500)),
                ('atendido', models.BooleanField(default=False)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('negocio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mensajes_contacto', to='citas.negocio')),
            ],
            options={
                'verbose_name': 'Mensaje de contacto',
                'verbose_name_plural': 'Mensajes de contacto',
                'ordering': ['atendido', '-creado_en'],
            },
        ),
        migrations.AddIndex(
            model_name='servicio',
            index=models.Index(fields=['negocio', 'activo', 'categoria'], name='servicio_catalogo_idx'),
        ),
        migrations.AddIndex(
            model_name='sucursal',
            index=models.Index(fields=['negocio', 'activa'], name='sucursal_negocio_activa_idx'),
        ),
        migrations.AddIndex(
            model_name='cita',
            index=models.Index(fields=['negocio', 'fecha'], name='cita_negocio_fecha_idx'),
        ),
        migrations.AddIndex(
            model_name='cita',
            index=models.Index(fields=['negocio', 'estado', 'fecha'], name='cita_estado_fecha_idx'),
        ),
        migrations.AddIndex(
            model_name='cita',
            index=models.Index(fields=['propietario', 'fecha'], name='cita_cliente_fecha_idx'),
        ),
        migrations.AddIndex(
            model_name='cita',
            index=models.Index(fields=['negocio', 'creado_en'], name='cita_negocio_creada_idx'),
        ),
        migrations.AddIndex(
            model_name='mensajecontacto',
            index=models.Index(fields=['negocio', 'atendido', 'creado_en'], name='mensaje_contacto_estado_idx'),
        ),
    ]
