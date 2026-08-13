from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0011_planes_suscripcion'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PagoSuscripcion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ciclo_facturacion', models.CharField(choices=[('MENSUAL', 'Mensual'), ('ANUAL', 'Anual')], default='MENSUAL', max_length=20)),
                ('monto', models.DecimalField(decimal_places=2, max_digits=8)),
                ('estado', models.CharField(choices=[('PENDIENTE', 'Pendiente'), ('APROBADO', 'Aprobado'), ('RECHAZADO', 'Rechazado')], default='PENDIENTE', max_length=20)),
                ('metodo', models.CharField(default='TARJETA', max_length=20)),
                ('contacto_pago', models.CharField(blank=True, default='', max_length=120)),
                ('checkout_id', models.CharField(blank=True, default='', max_length=180)),
                ('datafast_resource_path', models.CharField(blank=True, default='', max_length=255)),
                ('datafast_result_code', models.CharField(blank=True, default='', max_length=60)),
                ('referencia', models.CharField(blank=True, default='', max_length=180)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pagos', to='citas.plansuscripcion', verbose_name='Plan')),
                ('suscripcion', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pagos', to='citas.suscripcionnegocio', verbose_name='Suscripcion')),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pagos_suscripcion', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Pago de suscripcion',
                'verbose_name_plural': 'Pagos de suscripcion',
                'ordering': ['-creado_en'],
            },
        ),
    ]
