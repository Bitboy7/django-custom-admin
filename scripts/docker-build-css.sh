#!/bin/sh
# Script de ayuda para build de CSS en Docker
# Copia templates si existen, sin fallar si no

set -e

# Root del proyecto
APP_ROOT="/app"

# Directorio de salida
mkdir -p "$APP_ROOT"

echo "Copying Tailwind configuration..."
[ -f tailwind.config.js ] && cp tailwind.config.js "$APP_ROOT/" || echo "⚠ tailwind.config.js not found"
[ -f postcss.config.js ] && cp postcss.config.js "$APP_ROOT/" || echo "⚠ postcss.config.js not found"

echo "Copying static and template files..."
[ -d static/css ] && cp -r static/css "$APP_ROOT/static/" || mkdir -p "$APP_ROOT/static/css"
[ -d templates ] && cp -r templates "$APP_ROOT/" || echo "⚠ root templates not found"

# Copiar templates de cada app si existen
for app in app auditoria catalogo gastos ventas capital_inversiones reportes; do
    if [ -d "$app/templates" ]; then
        echo "  ✓ Copying $app/templates"
        mkdir -p "$APP_ROOT/$app"
        cp -r "$app/templates" "$APP_ROOT/$app/"
    else
        echo "  ℹ $app/templates not found (optional)"
    fi
done

echo "✓ All files copied successfully"
