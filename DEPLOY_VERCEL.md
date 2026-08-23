# Despliegue de PetNexo en Vercel para pruebas

## 1. Variables obligatorias en Vercel

Configura estas variables en Project Settings > Environment Variables:

```env
DEBUG=False
SECRET_KEY=coloca-una-clave-larga-segura-de-mas-de-50-caracteres
DATABASE_URL=postgresql://usuario:password@host:puerto/postgres
APP_NAME=PetNexo
ALLOWED_HOSTS=.vercel.app
CSRF_TRUSTED_ORIGINS=https://*.vercel.app
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
```

Para Supabase usa la URL del Session Pooler o Transaction Pooler. No uses SQLite en Vercel para pruebas reales.

## 2. Migraciones en Supabase

Antes o despues del despliegue, aplica las migraciones contra Supabase desde tu equipo:

```powershell
$env:DATABASE_URL="postgresql://usuario:password@host:puerto/postgres"
$env:DEBUG="False"
py manage.py migrate
```

Antes de aplicar la migracion de restriccion de horarios, revisa que no existan citas activas duplicadas en la misma sucursal, fecha y hora. Si existen, cancela o reprograma una de ellas desde el panel.

Si quieres cargar datos iniciales:

```powershell
py manage.py seed_data
```

## 3. Publicar cambios

```powershell
git add .
git commit -m "Prepara despliegue en Vercel"
git push origin main
```

Vercel desplegara automaticamente desde la rama `main`.

## 4. Validacion rapida

Revisa estas rutas:

- `/`
- `/health/`
- `/servicios/`
- `/registro/`
- `/login/`
- `/citas/agendar/`
- `/gestion/`
- `/admin/`

Primero abre `/health/`. Si responde `database: ok`, Django ya conecta con Supabase.
Si responde `database: error`, falta revisar `DATABASE_URL` o ejecutar migraciones.

Si aparece `Server Error (500)`, abre **Vercel > Deployment > Logs** y revisa el error exacto.
