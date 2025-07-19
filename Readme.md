# Sistema de Gestión Empresarial - Agrícola de la Costa

<div align="center">
  <img src="static/img/logo-sm.png" alt="Logo Agrícola de la Costa" width="250">
  <p><i>Sistema integral de gestión administrativa y financiera</i></p>
</div>

## 📋 Descripción General

Este sistema proporciona una plataforma completa para la gestión administrativa y financiera de **Agrícola de la Costa San Luis S.P.R. de R.L.** Desarrollado con Django y tecnologías modernas, ofrece una interfaz intuitiva para el control de operaciones, ventas, gastos y reportes.

[![Django](https://img.shields.io/badge/Django-5.1.3-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-orange.svg)](https://www.mysql.com/)

## 🚀 Características Principales

- **Panel de Administración Personalizado**: Interfaz moderna con Django Unfold
- **Sistema de Roles y Permisos**: Control granular de acceso para usuarios
- **Gestión de Catálogos**: Productos, proveedores, clientes y más
- **Control Financiero**: Seguimiento de gastos, ventas e inventario
- **Reportes y Balances**: Análisis de datos y exportación a Excel
- **Auditoría de Actividad**: Registro detallado de acciones de usuarios

## 📋 Tabla de Contenidos

- [Requisitos del Sistema](#requisitos-del-sistema)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso](#uso)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Gestión de Roles](#gestión-de-roles)
- [Mantenimiento](#mantenimiento)
- [Colaboradores](#colaboradores)

## 💻 Requisitos del Sistema

- Python 3.10 o superior
- MySQL 8.0 o superior
- Node.js y npm (para assets frontend)
- Poetry (recomendado para gestión de dependencias)

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

3. **Activar el entorno virtual**:
   ```bash
   poetry shell
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

## ⚙️ Configuración

1. **Configurar variables de entorno**:

   - Copia `.env.example` a `.env`
   - Actualiza las variables según tu entorno

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

## 🏃‍♂️ Uso

### Iniciar el servidor

```bash
# Con Python directamente
python manage.py runserver

# Con Script de inicio rápido (Windows)
runserver.bat
```

Accede a la aplicación en tu navegador: http://localhost:8000/admin

### Comandos útiles

```bash
# Asignar rol a un usuario
python manage.py setup_roles --assign-role <username> <rol>

# Listar usuarios y sus roles
python manage.py shell -c "from django.contrib.auth.models import User; from app.permissions import RoleManager; [print(f'{user.username}: {RoleManager.get_user_role(user) or \"Sin rol\"}') for user in User.objects.all()]"
```

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
│   ├── css/              # Estilos personalizados
│   ├── js/               # JavaScript
│   └── img/              # Imágenes y recursos gráficos
├── templates/            # Plantillas HTML
├── media/                # Archivos subidos por usuarios
├── logs/                 # Archivos de registro
├── manage.py             # Script de gestión de Django
├── pyproject.toml        # Configuración de Poetry
└── requirements.txt      # Dependencias del proyecto
```

## 👥 Gestión de Roles

El sistema incluye cinco roles predefinidos:

1. **Administrador**: Acceso completo al sistema
2. **Gerente**: Acceso a reportes y gestión general
3. **Contador**: Gestión completa de finanzas
4. **Vendedor**: Gestión de ventas y clientes
5. **Operador**: Acceso de solo lectura

Para más detalles sobre los permisos y configuración de roles, consulta [ROLES_GUIDE.md](ROLES_GUIDE.md).

## 🧩 Extensión del Sistema

Consulta la documentación detallada para:

- Añadir nuevos módulos
- Personalizar el panel de administración
- Integrar con servicios externos
- Configurar exportación de datos

## 🛠️ Mantenimiento

### Respaldo de base de datos

```bash
# Exportar la base de datos
python manage.py dumpdata > backup_$(date +%Y%m%d).json
```

### Actualización del sistema

```bash
# Actualizar dependencias
poetry update
# Aplicar migraciones pendientes
python manage.py migrate
```

## 👨‍💻 Colaboradores

- **Dev Y** - _Desarrollador principal_ - [Bitboy7](https://github.com/Bitboy7)
