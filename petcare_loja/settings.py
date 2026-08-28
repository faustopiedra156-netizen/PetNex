import json
import os
from importlib.util import find_spec
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent.parent
if load_dotenv:
    load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_list(name, default=''):
    return [item.strip() for item in os.getenv(name, default).split(',') if item.strip()]


def env_int(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def env_int_list(name, default=''):
    values = []
    for item in os.getenv(name, default).split(','):
        item = item.strip()
        if not item:
            continue
        try:
            values.append(int(item))
        except ValueError:
            continue
    return values


def env_float(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def env_json(name, default):
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return default
    return value if isinstance(value, type(default)) else default


DEBUG = env_bool('DEBUG', False)
IS_RENDER = env_bool('RENDER', False)
SECRET_KEY = os.getenv('SECRET_KEY', os.getenv('DJANGO_SECRET_KEY', ''))
APP_NAME = os.getenv('APP_NAME', 'PetNexo')
DEFAULT_EXCEPTION_REPORTER_FILTER = 'citas.exception_filters.PetNexoExceptionReporterFilter'

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-local-development-only'
    else:
        raise ImproperlyConfigured('Configura SECRET_KEY antes de publicar en produccion.')
if not DEBUG and SECRET_KEY.startswith('django-insecure-'):
    raise ImproperlyConfigured('Configura SECRET_KEY con una clave segura antes de publicar en produccion.')

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', '127.0.0.1,localhost')
CSRF_TRUSTED_ORIGINS = env_list(
    'CSRF_TRUSTED_ORIGINS',
    'http://127.0.0.1:8081,http://localhost:8081,http://127.0.0.1:8080,http://localhost:8080',
)

if env_bool('VERCEL', False):
    vercel_url = os.getenv('VERCEL_URL', '').strip()
    ALLOWED_HOSTS.extend(['.vercel.app'])
    CSRF_TRUSTED_ORIGINS.extend(['https://*.vercel.app'])
    if vercel_url:
        ALLOWED_HOSTS.append(vercel_url)
        CSRF_TRUSTED_ORIGINS.append(f'https://{vercel_url}')

render_host = os.getenv('RENDER_EXTERNAL_HOSTNAME', '').strip()
if render_host:
    ALLOWED_HOSTS.append(render_host)
    CSRF_TRUSTED_ORIGINS.append(f'https://{render_host}')

ALLOWED_HOSTS = list(dict.fromkeys(ALLOWED_HOSTS))
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(CSRF_TRUSTED_ORIGINS))
CSRF_FAILURE_VIEW = 'citas.views.csrf_failure'


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'citas.apps.CitasConfig',
]

WHITENOISE_AVAILABLE = find_spec('whitenoise') is not None

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'citas.middleware.SuperuserAdminOnlyMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

if WHITENOISE_AVAILABLE:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

ROOT_URLCONF = 'petcare_loja.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'citas.context_processors.business_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'petcare_loja.wsgi.application'

USE_SQLITE_LOCAL = env_bool('USE_SQLITE_LOCAL', False)
DATABASE_URL = '' if USE_SQLITE_LOCAL else os.getenv('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )
    }
    DATABASES['default']['CONN_HEALTH_CHECKS'] = True
    DATABASES['default'].setdefault('OPTIONS', {})['connect_timeout'] = env_int('DATABASE_CONNECT_TIMEOUT_SECONDS', 5)
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 10},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'es-ec'

TIME_ZONE = 'America/Guayaquil'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage' if WHITENOISE_AVAILABLE else 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

REDIS_URL = os.getenv('REDIS_URL', '').strip()
CACHE_DEFAULT_TIMEOUT = env_int('CACHE_DEFAULT_TIMEOUT', 300)
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'SOCKET_CONNECT_TIMEOUT': 2,
                'SOCKET_TIMEOUT': 2,
                'CONNECTION_POOL_KWARGS': {'max_connections': env_int('REDIS_MAX_CONNECTIONS', 50)},
            },
            'TIMEOUT': CACHE_DEFAULT_TIMEOUT,
            'KEY_PREFIX': 'petnexo',
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'petnexo-local',
            'TIMEOUT': CACHE_DEFAULT_TIMEOUT,
        }
    }
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_CACHE_ALIAS = 'default'

SENTRY_DSN = os.getenv('SENTRY_DSN', '').strip()
if SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        send_default_pii=False,
        traces_sample_rate=min(max(env_float('SENTRY_TRACES_SAMPLE_RATE', 0.05), 0), 1),
    )

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL = '/login/'

ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*']

# Desactiva el inicio de sesión por código enviado al correo.
# Para Google OAuth, el usuario debe entrar mediante el proveedor Google.
ACCOUNT_LOGIN_BY_CODE_ENABLED = False
ACCOUNT_LOGIN_BY_CODE_REQUIRED = False

PASSWORD_RESET_CODE_TTL_MINUTES = max(env_int('PASSWORD_RESET_CODE_TTL_MINUTES', 10), 1)
PASSWORD_RESET_CODE_MAX_ATTEMPTS = max(env_int('PASSWORD_RESET_CODE_MAX_ATTEMPTS', 5), 1)
PASSWORD_RESET_CODE_RESEND_SECONDS = max(env_int('PASSWORD_RESET_CODE_RESEND_SECONDS', 60), 1)

SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_ADAPTER = 'citas.adapters.PetNexoSocialAccountAdapter'

GOOGLE_LOGIN_ENABLED = env_bool('GOOGLE_LOGIN_ENABLED', False)
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '').strip()
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()
GOOGLE_LOGIN_CONFIGURED = GOOGLE_LOGIN_ENABLED and bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
            'prompt': 'select_account',
        },
        'OAUTH_PKCE_ENABLED': True,
    }
}

# Las credenciales vienen del entorno. No se registra una aplicacion vacia
# cuando Google aun no esta configurado.
if GOOGLE_LOGIN_CONFIGURED:
    SOCIALACCOUNT_PROVIDERS['google']['APP'] = {
        'client_id': GOOGLE_CLIENT_ID,
        'secret': GOOGLE_CLIENT_SECRET,
        'key': '',
    }

DATAFAST_BASE_URL = os.getenv('DATAFAST_BASE_URL', 'https://test.oppwa.com').rstrip('/')
DATAFAST_ENTITY_ID = os.getenv('DATAFAST_ENTITY_ID', '')
DATAFAST_AUTHORIZATION = os.getenv('DATAFAST_AUTHORIZATION', '')
DATAFAST_BRANDS = os.getenv('DATAFAST_BRANDS', 'VISA MASTER AMEX DINERS DISCOVER')
DATAFAST_TIMEOUT_SECONDS = env_int('DATAFAST_TIMEOUT_SECONDS', 10)
SIMULATE_PAYMENTS = env_bool('SIMULATE_PAYMENTS', False)

APPOINTMENT_OPEN_TIME = os.getenv('APPOINTMENT_OPEN_TIME', '08:30')
APPOINTMENT_CLOSE_TIME = os.getenv('APPOINTMENT_CLOSE_TIME', '18:30')
APPOINTMENT_SLOT_MINUTES = env_int('APPOINTMENT_SLOT_MINUTES', 30)
APPOINTMENT_CLOSED_WEEKDAYS = env_int_list('APPOINTMENT_CLOSED_WEEKDAYS', '6')
HOME_FEATURED_SERVICES_LIMIT = env_int('HOME_FEATURED_SERVICES_LIMIT', 4)
HOME_SERVICES_LIMIT = env_int('HOME_SERVICES_LIMIT', 6)
ADMIN_TODAY_APPOINTMENTS_LIMIT = env_int('ADMIN_TODAY_APPOINTMENTS_LIMIT', 8)

TRANSFER_BANK_NAME = os.getenv('TRANSFER_BANK_NAME', 'Banco Pichincha')
TRANSFER_ACCOUNT_NUMBER = os.getenv('TRANSFER_ACCOUNT_NUMBER', '0000000000')
TRANSFER_ACCOUNT_OWNER = os.getenv('TRANSFER_ACCOUNT_OWNER', 'PetCare Loja')
TRANSFER_ACCOUNT_ID = os.getenv('TRANSFER_ACCOUNT_ID', '0000000000000')

BUSINESS_NAME = os.getenv('BUSINESS_NAME', os.getenv('PETCARE_BUSINESS_NAME', 'PetCare Loja'))
BUSINESS_SHORT_NAME = os.getenv('BUSINESS_SHORT_NAME', BUSINESS_NAME.split()[0])
BUSINESS_CITY = os.getenv('BUSINESS_CITY', 'Loja')
BUSINESS_COUNTRY = os.getenv('BUSINESS_COUNTRY', 'Ecuador')
BUSINESS_COUNTRY_CODE = os.getenv('BUSINESS_COUNTRY_CODE', 'EC')
BUSINESS_CATEGORY = os.getenv('BUSINESS_CATEGORY', 'peluquería y estética para mascotas')
BUSINESS_TAGLINE = os.getenv('BUSINESS_TAGLINE', 'Cuidado profesional para mascotas')
BUSINESS_HERO_BADGE = os.getenv('BUSINESS_HERO_BADGE', f'{BUSINESS_CATEGORY.title()} en {BUSINESS_CITY}, {BUSINESS_COUNTRY}')
BUSINESS_HERO_TITLE = os.getenv('BUSINESS_HERO_TITLE', 'Baño, corte y cariño para tu mascota.')
BUSINESS_HERO_DESCRIPTION = os.getenv(
    'BUSINESS_HERO_DESCRIPTION',
    f'Ofrecemos baños, cortes, tratamientos de higiene y cuidado estético con atenci\u00f3n personalizada en {BUSINESS_CITY}.'
)
BUSINESS_CONTACT_TITLE = os.getenv('BUSINESS_CONTACT_TITLE', 'Estamos listos para atender a tu mascota')
BUSINESS_CONTACT_DESCRIPTION = os.getenv(
    'BUSINESS_CONTACT_DESCRIPTION',
    'Escribenos para consultar disponibilidad, servicios especiales o cuidados antes de una cita.'
)
BUSINESS_FOOTER_DESCRIPTION = os.getenv(
    'BUSINESS_FOOTER_DESCRIPTION',
    f'Centro especializado en estética, peluquería y spa para mascotas. Cuidamos a tu compañero con amor, higiene y atenci\u00f3n profesional en {BUSINESS_CITY}.'
)
BUSINESS_CONTACT_EMAIL = os.getenv('BUSINESS_CONTACT_EMAIL', os.getenv('PETCARE_CONTACT_EMAIL', 'contacto@negocio.com'))
BUSINESS_CONTACT_PHONE = os.getenv('BUSINESS_CONTACT_PHONE', os.getenv('PETCARE_CONTACT_PHONE', '+593 99 999 9999'))
BUSINESS_ADDRESS = os.getenv('BUSINESS_ADDRESS', os.getenv('PETCARE_ADDRESS', f'Centro de {BUSINESS_CITY}, {BUSINESS_COUNTRY}'))
BUSINESS_OPENING_HOURS = os.getenv('BUSINESS_OPENING_HOURS', 'Lun - Sab: 08:30 - 18:30')
BUSINESS_CURRENCY = os.getenv('BUSINESS_CURRENCY', 'USD')
BUSINESS_CURRENCY_SYMBOL = os.getenv('BUSINESS_CURRENCY_SYMBOL', '$')
BUSINESS_REVIEW_LABEL = os.getenv('BUSINESS_REVIEW_LABEL', f'Rese\u00f1as en {BUSINESS_CITY}')
BUSINESS_LOCATION_LABEL = os.getenv('BUSINESS_LOCATION_LABEL', f'{BUSINESS_CITY} Centro')
BUSINESS_PRIMARY_CTA = os.getenv('BUSINESS_PRIMARY_CTA', 'Agendar cita')
BUSINESS_SHOW_DEMO_ACCOUNTS = env_bool('BUSINESS_SHOW_DEMO_ACCOUNTS', DEBUG)
BUSINESS_TRANSACTION_PREFIX = os.getenv('BUSINESS_TRANSACTION_PREFIX', BUSINESS_SHORT_NAME.upper().replace(' ', '-'))
HOME_HERO_SLIDES = env_json('HOME_HERO_SLIDES', [
    {
        'image': 'https://images.unsplash.com/photo-1516734212186-a967f81ad0d7?w=900&q=85',
        'title': 'Groomers certificados',
        'text': 'Técnicas sin estr\u00e9s ni anestésicos',
        'alt': 'Ba\u00f1o profesional para mascotas',
    },
    {
        'image': 'https://images.unsplash.com/photo-1601758124510-52d02ddb7cbd?w=900&q=85',
        'title': 'Cortes con estilo',
        'text': 'Acabados limpios seg\u00fan raza y pelaje',
        'alt': 'Corte y estilo para mascotas',
    },
    {
        'image': 'https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=900&q=85',
        'title': 'Seguimiento visible',
        'text': 'Tu mascota avanza etapa por etapa',
        'alt': 'Cuidado y seguimiento de mascotas',
    },
])
HOME_TRUST_FEATURES = env_json('HOME_TRUST_FEATURES', [
    {
        'icon': 'sanitizer',
        'title': 'Productos hipoalerg\u00e9nicos',
        'text': 'Cosm\u00e9tica canina de primera l\u00ednea, formulada para cuidar el pH de la piel sensible.',
    },
    {
        'icon': 'spa',
        'title': 'Ambiente calmado',
        'text': 'Instalaciones pensadas para reducir ruido, estr\u00e9s y tiempos de espera innecesarios.',
    },
    {
        'icon': 'event_available',
        'title': 'Reserva f\u00e1cil online',
        'text': 'Agenda desde el celular, revisa historial y consulta el avance de cada atenci\u00f3n.',
    },
])
BUSINESS_CONFIG = {
    'app_name': APP_NAME,
    'name': BUSINESS_NAME,
    'short_name': BUSINESS_SHORT_NAME,
    'city': BUSINESS_CITY,
    'country': BUSINESS_COUNTRY,
    'country_code': BUSINESS_COUNTRY_CODE,
    'category': BUSINESS_CATEGORY,
    'tagline': BUSINESS_TAGLINE,
    'hero_badge': BUSINESS_HERO_BADGE,
    'hero_title': BUSINESS_HERO_TITLE,
    'hero_description': BUSINESS_HERO_DESCRIPTION,
    'contact_title': BUSINESS_CONTACT_TITLE,
    'contact_description': BUSINESS_CONTACT_DESCRIPTION,
    'footer_description': BUSINESS_FOOTER_DESCRIPTION,
    'email': BUSINESS_CONTACT_EMAIL,
    'phone': BUSINESS_CONTACT_PHONE,
    'address': BUSINESS_ADDRESS,
    'opening_hours': BUSINESS_OPENING_HOURS,
    'currency': BUSINESS_CURRENCY,
    'currency_symbol': BUSINESS_CURRENCY_SYMBOL,
    'review_label': BUSINESS_REVIEW_LABEL,
    'location_label': BUSINESS_LOCATION_LABEL,
    'primary_cta': BUSINESS_PRIMARY_CTA,
    'show_demo_accounts': BUSINESS_SHOW_DEMO_ACCOUNTS,
    'transaction_prefix': BUSINESS_TRANSACTION_PREFIX,
    'google_login_enabled': GOOGLE_LOGIN_CONFIGURED,
    'hero_slides': HOME_HERO_SLIDES,
    'trust_features': HOME_TRUST_FEATURES,
}

PETCARE_CONTACT_EMAIL = BUSINESS_CONTACT_EMAIL
PETCARE_CONTACT_PHONE = BUSINESS_CONTACT_PHONE
PETCARE_ADDRESS = BUSINESS_ADDRESS

EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
BREVO_API_KEY = os.getenv('BREVO_API_KEY', '').strip()
BREVO_SENDER_EMAIL = os.getenv('BREVO_SENDER_EMAIL', '').strip()
BREVO_SENDER_NAME = os.getenv('BREVO_SENDER_NAME', APP_NAME).strip()
BREVO_TIMEOUT_SECONDS = env_int('BREVO_TIMEOUT_SECONDS', 10)
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = env_int('EMAIL_PORT', 587)
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', BUSINESS_CONTACT_EMAIL)
ADMIN_NOTIFICATION_EMAIL = os.getenv('ADMIN_NOTIFICATION_EMAIL', BUSINESS_CONTACT_EMAIL)

if IS_RENDER and EMAIL_BACKEND.endswith('console.EmailBackend'):
    raise ImproperlyConfigured('Configura un proveedor SMTP o transaccional para enviar correos en produccion.')
if EMAIL_BACKEND == 'citas.email_backend.BrevoEmailBackend' and (not BREVO_API_KEY or not BREVO_SENDER_EMAIL):
    raise ImproperlyConfigured('Configura BREVO_API_KEY y BREVO_SENDER_EMAIL para usar Brevo.')

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'
TRUST_X_FORWARDED_FOR = env_bool('TRUST_X_FORWARDED_FOR', False)
DATA_UPLOAD_MAX_MEMORY_SIZE = env_int('DATA_UPLOAD_MAX_MEMORY_SIZE', 5 * 1024 * 1024)
FILE_UPLOAD_MAX_MEMORY_SIZE = env_int('FILE_UPLOAD_MAX_MEMORY_SIZE', 5 * 1024 * 1024)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': os.getenv('LOG_LEVEL', 'INFO')},
    'loggers': {
        'django.request': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'citas': {'handlers': ['console'], 'level': os.getenv('LOG_LEVEL', 'INFO'), 'propagate': False},
    },
}

if not DEBUG:
    SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', IS_RENDER)
    CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', IS_RENDER)
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', IS_RENDER)
    SECURE_HSTS_SECONDS = env_int('SECURE_HSTS_SECONDS', 31536000 if IS_RENDER else 0)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', IS_RENDER)
    SECURE_HSTS_PRELOAD = env_bool('SECURE_HSTS_PRELOAD', IS_RENDER)
