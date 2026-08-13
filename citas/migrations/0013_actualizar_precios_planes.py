from decimal import Decimal

from django.db import migrations


def actualizar_precios_planes(apps, schema_editor):
    PlanSuscripcion = apps.get_model('citas', 'PlanSuscripcion')
    precios = {
        'Basico': Decimal('25.00'),
        'Pro': Decimal('45.00'),
        'Premium': Decimal('75.00'),
    }
    for nombre, precio in precios.items():
        PlanSuscripcion.objects.filter(nombre=nombre).update(precio_mensual=precio)


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0012_pago_suscripcion'),
    ]

    operations = [
        migrations.RunPython(actualizar_precios_planes, migrations.RunPython.noop),
    ]
