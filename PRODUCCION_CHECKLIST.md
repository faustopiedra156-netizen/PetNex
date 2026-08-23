# Checklist de produccion PetNexo

Usa esta lista antes de publicar el sistema para clientes reales.

## 1. Variables obligatorias en Vercel

Configura estas variables en `Vercel > Project > Settings > Environment Variables`:

```env
DEBUG=False
SECRET_KEY=una-clave-larga-y-segura
APP_NAME=PetNexo
ALLOWED_HOSTS=.vercel.app,tu-dominio.com,www.tu-dominio.com
CSRF_TRUSTED_ORIGINS=https://*.vercel.app,https://tu-dominio.com,https://www.tu-dominio.com
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
DATABASE_URL=postgresql://...
```

## 2. Supabase

1. Crea el proyecto en Supabase.
2. Copia la URL del Session Pooler.
3. Pegala como `DATABASE_URL`.
4. Ejecuta migraciones:

```powershell
py manage.py migrate
```

Antes de migrar a produccion, revisa que no existan dos citas activas en la misma sucursal, fecha y hora. La restriccion `cita_horario_activo_unico_por_sucursal` bloqueara duplicados para proteger la agenda.

## 3. Google Login

En Google Cloud configura:

Origenes autorizados:

```text
http://127.0.0.1:8082
https://tu-dominio.com
https://tu-proyecto.vercel.app
```

Redirecciones autorizadas:

```text
http://127.0.0.1:8082/accounts/google/login/callback/
https://tu-dominio.com/accounts/google/login/callback/
https://tu-proyecto.vercel.app/accounts/google/login/callback/
```

Variables:

```env
GOOGLE_LOGIN_ENABLED=True
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

## 4. Correo real

Para recuperacion de contrasena y avisos:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-correo@gmail.com
EMAIL_HOST_PASSWORD=clave-de-aplicacion
DEFAULT_FROM_EMAIL=PetNexo <tu-correo@gmail.com>
ADMIN_NOTIFICATION_EMAIL=tu-correo@gmail.com
```

## 5. Pagos reales

Configura Datafast o el proveedor real:

```env
DATAFAST_BASE_URL=https://oppwa.com
DATAFAST_ENTITY_ID=...
DATAFAST_AUTHORIZATION=...
DATAFAST_BRANDS=VISA MASTER AMEX DINERS DISCOVER
```

Antes de vender, prueba pagos con montos pequenos y confirma que el dinero llegue a tu cuenta comercial.

## 6. Pruebas minimas

- Registro de cliente.
- Login normal.
- Login con Google.
- Recuperacion de contrasena por correo.
- Crear mascota.
- Crear sucursal y horarios.
- Agendar cita.
- Bloqueo de horarios ocupados.
- Seguimiento de mascota.
- Pago de cita.
- Pago de suscripcion.
- Crear y eliminar cuentas desde dueño PetNexo.
- Politica de privacidad, terminos y soporte visibles en el footer.
