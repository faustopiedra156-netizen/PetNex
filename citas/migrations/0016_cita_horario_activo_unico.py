from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0015_sucursal_horario_configurable'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='cita',
            constraint=models.UniqueConstraint(
                condition=models.Q(('estado', 'CANCELADA'), _negated=True),
                fields=('sucursal', 'fecha', 'hora'),
                name='cita_horario_activo_unico_por_sucursal',
            ),
        ),
    ]
