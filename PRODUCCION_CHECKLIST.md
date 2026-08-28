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

## 7. Fotos y almacenamiento persistente

Render no debe usarse como almacenamiento permanente para las fotos subidas por los usuarios. El proyecto admite un bucket S3 compatible, incluido Supabase Storage mediante su endpoint S3.

Configura estas variables solo despues de crear el bucket y sus credenciales:

```env
AWS_STORAGE_BUCKET_NAME=nombre-del-bucket
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_ENDPOINT_URL=https://<project-ref>.storage.supabase.co/storage/v1/s3
AWS_S3_REGION_NAME=us-east-1
```

El bucket debe permitir lectura de los objetos que se muestran en la ficha de mascota. No subas las credenciales al repositorio.

## 8. Errores y monitoreo

Configura un proyecto de Sentry y agrega su DSN en Render:

```env
SENTRY_DSN=https://...@sentry.io/...
SENTRY_TRACES_SAMPLE_RATE=0.05
```

El proyecto no envía datos personales completos a Sentry (`send_default_pii=False`).

## 9. Copias de seguridad

Activa las copias automáticas y la retención disponibles en el panel de PostgreSQL de Render. Antes de una migración importante, crea un respaldo manual y conserva al menos una copia fuera de Render. Prueba una restauración en una base separada antes de depender del respaldo.

## 10. Revisión antes de abrir al público

- `DEBUG=False`, `RENDER=True` y `USE_SQLITE_LOCAL=False` en Render.
- `SECRET_KEY` generada por Render y nunca incluida en Git.
- `CSRF_TRUSTED_ORIGINS` con el dominio definitivo.
- `EMAIL_BACKEND` configurado con Brevo, Resend o SMTP real.
- `SIMULATE_PAYMENTS=True` solo para demostraciones; usar `False` cuando Datafast esté validado.
- Dominio personalizado, HTTPS activo y correo corporativo verificados.
- Ejecutar `python manage.py check --deploy` y `python manage.py test` despues de cada cambio.
