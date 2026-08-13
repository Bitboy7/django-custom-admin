#!/bin/bash

# Entrypoint específico para Railway.app
set -e

echo "Iniciando configuración..."

# Instalar dependencias si no están instaladas
echo "Verificando e instalando dependencias... 📦 "
pip install -r requirements.txt

# Esperar un poco para asegurar que todo esté listo
echo "Esperando inicialización..."
sleep 5

# Verificar la configuración de Django
echo "Verificando configuración de Django..."
python manage.py check --deploy --settings=app.settings || echo "⚠️ Advertencias de configuración detectadas, continuando..."

# Ejecutar migraciones de forma más robusta
echo "Ejecutando migraciones..."
python manage.py migrate --fake-initial || python manage.py migrate --run-syncdb || echo "⚠️ Error en migraciones, continuando..."
python manage.py makemigrations || echo "⚠️ Error al crear migraciones, continuando..."
python manage.py migrate ventas  
# Crear superusuario si no existe (de forma más segura)
echo "Verificando superusuario..."
python manage.py shell -c "
import os
from django.contrib.auth import get_user_model
try:
    User = get_user_model()
    if not User.objects.filter(is_superuser=True).exists():
        print('Creando superusuario por defecto...')
        User.objects.create_superuser(
            os.environ.get('DJANGO_SUPERUSER_NAME'),
            os.environ.get('DJANGO_SUPERUSER_EMAIL'),
            os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        )
        print(f'Superusuario creado: {os.environ.get(\"DJANGO_SUPERUSER_NAME\")}')
    else:
        print('Superusuario ya existe')
except Exception as e:
    print(f'Error al verificar/crear superusuario: {e}')
" || echo "⚠️ Error al configurar superusuario, continuando..."

# Configurar roles si no existen
echo "Configurando roles del sistema..."
python manage.py setup_roles --create-roles || echo "Los roles ya están configurados o hubo un error"

# Recopilar archivos estáticos
echo "Recopilando archivos estáticos... 📦 "
python manage.py collectstatic --noinput --clear || echo "⚠️ Error al recopilar estáticos, continuando..."

# Compilar mensajes de traducción
echo "Compilando mensajes de traducción..."
python manage.py compilemessages || echo "⚠️ Error al compilar traducciones, continuando..."

# Crear directorios de media necesarios
echo "Creando directorios de media... 📁 "
python manage.py shell -c "
import os
from django.conf import settings
try:
    media_dirs = [
        'avatars', 'site',
        'bancos', 'bancos/logos',
        'catalogo', 'catalogo/productos',
        'clientes',
        'paises', 'paises/banderas',
        'productores', 'productores/imagenes',
        'capital_inversiones', 'capital_inversiones/documentos',
        'comprobantes_pagos', 'estados_cuenta',
        'temp_documents', 'temp_invoices'
    ]
    for dir_name in media_dirs:
        dir_path = os.path.join(settings.MEDIA_ROOT, dir_name)
        os.makedirs(dir_path, exist_ok=True)
        print(f'Directorio creado: {dir_path}')
except Exception as e:
    print(f'Error al crear directorios: {e}')
" || echo "Error al crear directorios de media"

echo "Configuración completada"

# El OCR se ejecuta en el mismo contenedor por defecto, por lo que la imagen se
# puede desplegar sin Docker Compose. En Compose se puede desactivar en `web`
# cuando se use un contenedor OCR dedicado.
OCR_WORKER_ENABLED=${OCR_WORKER:-true}
OCR_WORKER_SLEEP=${OCR_WORKER_SLEEP:-2}
OCR_WORKER_PID=""

case "${OCR_WORKER_ENABLED,,}" in
    1|true|yes|on)
        echo "Iniciando worker OCR (intervalo: ${OCR_WORKER_SLEEP}s)..."
        python manage.py process_receipt_ocr --loop --sleep "$OCR_WORKER_SLEEP" &
        OCR_WORKER_PID=$!
        ;;
    *)
        echo "Worker OCR desactivado (OCR_WORKER=${OCR_WORKER_ENABLED})."
        ;;
esac

stop_children() {
    trap - TERM INT
    echo "Deteniendo procesos hijos..."
    if [ -n "$OCR_WORKER_PID" ]; then
        kill -TERM "$OCR_WORKER_PID" 2>/dev/null || true
    fi
    if [ -n "${GUNICORN_PID:-}" ]; then
        kill -TERM "$GUNICORN_PID" 2>/dev/null || true
    fi
    wait 2>/dev/null || true
    exit 0
}

trap stop_children TERM INT

echo "Iniciando servidor..."

# Obtener el puerto de Railway o usar 8000 por defecto
PORT=${PORT:-8000}

# Ejecutar Gunicorn y mantener el entrypoint como PID 1 para reenviar señales
# tanto al servidor como al worker OCR.
gunicorn app.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --keep-alive 2 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile - \
    --error-logfile - \
    --log-level info &
GUNICORN_PID=$!

if wait "$GUNICORN_PID"; then
    GUNICORN_STATUS=0
else
    GUNICORN_STATUS=$?
fi

if [ -n "$OCR_WORKER_PID" ]; then
    kill -TERM "$OCR_WORKER_PID" 2>/dev/null || true
    wait "$OCR_WORKER_PID" 2>/dev/null || true
fi

exit "$GUNICORN_STATUS"
