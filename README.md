# PetCare Loja - Django desde cero

Proyecto web para la peluqueria canina PetCare Loja, desarrollado solo con Django, plantillas HTML y estilos por CDN. No usa React, Vite ni Node.

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
$env:TRANSFER_ACCOUNT_OWNER="PetCare Loja"
$env:TRANSFER_ACCOUNT_ID="0000000000000"
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
