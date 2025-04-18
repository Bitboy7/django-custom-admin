"""
Django settings for app project.

Generated by 'django-admin startproject' using Django 5.0.6.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

from import_export.formats.base_formats import *
from dotenv import load_dotenv
import os

load_dotenv()
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]

CRSF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "https://platypus-viable-doe.ngrok-free.app",]

# Application definition

INSTALLED_APPS = [
    'jazzmin',
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'django.contrib.humanize',
    'compressor',
    'catalogo.apps.CatalogoConfig',
    'gastos.apps.GastosConfig',
    'ventas.apps.VentasConfig',
    'import_export',
]

IMPORT_EXPORT_FORMATS = [XLSX, CSV, JSON, HTML]

JAZZMIN_SETTINGS = {
    # title of the window (Will default to current_admin_site.site_title if absent or None)
    "site_title": "Agricola de la Costa Admin",

    # Title on the login screen (19 chars max) (defaults to current_admin_site.site_header if absent or None)
    "site_header": "Agricola de la Costa Admin",

    # Title on the brand (19 chars max) (defaults to current_admin_site.site_header if absent or None)
       # Logo to use for your site, must be present in static files, used for brand on top left
    "site_logo": "/img/logo-sm.png",
    # Whether to display the side menu
    "show_sidebar": True,
    # Logo to use for your site, must be present in static files, used for login form logo (defaults to site_logo)
    "login_logo": "/img/logo-sm.png",
     # CSS classes that are applied to the logo above
    "site_logo_classes": "img-circle",

    # Relative path to a favicon for your site, will default to site_logo if absent (ideally 32x32 px)
    "site_icon": "/img/icon.png",

    # Whether to aut expand the menu
    "navigation_expanded": False,
     # Welcome text on the login screen
     # List of model admins to search from the search bar, search bar omitted if excluded
    # If you want to use a single search field you dont need to use a list, you can use a simple string 
    "search_model": ["catalogo.productor", "ventas.cliente"],
    # Field name on user model that contains avatar ImageField/URLField/Charfield or a callable that receives the user
    "user_avatar": "/img/icon.png",
    
      ############
    # Top Menu #
    ############

    # Links to put along the top menu
    "topmenu_links": [

        # external url that opens in a new window (Permissions can be added)
        {"name": "Acumulados", "url": "balances", "new_window": True, "permissions": ["auth.view_user"]},

    ],
    
    # Order the auth app before the books app, other apps will be alphabetically placed after these
    "order_with_respect_to": ["gastos", "ventas", "catalogo", "auth"],
    
    "related_modal_active": True,

       "icons": {
        "auth": "fa fa-database",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "catalogo.Pais": "fa fa-globe",
        "catalogo.Estado": "fas fa-map-marked-alt",
        "catalogo.Sucursal": "fas fa-store",
        "catalogo.Productor": "fa fa-id-badge",
        "catalogo.Producto": "fa fa-barcode",
        "gastos.Banco": "fas fa-university",
        "gastos.Cuenta": "fas fa-credit-card",
        "gastos.CatGastos": "fa fa-tag",
        "gastos.Gastos": "fas fa-money-check-alt",
        "gastos.Compra": "fa fa-shopping-basket",
        "gastos.SaldoMensual": "fa fa-chart-line",
        "ventas.Cliente": "fa fa-user-tie",
        "ventas.Ventas": "fa fa-shopping-cart",
        "ventas.Agente": "fa fa-user-secret",
        "ventas.Anticipo": "fa fa-money-bill-wave",
    },
        # Icons that are used when one is not manually specified
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "related_modal_active": True,
    #############
    # UI Tweaks #
    #############
    # Relative paths to custom CSS/JS scripts (must be present in static files)
    "custom_css": "/css/styles.css",
    "custom_js": "/js/scripts.js",
    # Whether to link font from fonts.googleapis.com (use custom_css to supply font otherwise)
    "use_google_fonts_cdn": True,
    # Whether to show the UI customizer on the sidebar
    "show_ui_builder": False,
        ###############
    # Change view #
    ###############
    # Render out the change view as a single form, or in tabs, current options are
    # - single
    # - horizontal_tabs (default)
    # - vertical_tabs
    # - collapsible
    # - carousel
    "changeform_format": "collapsible",
    # override change forms on a per modeladmin basis
    "changeform_format_overrides": {"auth.user": "collapsible", "auth.group": "vertical_tabs", "catalogo.Productor": "vertical_tabs", "catalogo.Pais": "vertical_tabs", "catalogo.Estado": "vertical_tabs", "catalogo.Sucursal": "vertical_tabs", "gastos.Banco": "vertical_tabs", "gastos.Cuenta": "vertical_tabs", "gastos.CatGastos": "vertical_tabs", "gastos.Gastos": "vertical_tabs", "gastos.Compra": "vertical_tabs" ,"gastos.SaldoMensual": "vertical_tabs",  "ventas.Cliente": "vertical_tabs", "ventas.Ventas": "vertical_tabs", "ventas.Agente": "vertical_tabs", "catalogo.Producto": "vertical_tabs"},
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": True,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-white",
    "accent": "accent-navy",
    "navbar": "navbar-gray navbar-dark",
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-light-olive",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": True,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": True,
    "theme": "litera",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-outline-primary",
        "secondary": "btn-outline-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    },
    "actions_sticky_top": True
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = "app.wsgi.application"

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
          'ENGINE': 'django.db.backends.mysql',
          'NAME': os.getenv("DB_NAME"),
          'USER': os.getenv("DB_USER"),
          'PASSWORD': os.getenv("DB_PASSWORD"),
          'HOST': os.getenv("DB_HOST"),
          'PORT': os.getenv("DB_PORT"),
     }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "es-ES"

TIME_ZONE = "America/Mexico_City"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "/static/"
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
STATIC_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'static-only')

STATICFILES_DIRS = (
    os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'),
)

TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'templates'),
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Compressor settings
COMPRESS_ROOT = BASE_DIR / 'static'

COMPRESS_ENABLED = True

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
]

