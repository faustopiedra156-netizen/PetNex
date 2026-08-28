from django.db import migrations, models
import django.db.models.deletion


def asignar_administradores_existentes(apps, schema_editor):
    Negocio = apps.get_model('citas', 'Negocio')
    UsuarioNegocio = apps.get_model('citas', 'UsuarioNegocio')

    for negocio in Negocio.objects.filter(
        propietario__isnull=False,
        activo=True,
    ).iterator():
        UsuarioNegocio.objects.get_or_create(
            usuario_id=negocio.propietario_id,
            negocio_id=negocio.pk,
            defaults={'rol': 'ADMIN_LOCAL', 'activo': True},
        )


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0023_mascota_negocio'),
    ]

    operations = [
        migrations.CreateModel(
            name='UsuarioNegocio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rol', models.CharField(choices=[('ADMIN_LOCAL', 'Administrador del local'), ('EMPLEADO', 'Empleado')], default='ADMIN_LOCAL', max_length=20)),
                ('activo', models.BooleanField(default=True, verbose_name='Activo')),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('negocio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='usuarios_asignados', to='citas.negocio', verbose_name='Negocio')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='asignaciones_negocio', to='auth.user', verbose_name='Usuario')),
            ],
            options={
                'verbose_name': 'Usuario del negocio',
                'verbose_name_plural': 'Usuarios de los negocios',
            },
        ),
        migrations.AddConstraint(
            model_name='usuarionegocio',
            constraint=models.UniqueConstraint(fields=('usuario', 'negocio'), name='usuario_negocio_unico'),
        ),
        migrations.AddIndex(
            model_name='usuarionegocio',
            index=models.Index(fields=['negocio', 'activo'], name='usuario_negocio_activo_idx'),
        ),
        migrations.AddIndex(
            model_name='usuarionegocio',
            index=models.Index(fields=['usuario', 'activo'], name='usuario_negocio_usuario_idx'),
        ),
        migrations.RunPython(asignar_administradores_existentes, migrations.RunPython.noop),
    ]
