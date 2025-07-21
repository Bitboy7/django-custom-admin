# Guía de Traducciones Multi-idioma

Este proyecto incluye soporte completo para traducciones en múltiples idiomas.

## Idiomas Soportados

- **Español (es)** - Idioma principal
- **Inglés (en)** - English
- **Francés (fr)** - Français
- **Alemán (de)** - Deutsch
- **Portugués (pt)** - Português

## Configuración para Desarrollo Local (Windows)

### Opción 1: Script Automático

Ejecuta el script de configuración:

```powershell
.\setup_translations.ps1
```

### Opción 2: Configuración Manual

1. **Compilar traducciones:**

   ```bash
   python compile_messages.py
   ```

2. **Habilitar middleware de localización en `app/settings.py`:**

   ```python
   MIDDLEWARE = [
       # ... otros middlewares ...
       "django.middleware.locale.LocaleMiddleware",  # Habilitar esta línea
       # ... resto de middlewares ...
   ]
   ```

3. **Iniciar servidor:**
   ```bash
   python manage.py runserver
   ```

## Configuración para Producción (Linux/Docker)

El Dockerfile ya incluye `gettext` y el entrypoint.sh compila automáticamente las traducciones:

```dockerfile
# Gettext ya incluido en Dockerfile
RUN apt-get install -y gettext
```

```bash
# Compilación automática en entrypoint.sh
python manage.py compilemessages
```

## Estructura de Archivos

```
locale/
├── es/LC_MESSAGES/
│   ├── django.po  # Archivo de traducciones en español
│   └── django.mo  # Archivo compilado para español
├── en/LC_MESSAGES/
│   ├── django.po  # Archivo de traducciones en inglés
│   └── django.mo  # Archivo compilado para inglés
├── fr/LC_MESSAGES/
│   ├── django.po  # Archivo de traducciones en francés
│   └── django.mo  # Archivo compilado para francés
├── de/LC_MESSAGES/
│   ├── django.po  # Archivo de traducciones en alemán
│   └── django.mo  # Archivo compilado para alemán
└── pt/LC_MESSAGES/
    ├── django.po  # Archivo de traducciones en portugués
    └── django.mo  # Archivo compilado para portugués
```

## Uso en Templates

Para marcar texto para traducción, usa el tag `{% trans %}`:

```html
<!-- En lugar de texto fijo -->
<h1>Panel de Control</h1>

<!-- Usa el tag de traducción -->
<h1>{% trans "Panel de Control" %}</h1>
```

## Cambio de Idioma

El admin de Django Unfold incluye un selector de idioma automático en la esquina superior derecha que permite cambiar entre los idiomas configurados.

## Agregar Nuevas Traducciones

1. **Actualizar templates:** Añadir tags `{% trans %}` al texto nuevo
2. **Actualizar archivos .po:** Agregar las nuevas entradas a cada archivo de idioma
3. **Recompilar:** Ejecutar `python compile_messages.py`
4. **Reiniciar servidor:** Para que los cambios tomen efecto

## Problemas Comunes

### Error de gettext en Windows

- **Problema:** `Can't find msgfmt` o `Can't find msguniq`
- **Solución:** Usar el script `compile_messages.py` que no requiere gettext tools

### Error de codificación UTF-8

- **Problema:** `UnicodeDecodeError` al cargar traducciones
- **Solución:** Verificar que todos los archivos .po tengan `charset=UTF-8` en el header

### Traducciones no aparecen

- **Problema:** Los cambios de idioma no se reflejan
- **Solución:**
  1. Verificar que `LocaleMiddleware` esté habilitado
  2. Recompilar archivos .mo
  3. Reiniciar el servidor

## Comandos Útiles

```bash
# Generar archivos de mensajes (requiere gettext)
python manage.py makemessages -l en

# Compilar archivos de mensajes (requiere gettext)
python manage.py compilemessages

# Compilar con script personalizado (no requiere gettext)
python compile_messages.py

# Verificar configuración
python manage.py check

# Ejecutar con un idioma específico
LANGUAGE_CODE=en python manage.py runserver
```
