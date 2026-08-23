from django.db import migrations


def crear_tabla_calificacion_si_falta(apps, schema_editor):
    Calificacion = apps.get_model("citas", "Calificacion")

    nombre_tabla = Calificacion._meta.db_table

    tablas_existentes = (
        schema_editor.connection.introspection.table_names()
    )

    if nombre_tabla not in tablas_existentes:
        schema_editor.create_model(Calificacion)


class Migration(migrations.Migration):

    dependencies = [
        ("citas", "0009_sucursal_cita_sucursal"),
    ]

    operations = [
        migrations.RunPython(
            crear_tabla_calificacion_si_falta,
            migrations.RunPython.noop,
        ),
    ]
