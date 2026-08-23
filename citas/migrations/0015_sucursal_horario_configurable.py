from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0014_multi_negocio_base'),
    ]

    operations = [
        migrations.AddField(
            model_name='sucursal',
            name='hora_apertura',
            field=models.TimeField(default='08:30', verbose_name='Hora de apertura'),
        ),
        migrations.AddField(
            model_name='sucursal',
            name='hora_cierre',
            field=models.TimeField(default='18:30', verbose_name='Hora de cierre'),
        ),
        migrations.AddField(
            model_name='sucursal',
            name='intervalo_turnos',
            field=models.PositiveIntegerField(default=30, verbose_name='Intervalo de turnos en minutos'),
        ),
        migrations.AddField(
            model_name='sucursal',
            name='dias_cerrados',
            field=models.CharField(
                blank=True,
                default='6',
                help_text='Numeros separados por coma: 0=lunes, 1=martes, 2=miercoles, 3=jueves, 4=viernes, 5=sabado, 6=domingo.',
                max_length=30,
                verbose_name='Dias cerrados',
            ),
        ),
    ]
