"""
Django settings for Appligne project.

Generated by 'django-admin startproject' using Django 5.0.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

from pathlib import Path
from decouple import config
import os
from datetime import datetime



# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-yjb=-9#-u7!9%++z)*)au0z*j_nsognm2mt#=jem%y=5cfx0%l'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [config('ALLOWED_HOST1', "localhost")]


# Application definition

INSTALLED_APPS = [
    'pages.apps.PagesConfig',
    'accounts',
    'eleves',
    'backups',  # <--- AJOUTE CETTE LIGNE
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'mathfilters',
    'cart',
    'payment',
    
]

# Configurer Stripe dans settings.py
STRIPE_PUBLIC_KEY = config('STRIPE_PUBLIC_KEY')
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

X_FRAME_OPTIONS = 'SAMEORIGIN' # Permet l’affichage de tes propres pages dans une iframe

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
            ],
        },
    },
]

WSGI_APPLICATION = 'Appligne.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME':  config('NAME_DATABASE', default=False),
        'USER': config('USER_DATABASE', default=False),
        'PASSWORD': config('PASSWORD_DATABASE', default=False),
        'HOST': config('HOST_DATABASE', default=False),   # ou l'adresse de votre serveur MySQL
        'PORT': config('PORT_DATABASE', default=False),        # ou le port que vous utilisez pour MySQL
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",  # pour corriger l'erreur que vous pouvez rencontrer (mysql.W002) concernant le mode strict de MariaDB qui n'est pas activé pour la connexion à la base de données par défaut de Django (ChatGPT)
        },
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'fr'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_ROOT =  BASE_DIR /  'static'

STATIC_URL = 'static/'

# Media folder
# pour que les photos dela base des données seront stoquées dans le répertoire media et non static du frontEnd
MEDIA_ROOT = BASE_DIR /  'media'

MEDIA_URL = 'media/'


# adapter la config MYSQL_PATHS selon l’OS (Windows, PythonAnywhere (Linux))
import platform
import shutil

if platform.system() == "Windows":
    MYSQL_PATHS = {
        'mysqldump': r'C:\xampp\mysql\bin\mysqldump.exe',
        'mysql': r'C:\xampp\mysql\bin\mysql.exe',
    }
else:
    # Sur Linux (PythonAnywhere), on utilise le chemin trouvé dans le PATH ou un chemin classique
    MYSQL_PATHS = {
        'mysqldump': shutil.which('mysqldump') or '/usr/bin/mysqldump',
        'mysql': shutil.which('mysql') or '/usr/bin/mysql',
    }


# localise l'emplacement des fichiers static du front_end qui vont etre 
# utiliser par django pour fabriquer le dossier static fonctionnel 
# dans django et qui contient le repertoire admin
STATICFILES_DIRS = [
    BASE_DIR /  'Appligne/static'
]


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom Messages
# https://docs.djangoproject.com/fr/5.0/ref/contrib/messages/
from django.contrib.messages import constants as messages

MESSAGE_TAGS = {
    # changer le tag du message de error à danger car Bootstdap ignore le tag error
    messages.ERROR: "danger",
    #50: "critical",
}



# Récupération du mot de passe email depuis le fichier .env
PASSWORD_EMAIL = config('PASSWORD_EMAIL')

# # Paramètres SMTP pour l'envoi d'emails
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp-mail.outlook.com'
# EMAIL_PORT = 587  # Port SMTP pour TLS
# EMAIL_HOST_USER = 'appligne@outlook.com'  # Votre adresse Gmail
# EMAIL_HOST_PASSWORD = PASSWORD_EMAIL  # Mot de passe de votre compte Gmail
# EMAIL_USE_TLS = True  # Utiliser TLS (Transport Layer Security)

# EMAIL_HOST_USER = 'prosib25@gmail.com'  # Votre adresse Gmail
# EMAIL_HOST_USER = 'appligne@outlook.com'  # Votre adresse Gmail

# Paramètres SMTP pour l'envoi d'emails
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587  # Port SMTP pour TLS
EMAIL_HOST_USER = 'prosib25@gmail.com'  # Votre adresse Gmail
EMAIL_HOST_PASSWORD = PASSWORD_EMAIL  # Mot de passe de votre compte Gmail
EMAIL_USE_TLS = True  # Utiliser TLS (Transport Layer Security)

DEFAULT_FROM_EMAIL = 'no-reply@monsite.com' # email par défaut si l'email de l'expéditeur manque, comme adresse de secours
ADMIN_EMAIL = 'prosib25@gmail.com' # email de l'administrateur

# Configurer les paramètres JWT
"""
Un JWT est un jeton d’authentification compact et encodé en base64, généralement utilisé pour prouver l’identité d’un utilisateur après qu’il se soit connecté.
risque: Le contenu est lisible (base64 ≠ chiffrement), donc ne jamais y stocker de données sensibles.
"""
PASSWORD_JWT = config('PASSWORD_JWT') # Récupération du mot de passe PASSWORD_JWT depuis le fichier .env
JWT_SECRET = PASSWORD_JWT # your_secret_key
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_SECONDS = 3600  # Token expiration time (e.g., 1 hour)

# Configurer les paramètres reCAPTCHA (Vérifier qu’un utilisateur est humain et non un robot automatisé.)
"""
Protéger les formulaires de contact, commentaires, inscriptions ou connexions.
Éviter les créations de comptes frauduleux.
Empêcher les attaques par force brute (essais multiples de mots de passe).
Réduire les spams automatiques.
"""
RECAPTCHA_PUBLIC_KEY = config('RECAPTCHA_PUBLIC_KEY')
RECAPTCHA_PRIVATE_KEY = config('RECAPTCHA_PRIVATE_KEY')
RECAPTCHA_MIN_SCORE = 0.5  # Seuil de sécurité (0.5-0.9 selon votre tolérance)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} [{levelname}] {name}:{lineno} - {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
            'formatter': 'verbose',
            'encoding': 'utf-8',  # ✅ Ici c'est valide
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'eleves': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}




# entregistrement de message logs
today = datetime.now()
log_dir = os.path.join(BASE_DIR, 'logs', today.strftime("%Y"), today.strftime("%m"))
os.makedirs(log_dir, exist_ok=True)
log_filename = os.path.join(log_dir, today.strftime("%Y-%m-%d") + '.log')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s',
        },
    },

    'handlers': {
        'myapp_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': log_filename,
            'formatter': 'standard',
        },
    },

    'loggers': {
        # Logger racine qui capte tout par défaut
        '': {
            'handlers': ['myapp_file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'myapp': {
            'handlers': ['myapp_file'],
            'level': 'DEBUG',
            'propagate': False,
        },

        'django': {
            'handlers': ['myapp_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['myapp_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['myapp_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.template': {
            'handlers': ['myapp_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['myapp_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.utils.autoreload': {
            'handlers': ['myapp_file'],
            'level': 'ERROR',
            'propagate': False,
        },
    }
}

# Générer une clé de chiffrement
SECRET_ENCRYPTION_KEY = config('PASSWORD_CRYPTO')

