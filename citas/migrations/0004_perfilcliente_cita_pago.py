import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0003_cita_seguimiento'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PerfilCliente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('telefono', models.CharField(blank=True, max_length=20, verbose_name='Teléfono')),
                ('direccion', models.CharField(blank=True, max_length=180, verbose_name='Dirección')),
                ('barrio', models.CharField(blank=True, max_length=80, verbose_name='Barrio o sector')),
                ('contacto_preferido', models.CharField(choices=[('whatsapp', 'WhatsApp'), ('llamada', 'Llamada'), ('email', 'Email')], default='whatsapp', max_length=20, verbose_name='Contacto preferido')),
                ('usuario', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='perfil_cliente', to=settings.AUTH_USER_MODEL, verbose_name='Usuario')),
            ],
            options={
                'verbose_name': 'Perfil de cliente',
                'verbose_name_plural': 'Perfiles de clientes',
            },
        ),
        migrations.AddField(
            model_name='cita',
            name='estado_pago',
            field=models.CharField(choices=[('PENDIENTE', 'Pendiente'), ('ABONADO', 'Abonado'), ('PAGADO', 'Pagado')], default='PENDIENTE', max_length=20, verbose_name='Estado de pago'),
        ),
        migrations.AddField(
            model_name='cita',
            name='metodo_pago',
            field=models.CharField(choices=[('EFECTIVO', 'Efectivo'), ('TRANSFERENCIA', 'Transferencia'), ('TARJETA', 'Tarjeta')], default='EFECTIVO', max_length=20, verbose_name='Método de pago'),
        ),
    ]
