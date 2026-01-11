# ✅ 1. Base des chemins (ne change pas)
from pathlib import Path
import os
from datetime import datetime
import platform
import shutil
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# ✅ 2. Variables d’environnement (toujours en haut)
SECRET_KEY = config('SECRET_KEY', default='django-insecure-...')  # ne jamais hardcoder !
DEBUG = config('DEBUG', cast=bool, default=True)

ALLOWED_HOSTS = [config('ALLOWED_HOST1', default="localhost")]
DOMAIN = config('DOMAIN_KEY', default="http://localhost:8000")

# ✅ 3. Applications Django
INSTALLED_APPS = [
    # Apps internes
    'pages.apps.PagesConfig',
    'accounts',
    'eleves',
    'backups',
    'cart',
    'payment',

    # Librairies tierces
    'mathfilters',

    # Apps Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

# ✅ 4. Middlewares & Templates (inchangés mais propres)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

X_FRAME_OPTIONS = 'SAMEORIGIN'

ROOT_URLCONF = 'Appligne.urls'

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
                'accounts.context_processors.debug_variable',
            ],
        },
    },
]

WSGI_APPLICATION = 'Appligne.wsgi.application'

# ✅ 5. Base de données
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('NAME_DATABASE'),
        'USER': config('USER_DATABASE'),
        'PASSWORD': config('PASSWORD_DATABASE'),
        'HOST': config('HOST_DATABASE'),
        'PORT': config('PORT_DATABASE'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET NAMES 'utf8mb4' COLLATE 'utf8mb4_unicode_ci';", # le 12/11/2025
        },
    }
}

# ✅ 6. Internationalisation
LANGUAGE_CODE = 'fr'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ✅ 7. Fichiers statiques et médias
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'static'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

STATICFILES_DIRS = [
    BASE_DIR / 'Appligne/static'
]

# ✅ 8. MySQL outils externes (backup)
if platform.system() == "Windows":
    MYSQL_PATHS = {
        'mysqldump': r'C:\xampp\mysql\bin\mysqldump.exe',
        'mysql': r'C:\xampp\mysql\bin\mysql.exe',
    }
else:
    MYSQL_PATHS = {
        'mysqldump': shutil.which('mysqldump') or '/usr/bin/mysqldump',
        'mysql': shutil.which('mysql') or '/usr/bin/mysql',
    }

# ✅ 9. Emails
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'prosib25@gmail.com'
EMAIL_HOST_PASSWORD = config('PASSWORD_EMAIL')
EMAIL_USE_TLS = True

DEFAULT_FROM_EMAIL = 'no-reply@monsite.com'
ADMIN_EMAIL = 'prosib25@gmail.com'

# ✅ 10. Stripe
STRIPE_PUBLIC_KEY = config('STRIPE_PUBLIC_KEY')
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET')
STRIPE_WEBHOOK_SECRET_TRANSFERT = config('STRIPE_WEBHOOK_SECRET_TRANSFERT')

# ✅ 11. JWT & reCAPTCHA & cryptography
JWT_SECRET = config('PASSWORD_JWT')
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_SECONDS = 3600

RECAPTCHA_PUBLIC_KEY = config('RECAPTCHA_PUBLIC_KEY')
RECAPTCHA_PRIVATE_KEY = config('RECAPTCHA_PRIVATE_KEY')
RECAPTCHA_MIN_SCORE = 0.5

# 🔒 Clé de chiffrement (cryptography)
SECRET_ENCRYPTION_KEY = config('PASSWORD_CRYPTO')

# ✅ 12. Logging
today = datetime.now()

stripe_log_dir = BASE_DIR / 'logs' / 'stripe' / today.strftime("%Y") / today.strftime("%m")
app_log_dir = BASE_DIR / 'logs' / 'app' / today.strftime("%Y") / today.strftime("%m")

os.makedirs(stripe_log_dir, exist_ok=True)
os.makedirs(app_log_dir, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s',
        },
    },
    'handlers': {
        'app_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': app_log_dir / f"{today.strftime('%Y-%m-%d')}.log",
            'formatter': 'standard',
            'encoding': 'utf-8',
        },
        'stripe_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': stripe_log_dir / f"{today.strftime('%Y-%m-%d')}.log",
            'formatter': 'standard',
            'encoding': 'utf-8',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
    },
    'loggers': {
        # Logger racine minimal
        '': {
            'handlers': ['console'],  # Seulement console pour debug
            'level': 'WARNING',
            'propagate': False
        },
        # Logger Stripe spécifique
        'payment.stripe': {
            'handlers': ['stripe_file', 'console'],
            'level': 'DEBUG',
            'propagate': False
        },
        # Logger pour payment.views - AJOUT IMPORTANT
        'payment.views': {
            'handlers': ['stripe_file', 'console'],
            'level': 'DEBUG',
            'propagate': False
        },
        # Vos autres loggers
        'myapp': {
            'handlers': ['app_file', 'console'],
            'level': 'DEBUG',
            'propagate': False
        },
        'django': {
            'handlers': ['app_file'],
            'level': 'WARNING',
            'propagate': False
        },
        'django.server': {
            'handlers': ['app_file'],
            'level': 'ERROR', 
            'propagate': False
        },
        'django.request': {
            'handlers': ['app_file'],
            'level': 'ERROR',
            'propagate': False
        },
        'django.db.backends': {
            'handlers': ['app_file'],
            'level': 'ERROR',
            'propagate': False
        },
    }
}
