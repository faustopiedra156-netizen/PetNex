from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0002_alter_cita_estado_alter_cita_fecha_alter_cita_hora_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='cita',
            name='actualizado_seguimiento',
            field=models.DateTimeField(auto_now=True, verbose_name='Última actualización de seguimiento'),
        ),
        migrations.AddField(
            model_name='cita',
            name='etapa_seguimiento',
            field=models.CharField(choices=[('AGENDADA', 'Cita agendada'), ('RECIBIDA', 'Mascota recibida'), ('BANO', 'Baño y limpieza'), ('SECADO', 'Secado y cepillado'), ('CORTE', 'Corte y estilizado'), ('REVISION', 'Revisión final'), ('LISTA', 'Lista para retirar'), ('ENTREGADA', 'Entregada')], default='AGENDADA', max_length=20, verbose_name='Etapa de seguimiento'),
        ),
        migrations.AddField(
            model_name='cita',
            name='nota_seguimiento',
            field=models.TextField(blank=True, null=True, verbose_name='Nota visible para el cliente'),
        ),
        migrations.AddField(
            model_name='cita',
            name='progreso',
            field=models.PositiveIntegerField(default=0, verbose_name='Progreso (%)'),
        ),
    ]
