from django.db import migrations, models
import django.db.models.deletion


def asignar_negocio_a_mascotas(apps, schema_editor):
    Mascota = apps.get_model('citas', 'Mascota')
    PerfilCliente = apps.get_model('citas', 'PerfilCliente')
    Cita = apps.get_model('citas', 'Cita')

    for mascota in Mascota.objects.filter(negocio__isnull=True).iterator():
        cita_negocios = list(
            Cita.objects.filter(
                mascota_id=mascota.pk,
                negocio__isnull=False,
            )
            .values_list('negocio_id', flat=True)
            .distinct()[:2]
        )
        if len(cita_negocios) == 1:
            negocio_id = cita_negocios[0]
        elif cita_negocios:
            # An ambiguous legacy record stays isolated until an administrator
            # assigns it explicitly from Django Admin.
            negocio_id = None
        else:
            negocio_id = (
                PerfilCliente.objects.filter(
                    usuario_id=mascota.propietario_id,
                    negocio__isnull=False,
                )
                .values_list('negocio_id', flat=True)
                .first()
            )
        if negocio_id:
            Mascota.objects.filter(pk=mascota.pk).update(negocio_id=negocio_id)


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0022_cita_precio_acordado'),
    ]

    operations = [
        migrations.AddField(
            model_name='mascota',
            name='negocio',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='mascotas',
                to='citas.negocio',
                verbose_name='Negocio',
            ),
        ),
        migrations.AddIndex(
            model_name='mascota',
            index=models.Index(
                fields=['negocio', 'propietario'],
                name='mascota_negocio_prop_idx',
            ),
        ),
        migrations.RunPython(asignar_negocio_a_mascotas, migrations.RunPython.noop),
    ]
