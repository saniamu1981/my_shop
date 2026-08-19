# my_shop/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Загружаем переменные из .env только если файл существует
env_path = BASE_DIR / '.env'
if env_path.exists():
    load_dotenv(env_path)

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-default-key-for-dev')
DEBUG = True  # Временно для отладки

# ============ ХОСТЫ И БЕЗОПАСНОСТЬ ============
ALLOWED_HOSTS = [
    'maidlingerie.ru',
    'www.maidlingerie.ru',
    'saniamu1981-my-shop-3994.twc1.net',
    'localhost',
    '127.0.0.1',
    '*',  # Временно для теста
]

# ============ CSRF НАСТРОЙКИ ============
CSRF_TRUSTED_ORIGINS = [
    'https://maidlingerie.ru',
    'http://maidlingerie.ru',
    'https://saniamu1981-my-shop-3994.twc1.net',
    'http://saniamu1981-my-shop-3994.twc1.net',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

SECURE_SSL_REDIRECT = False

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # Сторонние приложения
    'allauth',
    'allauth.account',
    'allauth.socialaccount',

    # Наши приложения
    'apps.accounts',
    'apps.products',
    'apps.cart',
    'apps.orders',
    'admin_panel',
    'delivery',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

ROOT_URLCONF = 'my_shop.urls'

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
                'apps.cart.context_processors.cart_total',
                'apps.orders.context_processors.orders_count',
                'apps.products.context_processors.favorites_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'my_shop.wsgi.application'

# ============ БАЗА ДАННЫХ ============
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'default_db',
        'USER': 'gen_user',
        'PASSWORD': '13Sent2005',
        'HOST': 'f58bcedf1f7b47e6242ee947.twc1.net',
        'PORT': '5432',
        'OPTIONS': {
            'sslmode': 'require',
        },
        'CONN_MAX_AGE': 600,
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'accounts.CustomUser'

# Authentication
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL = '/accounts/login/'

# Django-Allauth settings
SITE_ID = 1
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = True

# Email settings
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.yandex.ru')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

# Stripe settings
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', 'pk_test_...')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', 'sk_test_...')

# CSRF и сессии
CSRF_COOKIE_HTTPONLY = False
CSRF_USE_SESSIONS = False
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG

# Security headers
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

CART_SESSION_ID = 'cart'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.getenv('LOG_LEVEL', 'WARNING'),
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}

if os.getenv('RUN_MIGRATIONS', 'False') == 'True':
    os.system('python manage.py migrate --noinput')
    os.system('python manage.py collectstatic --noinput')


# ============ НАСТРОЙКИ ДОСТАВКИ ============

# ============ НАСТРОЙКИ ЯНДЕКС МАРКЕТ ============
YANDEX_MARKET_CLIENT_ID = 'f09d1d32d25e45a0b9dccf8ec851ecfa'
YANDEX_MARKET_CLIENT_SECRET = '5ee190b18e3e416e97abffbb9a2f7a42'
YANDEX_MARKET_OAUTH_TOKEN = 'y0__wgBEMvnoRcYldRHIJyk0NoYYZJVWS3hFcrEKypR4DXkceQTsi4'

# ============ НАСТРОЙКИ DADATA ============
DADATA_API_KEY = '45560e5654f1e3c242c97edb48996367ff1a9c40'  # Получить на dadata.ru
DADATA_SECRET_KEY = '6d99388bb9c34e17b147ba998b3008dd6c5ee9aa'  # Тоже из кабинета

# ВАШИ РЕАЛЬНЫЕ КЛЮЧИ СДЭК
CDEK_CLIENT_ID = 'GYbe8QlTfyulXTyaTyNVFKcDgWI5VK5T'
CDEK_CLIENT_SECRET = 'dC6wVstTd2YWkyXPOTaZRpRAXgkyV4eH'

# ВАЖНО: Используем боевой режим (False), так как ключи работают только в боевом API
CDEK_TEST_MODE = False

# Яндекс Карты
YANDEX_MAPS_API_KEY = '945266d5-9e2f-4e11-b600-99e446df15e6'

# Город отправителя
SHOP_CITY = 'Москва'
SHOP_CITY_CODE = 44

# Логирование для отладки API СДЭК
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'delivery.views': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}