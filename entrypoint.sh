#!/bin/bash

# Entrypoint específico para Railway.app
set -e

echo "🚀 Iniciando configuración para Railway..."

# Instalar dependencias si no están instaladas
echo "📦 Verificando e instalando dependencias..."
pip install -r requirements.txt

# Esperar un poco para asegurar que todo esté listo
echo "⏳ Esperando inicialización..."
sleep 5

# Verificar la configuración de Django
echo "🔍 Verificando configuración de Django..."
python manage.py check --deploy --settings=app.settings || echo "⚠️ Advertencias de configuración detectadas, continuando..."

# Ejecutar migraciones
echo "🔄 Ejecutando migraciones..."
python manage.py migrate || echo "⚠️ Error en migraciones, continuando..."

# Crear superusuario si no existe (de forma más segura)
echo "👤 Verificando superusuario..."
python manage.py shell -c "
import os
from django.contrib.auth import get_user_model
try:
    User = get_user_model()
    if not User.objects.filter(is_superuser=True).exists():
        print('Creando superusuario por defecto...')
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print('Superusuario creado: admin/admin123')
    else:
        print('Superusuario ya existe')
except Exception as e:
    print(f'Error al verificar/crear superusuario: {e}')
" || echo "⚠️ Error al configurar superusuario, continuando..."

# Configurar roles si no existen
echo "🔐 Configurando roles del sistema..."
python manage.py setup_roles --create-roles || echo "Los roles ya están configurados o hubo un error"

# Recopilar archivos estáticos
echo "📦 Recopilando archivos estáticos..."
python manage.py collectstatic --noinput --clear || echo "⚠️ Error al recopilar estáticos, continuando..."

# Crear directorios de media necesarios
echo "📁 Creando directorios de media..."
python manage.py shell -c "
import os
from django.conf import settings
try:
    media_dirs = [
        'bancos', 'catalogo', 'clientes', 'paises', 
        'productores', 'temp_documents', 'temp_invoices'
    ]
    for dir_name in media_dirs:
        dir_path = os.path.join(settings.MEDIA_ROOT, dir_name)
        os.makedirs(dir_path, exist_ok=True)
        print(f'Directorio creado: {dir_path}')
except Exception as e:
    print(f'Error al crear directorios: {e}')
" || echo "⚠️ Error al crear directorios de media"

echo "✅ Configuración completada"
echo "🎯 Iniciando servidor..."

# Obtener el puerto de Railway o usar 8080   por defecto
PORT=${PORT:-8080}

# Ejecutar Gunicorn con configuración optimizada para Railway
exec gunicorn app.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --keep-alive 2 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile - \
    --error-logfile - \
    --log-level info