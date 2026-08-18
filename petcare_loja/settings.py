import os
from importlib.util import find_spec
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
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


SECRET_KEY = os.getenv(
    'SECRET_KEY',
    os.getenv('DJANGO_SECRET_KEY', 'django-insecure-petcare-loja-secret-key-key-loja-2026')
)

DEBUG = env_bool('DEBUG', True)
APP_NAME = os.getenv('APP_NAME', 'PetNexo')

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', '127.0.0.1,localhost')
CSRF_TRUSTED_ORIGINS = env_list(
    'CSRF_TRUSTED_ORIGINS',
    'http://127.0.0.1:8081,http://localhost:8081,http://127.0.0.1:8080,http://localhost:8080',
)

if os.getenv('VERCEL'):
    vercel_url = os.getenv('VERCEL_URL', '').strip()
    ALLOWED_HOSTS.extend(['.vercel.app'])
    CSRF_TRUSTED_ORIGINS.extend(['https://*.vercel.app'])
    if vercel_url:
        ALLOWED_HOSTS.append(vercel_url)
        CSRF_TRUSTED_ORIGINS.append(f'https://{vercel_url}')

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
    'citas',
]

WHITENOISE_AVAILABLE = find_spec('whitenoise') is not None

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
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

DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 4},
    },
]

LANGUAGE_CODE = 'es-ec'

TIME_ZONE = 'America/Guayaquil'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage' if WHITENOISE_AVAILABLE else 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

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

SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_ADAPTER = 'citas.adapters.PetNexoSocialAccountAdapter'

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

DATAFAST_BASE_URL = os.getenv('DATAFAST_BASE_URL', 'https://test.oppwa.com').rstrip('/')
DATAFAST_ENTITY_ID = os.getenv('DATAFAST_ENTITY_ID', '')
DATAFAST_AUTHORIZATION = os.getenv('DATAFAST_AUTHORIZATION', '')
DATAFAST_BRANDS = os.getenv('DATAFAST_BRANDS', 'VISA MASTER AMEX DINERS DISCOVER')
DATAFAST_TIMEOUT_SECONDS = env_int('DATAFAST_TIMEOUT_SECONDS', 20)
GOOGLE_LOGIN_ENABLED = env_bool('GOOGLE_LOGIN_ENABLED', False)

TRANSFER_BANK_NAME = os.getenv('TRANSFER_BANK_NAME', 'Banco Pichincha')
TRANSFER_ACCOUNT_NUMBER = os.getenv('TRANSFER_ACCOUNT_NUMBER', '0000000000')
TRANSFER_ACCOUNT_OWNER = os.getenv('TRANSFER_ACCOUNT_OWNER', 'PetCare Loja')
TRANSFER_ACCOUNT_ID = os.getenv('TRANSFER_ACCOUNT_ID', '0000000000000')

BUSINESS_NAME = os.getenv('BUSINESS_NAME', os.getenv('PETCARE_BUSINESS_NAME', 'PetCare Loja'))
BUSINESS_SHORT_NAME = os.getenv('BUSINESS_SHORT_NAME', BUSINESS_NAME.split()[0])
BUSINESS_CITY = os.getenv('BUSINESS_CITY', 'Loja')
BUSINESS_COUNTRY = os.getenv('BUSINESS_COUNTRY', 'Ecuador')
BUSINESS_COUNTRY_CODE = os.getenv('BUSINESS_COUNTRY_CODE', 'EC')
BUSINESS_CATEGORY = os.getenv('BUSINESS_CATEGORY', 'peluqueria y estetica para mascotas')
BUSINESS_TAGLINE = os.getenv('BUSINESS_TAGLINE', 'Cuidado profesional para mascotas')
BUSINESS_HERO_BADGE = os.getenv('BUSINESS_HERO_BADGE', f'{BUSINESS_CATEGORY.title()} en {BUSINESS_CITY}, {BUSINESS_COUNTRY}')
BUSINESS_HERO_TITLE = os.getenv('BUSINESS_HERO_TITLE', 'Bano, corte y carino para tu mascota.')
BUSINESS_HERO_DESCRIPTION = os.getenv(
    'BUSINESS_HERO_DESCRIPTION',
    f'Ofrecemos banos, cortes, tratamientos de higiene y cuidado estetico con atencion personalizada en {BUSINESS_CITY}.'
)
BUSINESS_CONTACT_TITLE = os.getenv('BUSINESS_CONTACT_TITLE', 'Estamos listos para atender a tu mascota')
BUSINESS_CONTACT_DESCRIPTION = os.getenv(
    'BUSINESS_CONTACT_DESCRIPTION',
    'Escribenos para consultar disponibilidad, servicios especiales o cuidados antes de una cita.'
)
BUSINESS_FOOTER_DESCRIPTION = os.getenv(
    'BUSINESS_FOOTER_DESCRIPTION',
    f'Centro especializado en estetica, peluqueria y spa para mascotas. Cuidamos a tu companero con amor, higiene y atencion profesional en {BUSINESS_CITY}.'
)
BUSINESS_CONTACT_EMAIL = os.getenv('BUSINESS_CONTACT_EMAIL', os.getenv('PETCARE_CONTACT_EMAIL', 'contacto@negocio.com'))
BUSINESS_CONTACT_PHONE = os.getenv('BUSINESS_CONTACT_PHONE', os.getenv('PETCARE_CONTACT_PHONE', '+593 99 999 9999'))
BUSINESS_ADDRESS = os.getenv('BUSINESS_ADDRESS', os.getenv('PETCARE_ADDRESS', f'Centro de {BUSINESS_CITY}, {BUSINESS_COUNTRY}'))
BUSINESS_OPENING_HOURS = os.getenv('BUSINESS_OPENING_HOURS', 'Lun - Sab: 08:30 - 18:30')
BUSINESS_CURRENCY = os.getenv('BUSINESS_CURRENCY', 'USD')
BUSINESS_CURRENCY_SYMBOL = os.getenv('BUSINESS_CURRENCY_SYMBOL', '$')
BUSINESS_REVIEW_LABEL = os.getenv('BUSINESS_REVIEW_LABEL', f'Resenas en {BUSINESS_CITY}')
BUSINESS_LOCATION_LABEL = os.getenv('BUSINESS_LOCATION_LABEL', f'{BUSINESS_CITY} Centro')
BUSINESS_PRIMARY_CTA = os.getenv('BUSINESS_PRIMARY_CTA', 'Agendar cita')
BUSINESS_SHOW_DEMO_ACCOUNTS = env_bool('BUSINESS_SHOW_DEMO_ACCOUNTS', DEBUG)
BUSINESS_TRANSACTION_PREFIX = os.getenv('BUSINESS_TRANSACTION_PREFIX', BUSINESS_SHORT_NAME.upper().replace(' ', '-'))
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
    'google_login_enabled': GOOGLE_LOGIN_ENABLED,
}

PETCARE_CONTACT_EMAIL = BUSINESS_CONTACT_EMAIL
PETCARE_CONTACT_PHONE = BUSINESS_CONTACT_PHONE
PETCARE_ADDRESS = BUSINESS_ADDRESS

EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = env_int('EMAIL_PORT', 587)
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', BUSINESS_CONTACT_EMAIL)
ADMIN_NOTIFICATION_EMAIL = os.getenv('ADMIN_NOTIFICATION_EMAIL', BUSINESS_CONTACT_EMAIL)

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', False)
    SECURE_HSTS_SECONDS = env_int('SECURE_HSTS_SECONDS', 31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
