## 🎨 Instalación de Tailwind CSS — Producción & Desarrollo

### ✅ Lo que se instaló

- ✅ `tailwind.config.js` — Configuración de Tailwind con tema personalizado
- ✅ `postcss.config.js` — PostCSS con autoprefixer
- ✅ `static/css/input.css` — Punto de entrada para compilación
- ✅ **package.json** — Scripts de build actualizados
- ✅ **Dockerfile** — Multi-stage build (Node.js + Python)
- ✅ **app/settings.py** — JAZZMIN_SETTINGS actualizado a `output.css`
- ✅ **.gitignore** — Agregado `static/css/output.css`

---

## 📦 Instalación Local (Desarrollo)

### Paso 1: Instalar dependencias

```bash
npm install
```

### Paso 2: Generar CSS compilado

```bash
# Compilar CSS una sola vez
npm run build:css

# O monitorear cambios en tiempo real
npm run watch:css
```

El archivo compilado se guardará en: **`static/css/output.css`**

### Paso 3: Ejecutar Django

```bash
python manage.py collectstatic --noinput
python manage.py runserver
```

O usar el script de Windows:

```bash
runserver.bat
```

---

## 🐳 Instalación en Producción (Docker)

### Multi-Stage Build automático

El nuevo **Dockerfile** usa 2 etapas:

1. **Stage 1 (Node.js)**: Compila CSS con Tailwind → `output.css`
2. **Stage 2 (Python)**: Copia `output.css` compilado + ejecuta Gunicorn

### Construir imagen

```bash
docker build -t django-custom-admin:latest .
```

O con compose:

```bash
docker-compose up --build
```

**El CSS ya está compilado y minificado** ✨

---

## 🎯 Cómo funciona

### Desarrollo

```
Editas HTML/tailwind.config.js
         ↓
npm run watch:css
         ↓
static/css/output.css se regenera automáticamente
         ↓
Recargas el navegador → Cambios visibles
```

### Producción

```
docker build .
         ↓
Stage 1: Node.js compila Tailwind → output.css
         ↓
Stage 2: Python copia output.css + corre Gunicorn
         ↓
static/css/output.css ya minificado en la imagen
         ↓
Contenedor listo sin necesidad de Node.js en runtime
```

---

## 📝 Estructura de archivos

```
django-custom-admin/
├── tailwind.config.js          ← Configuración de Tailwind
├── postcss.config.js            ← Configuración de PostCSS
├── Dockerfile                   ← Multi-stage (actualizado)
├── package.json                 ← Scripts npm (actualizado)
├── static/css/
│   ├── input.css               ← Punto de entrada (nuevo)
│   ├── output.css              ← CSS compilado (generado)
│   ├── admin_custom.css        ← Aún existe, pero no se usa
│   ├── tokens.css              ← Variables CSS
│   ├── base.css                ← Reset y tipografía
│   ├── layout.css              ← Navbar, sidebar
│   ├── components.css          ← Botones, cards
│   ├── forms.css               ← Inputs, validación
│   ├── tables.css              ← Tablas, DataTables
│   ├── dashboard.css           ← KPI cards
│   ├── login.css               ← Página de login
│   └── money_widget.css        ← Widget moneda
└── app/settings.py             ← JAZZMIN apunta a output.css
```

---

## 🔍 Verificación

### 1. Desarrollo — Ver si CSS se compila

```bash
npm run build:css
# Output esperado:
# > tailwindcss -i ./static/css/input.css -o ./static/css/output.css --minify
# Done. Generated: static/css/output.css
```

### 2. Producción — Verificar en Docker

```bash
docker build -t test-build .

# Ver logs de compilación
docker build --progress=plain -t test-build .

# Debe mostrar:
# #11 [node-builder 5/8] RUN npm run build:css
# #12 > tailwindcss -i ./static/css/input.css -o ./static/css/output.css --minify
```

### 3. Verificar que output.css existe

```bash
ls -lh static/css/output.css

# Debe existir y tener tamaño razonable (~50-200 KB minificado)
```

---

## 🚀 Comandos útiles

| Comando                         | Descripción                          |
| ------------------------------- | ------------------------------------ |
| `npm install`                   | Instalar dependencias (una sola vez) |
| `npm run build:css`             | Compilar CSS una vez                 |
| `npm run watch:css`             | Monitorear cambios (desarrollo)      |
| `npm test`                      | Ejecutar tests Jest                  |
| `npm run build:css && npm test` | Build + tests                        |

---

## ⚡ Optimizaciones incluidas

✅ **Minificación automática** — `output.css` está comprimido (`--minify`)
✅ **Purging** — Solo clases usadas en templates se incluyen
✅ **Tailwind 3.4** — Último LTS con nuevas features
✅ **Flowbite** — Componentes pre-built incluidos
✅ **Autoprefixer** — Compatibilidad entre navegadores
✅ **Multi-stage Docker** — Node.js no en runtime ⬇️ 50% tamaño imagen

---

## 🔧 Troubleshooting

### "output.css no se genera"

```bash
# Verifica que input.css existe
ls static/css/input.css

# Verifica que tailwind.config.js está en la raíz
ls tailwind.config.js

# Limpia node_modules e instala de nuevo
rm -r node_modules package-lock.json
npm install
npm run build:css
```

### "CSS no se aplica en admin"

1. Verifica que `static/css/output.css` existe
2. Ejecuta `python manage.py collectstatic --noinput`
3. Verifica que `app/settings.py` tiene `"custom_css": "css/output.css"`
4. Recarga la página (Ctrl+Shift+R para hard-refresh)

### "Docker build es muy lento"

```bash
# Verifica que npm ci es rápido
npm cache clean --force
docker build --no-cache -t django-custom-admin:latest .
```

---

## 📚 Documentación

- [Tailwind CSS Docs](https://tailwindcss.com)
- [PostCSS Docs](https://postcss.org)
- [Flowbite Components](https://flowbite.com)
- [Django StaticFiles](https://docs.djangoproject.com/en/5.1/howto/static-files/)
