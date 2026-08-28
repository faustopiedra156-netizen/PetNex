# Sistema Django para peluqueria y estetica de mascotas

Proyecto web parametrizable para locales de peluqueria, spa y estetica de mascotas, desarrollado solo con Django y plantillas HTML. No usa React, Vite ni Node.

## Funciones incluidas

- Pagina publica de inicio y catalogo de servicios.
- Registro, inicio y cierre de sesion.
- Registro, edicion y eliminacion de mascotas.
- Reserva, consulta y cancelacion de citas.
- Seguimiento del estado de atencion de la mascota.
- Calificacion del servicio con estrellas.
- Metodos de pago: transferencia, pago fisico y tarjeta mediante Datafast.
- Panel de administracion para gestionar citas y activar/desactivar servicios.
- Administracion avanzada mediante `/admin/`.
- Diseno adaptable para computador y celular.

## 1. Crear el entorno en Windows PowerShell

```powershell
cd C:\Users\piedr\Documents\Cuarto\PetCare
py -m venv venv
.\venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
pip install -r requirements.txt
```

Si PowerShell bloquea la activacion:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

## 2. Crear la base de datos

```powershell
py manage.py makemigrations
py manage.py migrate
```

Si aparece un error como `relation "citas_calificacion" does not exist`, significa que falta aplicar migraciones en la base de datos activa. Ejecuta:

```powershell
py manage.py showmigrations citas
py manage.py migrate
```

La migracion `citas.0006_calificacion` debe quedar marcada con `[X]`.

## 3. Cargar datos de ejemplo

```powershell
py manage.py seed_data
```

Usuarios demo:

- Admin: `admin` / `admin123`
- Cliente: `juanperez` / `cliente123`

## 4. Crear un administrador propio

```powershell
py manage.py createsuperuser
```

## 5. Ejecutar el servidor

```powershell
py manage.py runserver 8081
```

Abrir en el navegador:

- Sitio: `http://127.0.0.1:8081/`
- Administracion Django: `http://127.0.0.1:8081/admin/`

## Pagos reales

Transferencia y pago fisico funcionan dentro del sistema. Para tarjetas reales se requiere una cuenta de comercio Datafast y sus credenciales:

```powershell
$env:DATAFAST_BASE_URL="https://test.oppwa.com"
$env:DATAFAST_ENTITY_ID="TU_ENTITY_ID"
$env:DATAFAST_AUTHORIZATION="TU_BEARER_TOKEN"
$env:DATAFAST_BRANDS="VISA MASTER AMEX DINERS DISCOVER"
```

Tambien puedes configurar los datos de transferencia:

```powershell
$env:TRANSFER_BANK_NAME="Banco Pichincha"
$env:TRANSFER_ACCOUNT_NUMBER="0000000000"
$env:TRANSFER_ACCOUNT_OWNER="Nombre del negocio"
$env:TRANSFER_ACCOUNT_ID="0000000000000"
```

## Fotos en produccion

El almacenamiento local funciona para desarrollo, pero los archivos subidos a Render deben guardarse en un bucket S3 compatible para sobrevivir a nuevos despliegues. El proyecto acepta Supabase Storage usando su endpoint S3:

```env
AWS_STORAGE_BUCKET_NAME=nombre-del-bucket
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_ENDPOINT_URL=https://<project-ref>.storage.supabase.co/storage/v1/s3
AWS_S3_REGION_NAME=us-east-1
```

Si estas variables permanecen vacias, se usa `media/` localmente. Nunca guardes las credenciales en Git.

## Monitoreo y respaldos

Para registrar errores en produccion configura `SENTRY_DSN` y `SENTRY_TRACES_SAMPLE_RATE` en Render. Activa los respaldos automáticos de la base PostgreSQL desde el panel del proveedor y realiza una restauracion de prueba antes del lanzamiento.

## Parametrizar el negocio

La identidad del local se configura desde `.env`, sin editar templates:

```env
BUSINESS_NAME=Nombre del local
BUSINESS_SHORT_NAME=Nombre corto
BUSINESS_CITY=Ciudad
BUSINESS_COUNTRY=Pais
BUSINESS_COUNTRY_CODE=EC
BUSINESS_CATEGORY=peluqueria y estetica para mascotas
BUSINESS_TAGLINE=Cuidado profesional para mascotas
BUSINESS_HERO_BADGE=Peluqueria y estetica para mascotas en Ciudad, Pais
BUSINESS_HERO_TITLE=Bano, corte y carino para tu mascota.
BUSINESS_HERO_DESCRIPTION=Descripcion comercial del local
BUSINESS_FOOTER_DESCRIPTION=Descripcion breve para el pie de pagina
BUSINESS_CONTACT_EMAIL=contacto@negocio.com
BUSINESS_CONTACT_PHONE=+593 99 999 9999
BUSINESS_ADDRESS=Direccion del local
BUSINESS_OPENING_HOURS=Lun - Sab: 08:30 - 18:30
BUSINESS_CURRENCY=USD
BUSINESS_CURRENCY_SYMBOL=$
BUSINESS_REVIEW_LABEL=Resenas de clientes
BUSINESS_LOCATION_LABEL=Sector del local
BUSINESS_PRIMARY_CTA=Agendar cita
BUSINESS_SHOW_DEMO_ACCOUNTS=False
BUSINESS_TRANSACTION_PREFIX=NEGOCIO
```

## Despliegue en produccion

Antes de subir o reiniciar el sitio en produccion:

```powershell
pip install -r requirements.txt
py manage.py check --deploy
py manage.py migrate
```

En Supabase o cualquier PostgreSQL, verifica que `DATABASE_URL` apunte a la base correcta antes de ejecutar `migrate`. Si usas un panel como Render, Railway o similar, agrega `py manage.py migrate` como comando de release o ejecútalo en la consola del servicio despues de cada despliegue con cambios de modelos.

## Estructura principal

```text
PetCare/
|-- manage.py
|-- requirements.txt
|-- petcare_loja/          # configuracion general del proyecto
|-- citas/                 # modelos, formularios, vistas y rutas
|-- templates/             # paginas HTML
`-- static/css/            # estilos propios
```

Todos los comandos `py manage.py ...` deben ejecutarse desde la carpeta donde esta `manage.py`.
