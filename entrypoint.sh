#!/bin/bash

# Script de inicio para producción
# Este script prepara la aplicación para ejecutarse en producción

set -e

echo "🚀 Iniciando configuración de producción..."

# Ejecutar migraciones
echo "🔄 Ejecutando migraciones..."
python manage.py migrate --noinput

# Crear superusuario si no existe
echo "👤 Verificando superusuario..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    print('Creando superusuario por defecto...')
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superusuario creado: admin/admin123')
else:
    print('Superusuario ya existe')
"

# Configurar roles si no existen
echo "🔐 Configurando roles del sistema..."
python manage.py setup_roles --create-roles || echo "Los roles ya están configurados"

# Recopilar archivos estáticos
echo "📦 Recopilando archivos estáticos..."
python manage.py collectstatic --noinput --clear

# Crear directorios de media necesarios
echo "📁 Creando directorios de media..."
python manage.py shell -c "
import os
from django.conf import settings

media_dirs = [
    'bancos', 'catalogo', 'clientes', 'paises', 
    'productores', 'temp_documents', 'temp_invoices'
]

for dir_name in media_dirs:
    dir_path = os.path.join(settings.MEDIA_ROOT, dir_name)
    os.makedirs(dir_path, exist_ok=True)
    print(f'Directorio creado: {dir_path}')
"

echo "✅ Configuración de producción completada"
echo "🎯 Iniciando servidor Gunicorn..."

# Ejecutar Gunicorn
exec gunicorn app.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --keep-alive 2 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile - \
    --error-logfile -
