# Puesta en marcha de PetNexo para un local

Este documento describe los pasos minimos para operar PetNexo con un local real
en Render. No guardes claves, tokens ni contrasenas en Git.

## 1. Configurar Render

En el servicio web abre `Environment` y confirma estas variables:

```env
DEBUG=False
RENDER=True
USE_SQLITE_LOCAL=False
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

`DATABASE_URL` debe provenir de PostgreSQL y `REDIS_URL` de Render Key Value.
El archivo `render.yaml` ya declara ambas relaciones para nuevos despliegues
mediante Blueprint. Si el servicio ya existia antes, comprueba que esten creadas
en el panel de Render.

Configura tambien los secretos que Render no puede inventar:

```env
BREVO_API_KEY=tu_clave_de_brevo
BREVO_SENDER_EMAIL=notificaciones@tu-dominio.com
DEFAULT_FROM_EMAIL=notificaciones@tu-dominio.com
ADMIN_NOTIFICATION_EMAIL=correo-del-dueno-del-local@tu-dominio.com
```

Opcionales, pero recomendados:

```env
SENTRY_DSN=tu_dsn_de_sentry
GOOGLE_LOGIN_ENABLED=True
GOOGLE_CLIENT_ID=tu_cliente_google
GOOGLE_CLIENT_SECRET=tu_secreto_google
```

Para demostraciones academicas se puede usar `SIMULATE_PAYMENTS=True`. Para
cobros reales usa `SIMULATE_PAYMENTS=False` y completa las credenciales
comerciales de Datafast. Nunca uses la simulacion como comprobante bancario.

## 2. Desplegar cambios

Desde la carpeta del proyecto ejecuta:

```powershell
git add citas/services.py citas/views.py citas/tests.py petcare_loja/settings.py render.yaml docs/OPERACION_LOCAL_RENDER.md
git commit -m "Refuerza operacion de Render para locales"
git push origin main
```

Render ejecuta las migraciones antes de iniciar Gunicorn. Cuando termine el
despliegue, abre:

```text
https://TU-SERVICIO.onrender.com/health/
```

Debe devolver `database: ok`. `cache: degraded` no bloquea el sitio, pero debes
revisar que el servicio Key Value este creado y enlazado para recuperar el
rendimiento compartido entre procesos.

## 3. Configurar el primer local

1. Ingresa con el dueno de PetNexo.
2. Crea el administrador del local desde `Panel Admin > Cuentas del sistema`.
3. Ingresa con ese administrador.
4. En `Panel Admin > Configuracion` registra nombre, telefono, correo,
   direccion, mapa, horario y dias cerrados.
5. Crea las sucursales del local.
6. Crea servicios con precio, duracion, categoria y visibilidad.
7. Realiza una reserva de prueba con una cuenta cliente.

Cada administrador local solo puede operar los datos de su negocio. Los clientes
solo ven sus propias mascotas, citas, pagos y seguimiento.

## 4. Validacion antes de abrir al publico

Comprueba estos flujos en el sitio ya desplegado:

- Registro e inicio de sesion con usuario o correo.
- Recuperacion de contrasena y llegada del codigo a un correo real.
- Registro de mascota con foto opcional.
- Reserva por sucursal y bloqueo de horarios ocupados.
- Cambio de estado y seguimiento desde el administrador local.
- Pago simulado aprobado y rechazado, si aun no se dispone de Datafast.
- Restricciones entre dueno de PetNexo, administrador local y cliente final.

Activa copias de seguridad de PostgreSQL en Render y configura un dominio propio
antes de anunciar el sistema. Las fotos de produccion deben usar almacenamiento
externo S3 compatible; el disco local de Render no es persistente.
