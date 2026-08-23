from django.db import migrations


def corregir_textos_configuracion(apps, schema_editor):
    ConfiguracionNegocio = apps.get_model('citas', 'ConfiguracionNegocio')

    correcciones = {
        'categoria': 'peluquer\u00eda y est\u00e9tica para mascotas',
        'hero_badge': 'Peluquer\u00eda y est\u00e9tica para mascotas en Loja, Ecuador',
        'hero_titulo': 'Ba\u00f1o, corte y cari\u00f1o para tu mascota.',
        'hero_descripcion': 'Ofrecemos ba\u00f1os, cortes, tratamientos de higiene y cuidado est\u00e9tico con atenci\u00f3n personalizada.',
        'descripcion_footer': 'Centro especializado en est\u00e9tica, peluquer\u00eda y spa para mascotas. Cuidamos a tu compa\u00f1ero con amor, higiene y atenci\u00f3n profesional.',
        'etiqueta_resenas': 'Rese\u00f1as de clientes',
    }

    textos_danados = {
        'Bano': 'Ba\u00f1o',
        'banos': 'ba\u00f1os',
        'carino': 'cari\u00f1o',
        'Peluqueria': 'Peluquer\u00eda',
        'peluqueria': 'peluquer\u00eda',
        'estetica': 'est\u00e9tica',
        'estetico': 'est\u00e9tico',
        'atencion': 'atenci\u00f3n',
        'companero': 'compa\u00f1ero',
        'Resenas': 'Rese\u00f1as',
    }

    for config in ConfiguracionNegocio.objects.all():
        for campo, valor in correcciones.items():
            actual = getattr(config, campo, '') or ''
            if not actual or any(texto in actual for texto in textos_danados):
                setattr(config, campo, valor)
                continue

            for origen, destino in textos_danados.items():
                actual = actual.replace(origen, destino)
            setattr(config, campo, actual)
        config.save()


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0016_cita_horario_activo_unico'),
    ]

    operations = [
        migrations.RunPython(corregir_textos_configuracion, migrations.RunPython.noop),
    ]
