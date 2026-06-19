# Sistema de Gestión Empresarial - Agrícola de la Costa

<div align="center">
  <img src="static/img/logo-sm.png" alt="Logo Agrícola de la Costa" width="250">
  <p><i>Sistema integral de gestión administrativa y financiera con IA</i></p>
</div>

## 📋 Descripción General

Este sistema proporciona una plataforma completa para la gestión administrativa y financiera de **Agrícola de la Costa San Luis S.P.R. de R.L.** Desarrollado con Django y tecnologías modernas, incluye procesamiento de documentos con inteligencia artificial, interfaz responsive y un completo sistema de auditoría.

[![Django](https://img.shields.io/badge/Django-5.1.3-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-orange.svg)](https://www.mysql.com/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-38B2AC.svg)](https://tailwindcss.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)

## 🚀 Características Principales

- **Panel de Administración Personalizado**: Interfaz moderna con Django Unfold
- **Procesamiento con IA**: Reconocimiento automático de facturas y estados de cuenta usando Google Gemini
- **Sistema de Roles y Permisos**: Control granular de acceso para usuarios (5 roles predefinidos)
- **Gestión de Catálogos**: Productos, proveedores, clientes y más
- **Control Financiero**: Seguimiento de gastos, ventas e inventario
- **Reportes y Balances**: Análisis de datos y exportación a Excel/PDF
- **Auditoría Completa**: Registro detallado de todas las acciones de usuarios
- **Interfaz Responsive**: Diseño moderno con TailwindCSS y Flowbite
- **Containerización**: Deployment listo con Docker y docker-compose

## 📋 Tabla de Contenidos

- [Requisitos del Sistema](#requisitos-del-sistema)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Deployment con Docker](#deployment-con-docker)
- [Uso](#uso)
- [Módulos del Sistema](#módulos-del-sistema)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Gestión de Roles](#gestión-de-roles)
- [Funciones de IA](#funciones-de-ia)
- [Mantenimiento](#mantenimiento)
- [Colaboradores](#colaboradores)

## 💻 Requisitos del Sistema

### Requisitos Base

- Python 3.12 o superior
- MySQL 8.0 o superior
- Node.js 16+ y npm (para assets frontend)
- Poetry (recomendado para gestión de dependencias)

### Para Funciones de IA (Opcional)

- Cuenta de Google Cloud con acceso a Gemini API
- Variables de entorno configuradas para servicios de IA

## 🔧 Instalación

### Con Poetry (Recomendado)

1. **Clonar el repositorio**:

   ```bash
   git clone https://github.com/Bitboy7/django-custom-admin.git
   cd django-custom-admin
   ```

2. **Instalar dependencias con Poetry**:

   ```bash
   poetry install
   ```

3. **Instalar dependencias frontend**:

   ```bash
   npm install
   ```

4. **Compilar assets CSS con Tailwind**:
   ```bash
   npx tailwindcss -i ./static/css/input.css -o ./static/css/output.css --watch
   ```

### Con Pip

1. **Crear y activar un entorno virtual**:

   ```bash
   python -m venv venv
   # En Windows
   venv\Scripts\activate
   # En Linux/Mac
   source venv/bin/activate
   ```

2. **Instalar dependencias**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Instalar dependencias frontend**:
   ```bash
   npm install
   ```

## ⚙️ Configuración

1. **Configurar variables de entorno**:
   - Copia `.env.example` a `.env`
   - Actualiza las variables según tu entorno:

   ```env
   # Base de datos
   DB_NAME=tu_base_datos
   DB_USER=tu_usuario
   DB_PASSWORD=tu_contraseña
   DB_HOST=localhost

   # Django
   SECRET_KEY=tu_clave_secreta
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1

   # IA (Opcional)
   GOOGLE_API_KEY=tu_api_key_gemini
   ```

2. **Configurar base de datos**:

   ```bash
   # Aplicar migraciones
   python manage.py migrate
   ```

3. **Crear superusuario**:

   ```bash
   python manage.py createsuperuser
   ```

4. **Configurar roles iniciales**:
   ```bash
   python manage.py setup_roles --create-roles
   ```

## 🐳 Deployment con Docker

### Desarrollo Local

1. **Crear archivo .env** con las variables necesarias

2. **Iniciar servicios**:

   ```bash
   docker-compose up -d
   ```

3. **Aplicar migraciones**:

   ```bash
   docker-compose exec web python manage.py migrate
   ```

4. **Crear superusuario**:
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

### Producción

Para deployment en producción, modifica las variables de entorno en `.env` y ajusta la configuración de `docker-compose.yml` según tus necesidades.

## 🏃‍♂️ Uso

### Iniciar el servidor

```bash
# Con Poetry
poetry shell
python manage.py runserver

# Con venv activado
python manage.py runserver

# Con Script de inicio rápido (Windows)
runserver.bat

# Con Docker
docker-compose up
```

Accede a la aplicación en tu navegador: http://localhost:8000/admin

### Comandos útiles

```bash
# Asignar rol a un usuario
python manage.py setup_roles --assign-role <username> <rol>

# Listar usuarios y sus roles
python manage.py shell -c "from django.contrib.auth.models import User; from app.permissions import RoleManager; [print(f'{user.username}: {RoleManager.get_user_role(user) or \"Sin rol\"}') for user in User.objects.all()]"

# Compilar assets en producción
python manage.py collectstatic

# Compilar CSS con Tailwind (desarrollo)
npx tailwindcss -i ./static/css/input.css -o ./static/css/output.css --watch
```

## 🏗️ Módulos del Sistema

### Core (app/)

- **Configuración principal**: Settings, URLs, middleware
- **Servicios compartidos**: Balances, exportación, utilidades
- **Sistema de permisos**: Gestión de roles y permisos granulares

### Auditoría (auditoria/)

- **Registro de actividad**: Tracking de acciones de usuarios
- **Middleware de auditoría**: Captura automática de eventos
- **Reportes de seguridad**: Análisis de accesos y cambios

### Catálogo (catalogo/)

- **Gestión de productos**: CRUD completo con categorías
- **Proveedores**: Información de contactos y productos
- **Clientes**: Base de datos de clientes y historial

### Gastos (gastos/)

- **Control de gastos**: Registro y categorización
- **Reconocimiento con IA**: Procesamiento automático de facturas
- **Estados de cuenta**: Análisis de movimientos bancarios
- **Reportes financieros**: Balances y análisis de gastos

### Ventas (ventas/)

- **Gestión de ventas**: Facturas y cotizaciones
- **Control de inventario**: Stock y movimientos
- **Análisis de ventas**: Reportes de rendimiento

## 📁 Estructura del Proyecto

```
django-custom-admin/
├── app/                  # Configuración principal y servicios core
│   ├── management/       # Comandos personalizados (setup_roles, etc.)
│   ├── permissions.py    # Sistema de gestión de roles
│   └── services/         # Servicios compartidos (balances, etc.)
├── auditoria/            # Sistema de registro de actividad
├── catalogo/             # Gestión de productos y proveedores
├── gastos/               # Control de gastos y compras
├── ventas/               # Gestión de ventas y clientes
├── static/               # Archivos estáticos
│   ├── css/              # Estilos personalizados y Tailwind
│   ├── js/               # JavaScript y componentes
│   └── img/              # Imágenes y recursos gráficos
├── templates/            # Plantillas HTML con componentes Tailwind
├── media/                # Archivos subidos por usuarios
├── logs/                 # Archivos de registro de la aplicación
├── Docs/                 # Documentación del proyecto
│   ├── AI_INVOICE_MODULE.md    # Documentación del módulo de IA
│   ├── ROLES_GUIDE.md          # Guía de roles y permisos
│   └── SISTEMA_CATEGORIAS_IA.md # Sistema de categorización
├── docker-compose.yml    # Configuración de contenedores
├── Dockerfile           # Imagen de la aplicación
├── manage.py            # Script de gestión de Django
├── pyproject.toml       # Configuración de Poetry
├── package.json         # Dependencias frontend (Tailwind, Flowbite)
├── tailwind.config.js   # Configuración de TailwindCSS
└── requirements.txt     # Dependencias del proyecto
```

## 👥 Gestión de Roles

El sistema incluye cinco roles predefinidos:

1. **Administrador**: Acceso completo al sistema
2. **Gerente**: Acceso a reportes y gestión general
3. **Contador**: Gestión completa de finanzas
4. **Vendedor**: Gestión de ventas y clientes
5. **Operador**: Acceso de solo lectura

Para más detalles sobre los permisos y configuración de roles, consulta [ROLES_GUIDE.md](Docs/ROLES_GUIDE.md).

## 🤖 Funciones de IA

El sistema incluye un módulo avanzado de reconocimiento de documentos:

### Características de IA

- **Motor**: LangChain + Google Gemini 2.0 Flash Experimental
- **Tipos de documento**: Facturas individuales y estados de cuenta bancarios
- **Extracción estructurada**: Datos validados con modelos Pydantic
- **Interfaz guiada**: Proceso paso a paso con confirmación de datos

### Configuración de IA

1. **Obtener API Key de Google Gemini**
2. **Configurar variable de entorno**:
   ```env
   GOOGLE_API_KEY=tu_api_key_aqui
   ```
3. **Instalar dependencias de IA** (descomentarlas en `pyproject.toml`)

Para documentación completa, consulta [AI_INVOICE_MODULE.md](Docs/AI_INVOICE_MODULE.md).

## 🧩 Extensión del Sistema

### Añadir Nuevos Módulos

1. **Crear nueva app Django**:

   ```bash
   python manage.py startapp nueva_app
   ```

2. **Configurar permisos** en `app/permissions.py`
3. **Registrar en admin** con Django Unfold
4. **Añadir a INSTALLED_APPS** en settings

### Personalización del Admin

- **Temas**: Configuración en Django Unfold
- **Componentes**: TailwindCSS + Flowbite
- **Menús**: Personalización en cada app/admin.py

### Integración con Servicios Externos

- **APIs**: Estructura preparada en services/
- **Webhooks**: Middleware personalizable
- **Exportación**: Excel, PDF, CSV integrados

## 🛠️ Mantenimiento

### Respaldo de base de datos

```bash
# Exportar la base de datos
python manage.py dumpdata > backup_$(Get-Date -Format "yyyyMMdd").json

# Con Docker
docker-compose exec web python manage.py dumpdata > backup_$(Get-Date -Format "yyyyMMdd").json
```

### Actualización del sistema

```bash
# Actualizar dependencias Python
poetry update
# o con pip
pip install -r requirements.txt --upgrade

# Actualizar dependencias frontend
npm update

# Aplicar migraciones pendientes
python manage.py migrate

# Recompilar assets estáticos
python manage.py collectstatic --noinput
```

### Logs y Monitoreo

```bash
# Ver logs de la aplicación
tail -f logs/app.log

# Con Docker
docker-compose logs -f web
```

### Limpieza de archivos temporales

```bash
# Limpiar archivos temporales de media
python manage.py shell -c "
import os
temp_dirs = ['media/temp_documents/', 'media/temp_invoices/']
for temp_dir in temp_dirs:
    if os.path.exists(temp_dir):
        for file in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, file))
"
```

## 👨‍💻 Colaboradores

- **Dev Y** - _Desarrollador principal_ - [Bitboy7](https://github.com/Bitboy7)

---

## 📄 Licencia

Este proyecto es propietario de **Agrícola de la Costa San Luis S.P.R. de R.L.**

## 🆘 Soporte

Para reportar bugs o solicitar nuevas características:

1. **Issues**: Usa el sistema de issues de GitHub
2. **Documentación**: Consulta la carpeta `Docs/` para guías detalladas
3. **Contacto**: A través del repositorio en GitHub

## 🏷️ Versiones

- **v1.2** (Actual): Módulo de IA, TailwindCSS, Docker
- **v1.1**: Sistema de auditoría, roles mejorados
- **v1.0**: Sistema base con Django Unfold

## 🔗 Enlaces Útiles

- [Django Documentation](https://docs.djangoproject.com/)
- [Django Unfold](https://github.com/unfoldadmin/django-unfold)
- [TailwindCSS](https://tailwindcss.com/)
- [Flowbite Components](https://flowbite.com/)
- [Google Gemini API](https://ai.google.dev/)
