from .base import *  # noqa: F401,F403

DEBUG = True
SECRET_KEY = 'django-insecure-dev-key-change-in-production'

ALLOWED_HOSTS = ['*']
CORS_ALLOW_ALL_ORIGINS = True

# Dev database defaults (override via env vars in production)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'seedteam'),  # noqa: F405
        'USER': os.environ.get('POSTGRES_USER', 'seedteam'),  # noqa: F405
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'seedteam'),  # noqa: F405
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),  # noqa: F405
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),  # noqa: F405
        'CONN_MAX_AGE': 600,  # noqa: F405
        'CONN_HEALTH_CHECKS': True,  # noqa: F405
        'OPTIONS': {
            'connect_timeout': 10,
        },
    }
}

# Use console email backend in dev
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Django Debug Toolbar
INSTALLED_APPS += ['debug_toolbar']  # noqa: F405
MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')  # noqa: F405
INTERNAL_IPS = ['127.0.0.1']

# Simpler password hashing for faster tests
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# Whitenoise off in dev
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}
