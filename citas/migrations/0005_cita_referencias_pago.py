from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0004_perfilcliente_cita_pago'),
    ]

    operations = [
        migrations.AddField(
            model_name='cita',
            name='datafast_checkout_id',
            field=models.CharField(blank=True, max_length=180, verbose_name='Checkout ID Datafast'),
        ),
        migrations.AddField(
            model_name='cita',
            name='datafast_resource_path',
            field=models.CharField(blank=True, max_length=255, verbose_name='Resource path Datafast'),
        ),
        migrations.AddField(
            model_name='cita',
            name='datafast_result_code',
            field=models.CharField(blank=True, max_length=60, verbose_name='Código de respuesta Datafast'),
        ),
        migrations.AddField(
            model_name='cita',
            name='referencia_pago',
            field=models.CharField(blank=True, max_length=120, verbose_name='Referencia de pago'),
        ),
    ]
