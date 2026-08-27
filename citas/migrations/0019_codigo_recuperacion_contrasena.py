# Generated manually for the password recovery code workflow.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0018_alter_configuracionnegocio_categoria_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CodigoRecuperacionContrasena',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo_hash', models.CharField(max_length=128, verbose_name='Codigo cifrado')),
                ('expira_en', models.DateTimeField(verbose_name='Expira en')),
                ('intentos', models.PositiveSmallIntegerField(default=0, verbose_name='Intentos realizados')),
                ('usado_en', models.DateTimeField(blank=True, null=True, verbose_name='Usado en')),
                ('creado_en', models.DateTimeField(auto_now_add=True, verbose_name='Creado en')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='codigos_recuperacion_contrasena', to=settings.AUTH_USER_MODEL, verbose_name='Usuario')),
            ],
            options={
                'verbose_name': 'Codigo de recuperacion de contrasena',
                'verbose_name_plural': 'Codigos de recuperacion de contrasena',
                'ordering': ['-creado_en'],
            },
        ),
        migrations.AddIndex(
            model_name='codigorecuperacioncontrasena',
            index=models.Index(fields=['usuario', 'expira_en'], name='citas_codig_usuario_9be51c_idx'),
        ),
    ]
