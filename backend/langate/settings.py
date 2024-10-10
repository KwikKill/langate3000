# flake8: noqa E501
"""
Django settings for langate project.

Generated by 'django-admin startproject' using Django 4.1.5.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

from os import getenv, path
from pathlib import Path
from sys import argv
import json
import logging

from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = getenv(
    "DJANGO_SECRET",
    "django-insecure-&s(%0f90_a(wa!hk5w9pzri%+6%46)pjn4tq5xycvk9t7dwe_d",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = int(getenv("DEV", "0")) == 1

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
PROTOCOL = getenv("HTTP_PROTOCOL", "http")

OUTSIDE_PORT = getenv("NGINX_PORT", "80")
if (OUTSIDE_PORT == "80" and PROTOCOL == "http") or (OUTSIDE_PORT == "443" and PROTOCOL == "https"):
    OUTSIDE_PORT = "" # Don't specify it
else:
    OUTSIDE_PORT = f":{OUTSIDE_PORT}"

# LOGGING Setup
LOGGING = {
    "version":1,
    "disable_existing_loggers":False,
    "handlers":{
        "console":{
                "class":"logging.StreamHandler",
            },
        },
    "root": {
        "handlers": ["console"],
        "level": ["INFO", "DEBUG"][DEBUG]
        },
}

# Allow itself and the frontend
WEBSITE_HOST = getenv("WEBSITE_HOST", "localhost")
ALLOWED_HOSTS = [
    "api." + WEBSITE_HOST,
    WEBSITE_HOST,
    "dev." + WEBSITE_HOST,
]

CSRF_TRUSTED_ORIGINS = [
     PROTOCOL + "://api." + getenv("WEBSITE_HOST", "localhost") + OUTSIDE_PORT,
     PROTOCOL + "://" + getenv("WEBSITE_HOST", "localhost") + OUTSIDE_PORT,
]

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "langate.user",
    "langate.network",
    "drf_yasg",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

SWAGGER_SETTINGS = {
    "USE_SESSION_AUTH": True,
    "LOGIN_URL": "/user/login/",
    "LOGOUT_URL": "/user/logout/",
}

ROOT_URLCONF = "langate.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "langate.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "USER": getenv("DB_USER", "user") + ("_test" if "test" in argv else ""),
        "NAME": getenv("DB_NAME", "mydb"),
        "PASSWORD": getenv("DB_PASS", "password"),
        "HOST": getenv("DB_HOST", "localhost"),
        "PORT": getenv("DB_PORT", "5432"),
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

AUTH_USER_MODEL = "user.User"

# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

TIME_ZONE = "Europe/Paris"

LANGUAGE_CODE = 'en'
LOCALE_PATH='locale'
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("en", _("English")),
    ("fr", _("French")),
]

LOCALE_PATHS = [path.join(BASE_DIR, 'locale')]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = "v1/" + getenv("STATIC_ROOT", "static/")
STATICFILES_DIRS = [path.join(BASE_DIR, "assets")]

MEDIA_URL = 'media/'
MEDIA_ROOT = "v1/" + getenv("MEDIA_ROOT", "media/")

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

# Login and logout
LOGIN_URL = ("rest_framework:login",)
#LOGIN_REDIRECT_URL = ""
LOGOUT_URL = "rest_framework:logout"

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "https://" + getenv("WEBSITE_HOST", "localhost"),
    "https://api." + getenv("WEBSITE_HOST", "localhost"),
    "http://" + getenv("WEBSITE_HOST", "localhost"),
    "http://api." + getenv("WEBSITE_HOST", "localhost"),
    "https://" + getenv("HELLOASSO_HOSTNAME", "localhost"), # helloasso has be to trusted
    "https://gate." + getenv("WEBSITE_HOST", "localhost"),

]
CSRF_COOKIE_DOMAIN = '.' + getenv("WEBSITE_HOST", "localhost")

# Session cookie settings
SESSION_COOKIE_AGE = int(getenv("SESSION_COOKIE_AGE", "1209600"))
SETTINGS = {}

# Network settings
if not path.exists("assets/misc/settings.json"):
    logger.error("No settings.json found, defaulting to [100]")
    SETTINGS = {
      "marks": [{"name": "default", "value": 100, "priority":1}]
    }
else:
    file = open("assets/misc/settings.json", "r")
    with file as f:
        data = json.load(f)
        SETTINGS = data

    if "marks" not in SETTINGS:
        logger.error("No marks found in settings.json, defaulting to [100]")
        SETTINGS["marks"] = [{"name": "default", "value": 100, "priority":1}]

    sum = 0
    for mark in range(len(SETTINGS["marks"])):
        sum += SETTINGS["marks"][mark]["priority"]
    if sum != 1:
        logger.error("Sum of priorities is not 1, defaulting to [100]")
        SETTINGS["marks"] = [{"name": "default", "value": 100, "priority":1}]

NETCONTROL_SOCKET_FILE = getenv("NETCONTROL_SOCKET_FILE", "/var/run/langate3000-netcontrol.sock")
