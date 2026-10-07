# Sistema de Gestión Empresarial — Agrícola de la Costa

<div align="center">
  <img src="static/img/logo-sm.png" alt="Logo Agrícola de la Costa" width="200">
  <p><em>ERP administrativo y financiero con inteligencia artificial para operaciones agrícolas</em></p>
</div>

<p align="center">
  <a href="https://www.djangoproject.com/"><img src="https://img.shields.io/badge/Django-5.1-green.svg" alt="Django"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.12+-blue.svg" alt="Python"></a>
  <a href="https://www.mysql.com/"><img src="https://img.shields.io/badge/MySQL-8.0-orange.svg" alt="MySQL"></a>
  <a href="https://redis.io/"><img src="https://img.shields.io/badge/Redis-7.2-red.svg" alt="Redis"></a>
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED.svg" alt="Docker">
  <img src="https://img.shields.io/badge/2FA-Required-critical.svg" alt="2FA Required">
</p>

---

## Tabla de Contenidos

- [Descripción General](#descripción-general)
- [Stack Tecnológico](#stack-tecnológico)
- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Instalación Local](#instalación-local)
- [Configuración](#configuración)
- [Entorno con Docker](#entorno-con-docker)
- [Comandos de Desarrollo](#comandos-de-desarrollo)
- [Testing](#testing)
- [Módulos del Sistema](#módulos-del-sistema)
- [Seguridad](#seguridad)
- [Mantenimiento](#mantenimiento)
- [Documentación Adicional](#documentación-adicional)
- [Colaboradores](#colaboradores)

---

## Descripción General

Sistema ERP completo para **Agrícola de la Costa San Luis S.P.R. de R.L.** (Sinaloa, México). Gestiona operaciones financieras, ventas nacionales/exportación, gastos, compras, cuentas por cobrar, capital e inversiones, con soporte multiidioma (es-MX / en) y auditoría completa de actividad.

### Capacidades clave

- **Panel administrativo con Jazzmin**: Tema personalizado con dashboard integrado, menús configurables y soporte UI builder.
- **Autenticación reforzada**: 2FA obligatorio (TOTP) para acceso al admin + protección contra fuerza bruta (`django-axes`).
- **Procesamiento con IA**: Reconocimiento automático de facturas CFDI y estados de cuenta vía Google Gemini + LangChain.
- **Cuentas por cobrar**: Aging automático, estados de cuenta, alertas de vencimiento, cálculo de intereses moratorios.
- **Reportes ejecutivos**: Generación con IA y envío por correo de resúmenes financieros.
- **Multi-moneda**: `django-money` con MXN por defecto, conversión automática vía OpenExchangeRates.
- **Caché distribuido**: Redis con 3 DBs lógicas (default, sesiones, estáticos), fallback a LocMemCache.

---

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Framework | Django 5.1 |
| Lenguaje | Python 3.12+ |
| Base de datos | MySQL 8.0 (utf8mb4) |
| Caché | Redis 7.2 (3 DBs lógicos) |
| Admin UI | Django Jazzmin |
| Auth | django-two-factor-auth + django-otp + django-axes |
| Money | django-money + openpyxl |
| IA | LangChain + Google Gemini + PyPDF |
| Static | WhiteNoise + TailwindCSS + Flowbite |
| i18n | django-i18n (es-MX default) |
| Contenedores | Docker + docker-compose |

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                        Cliente                               │
│              (Navegador / Nginx en prod)                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    Django App                                │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────────────┐ │
│  │  app/   │ │ auditoria│ │ catalogo│ │     gastos/       │ │
│  │(core)   │ │(audit)  │ │(master) │ │ (expenses)        │ │
│  └─────────┘ └─────────┘ └─────────┘ └───────────────────┘ │
│  ┌─────────┐ ┌─────────────────┐ ┌───────────────────────┐ │
│  │ ventas/ │ │capital_inversiones│ │      reportes/       │ │
│  │(sales)  │ │  (investments)  │ │  (AI reports)        │ │
│  └─────────┘ └─────────────────┘ └───────────────────────┘ │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌────▼─────┐ ┌──────▼──────┐
│   MySQL 8.0  │ │  Redis   │ │  Media/     │
│  (Principal) │ │  (Cache) │ │  Static     │
└──────────────┘ └──────────┘ └─────────────┘
```

### Middleware (orden crítico)

1. `SecurityMiddleware`
2. `WhiteNoiseMiddleware`
3. `SessionMiddleware`
4. `LocaleMiddleware` (i18n)
5. `CommonMiddleware`
6. `CsrfViewMiddleware`
7. `AuthenticationMiddleware`
8. `OTPMiddleware` (2FA)
9. `MessageMiddleware`
10. `XFrameOptionsMiddleware`
11. `CacheMiddleware`
12. `DatabaseCacheInvalidationMiddleware`
13. `AuthAuditMiddleware`
14. `AdminAuditMiddleware`
15. `AxesMiddleware` (brute-force, siempre al final)

---

## Requisitos

### Base

- Python 3.12+
- MySQL 8.0+
- Redis 7.2+ (opcional en dev, usa LocMemCache fallback)
- Node.js 16+ y npm (solo para assets frontend)

### Opcionales (IA y email)

- Cuenta Google Cloud con API Key de Gemini
- Servidor SMTP o cuenta Resend para notificaciones
- App ID de OpenExchangeRates para conversión de divisas

---

## Instalación Local

### Opción A: Con Poetry

```bash
git clone https://github.com/Bitboy7/django-custom-admin.git
cd django-custom-admin

# Python deps
poetry install

# Frontend deps
npm install
```

### Opción B: Con pip + venv

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
npm install
```

> **Nota**: Las dependencias de IA están activas en `requirements.txt` pero comentadas en `pyproject.toml`. Usa `requirements.txt` para instalación completa.

---

## Configuración

1. **Variables de entorno**:

```bash
cp .env-example .env
```

Variables mínimas requeridas:

```env
# Base de datos
DB_NAME=agricola_costa_db
DB_USER=agricola_user
DB_PASSWORD=secure_password
DB_HOST=localhost
DB_PORT=3306
DB_ROOT_PASSWORD=root_password

# Django
SECRET_KEY=change-me-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Redis (opcional en dev)
# REDIS_URL=redis://localhost:6379/1

# IA (opcional)
GOOGLE_API_KEY=tu_api_key_gemini
GOOGLE_API_MODEL=gemini-2.5-flash

# Email (opcional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password
```

2. **Base de datos y datos iniciales**:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py setup_roles --create-roles
python manage.py compilemessages
python manage.py collectstatic --noinput --clear
```

3. **Acceso**:

- Admin: `http://localhost:8000/es/admin/` (requiere 2FA)
- Login 2FA: `http://localhost:8000/account/login/`

---

## Entorno con Docker

### Desarrollo (MySQL en puerto 3307, Redis en 6379)

```bash
# Iniciar servicios
make dev-up

# Migraciones, superusuario y shell
make migrate-dev
make superuser-dev
make shell-dev
```

### Producción

```bash
make up
make migrate
make setup-roles
make collectstatic
```

Ver `Makefile` para todos los comandos disponibles (`make help`).

---

## Comandos de Desarrollo

```bash
# Servidor de desarrollo
python manage.py runserver

# Windows shortcut
runserver.bat

# Gestión de roles
python manage.py setup_roles --create-roles
python manage.py setup_roles --assign-role <username> Administrador
python manage.py setup_roles --list-roles

# Optimización
python manage.py optimize_database
python manage.py setup_media_dirs

# Compilación de traducciones
python manage.py compilemessages

# Recopilación de estáticos
python manage.py collectstatic --noinput --clear
```

---

## Testing

```bash
# Todos los tests
pytest

# Tests específicos
pytest app/tests/test_security.py          # OWASP / seguridad
pytest app/tests/test_cache_service.py     # Cache unitario
pytest app/tests/test_cache_integration.py # Cache + Redis
pytest app/tests/test_integration.py       # Cross-app
pytest app/tests/test_money_widget.py      # Widgets

# Tests por app (requieren DB)
pytest gastos/tests.py ventas/tests.py

# Tests de integración por app
pytest gastos/tests_integration.py
pytest ventas/tests_integration.py
pytest capital_inversiones/tests_integration.py

# Scripts standalone (no pytest)
python app/tests/test_normalizacion.py
python app/tests/test_categoria_seleccion.py
python app/tests/test_ai_system.py
```

### Marcadores de pytest

- `slow` — tests de larga duración
- `performance` — stress tests

---

## Módulos del Sistema

| Módulo | Ruta | Propósito |
|--------|------|-----------|
| **Core** | `app/` | Settings, URLs, WSGI, middleware, servicios compartidos (cache, reportes, Excel), admin site customizado |
| **Auditoría** | `auditoria/` | LogActividad, UserProfile, SiteConfiguration, middleware de login/logout y admin CRUD |
| **Catálogo** | `catalogo/` | Productos, productores, países, estados, sucursales |
| **Gastos** | `gastos/` | Gastos, compras, bancos, cuentas, saldos mensuales, reconocimiento de facturas con IA |
| **Ventas** | `ventas/` | Ventas nacionales/exportación, clientes, agentes aduanales, anticipos, pagos, cuentas por cobrar, estados de cuenta, reporte de cobranza |
| **Capital** | `capital_inversiones/` | Capital e inversiones |
| **Reportes** | `reportes/` | Reportes ejecutivos con IA, configuración de envío por email, historial de reportes |

---

## Seguridad

- **2FA obligatorio**: Todos los usuarios del admin deben configurar TOTP antes del primer acceso.
- **Bloqueo por fuerza bruta**: `django-axes` — 5 intentos fallidos = bloqueo 1 hora (por usuario + IP).
- **Contraseñas**: Mínimo 12 caracteres, validación NIST SP 800-63B.
- **Headers de seguridad**: HSTS, XSS Filter, Content-Type nosniff, X-Frame DENY (en producción).
- **Sesiones**: 8 horas de duración, expiran al cerrar navegador.
- **Auditoría**: Cada login/logout y CRUD en admin se registra en `LogActividad` con IP, navegador y campos modificados.

---

## Mantenimiento

### Backup

```bash
# JSON dump
python manage.py dumpdata > backup_$(date +%Y%m%d).json

# SQL dump (Docker)
docker-compose exec db mysqldump -u root -p$DB_ROOT_PASSWORD $DB_NAME > backup_$(date +%Y%m%d).sql
```

### Logs

```bash
# Local
tail -f logs/app.log

# Docker
make logs
```

### Actualización de dependencias

```bash
# Python
pip install -r requirements.txt --upgrade

# Frontend
npm update

# Migraciones y estáticos
python manage.py migrate
python manage.py collectstatic --noinput
```

---

## Documentación Adicional

| Documento | Contenido |
|-----------|-----------|
| [`AGENTS.md`](AGENTS.md) | Guía rápida para desarrolladores y sesiones de IA |
| [`Docs/ROLES_GUIDE.md`](Docs/ROLES_GUIDE.md) | Matriz de permisos por rol |
| [`Docs/AI_INVOICE_MODULE.md`](Docs/AI_INVOICE_MODULE.md) | Arquitectura del módulo de IA para facturas |
| [`Docs/DEPLOYMENT_GUIDE.md`](Docs/DEPLOYMENT_GUIDE.md) | Guía de despliegue en producción |
| [`Docs/SECURITY_AUDIT_REPORT.md`](Docs/SECURITY_AUDIT_REPORT.md) | Reporte de auditoría de seguridad |
| [`Docs/BACKEND_SERVICES_ARCHITECTURE.md`](Docs/BACKEND_SERVICES_ARCHITECTURE.md) | Documentación de la capa de servicios |

> La carpeta `Docs/` contiene más de 30 documentos técnicos organizados por módulo.

---

## Colaboradores

- **Dev Y** — Desarrollador principal — [@Bitboy7](https://github.com/Bitboy7)

---

## Licencia

Este proyecto es propiedad de **Agrícola de la Costa San Luis S.P.R. de R.L.**

---

<p align="center">
  <sub>Construido con Django 5.1 · Python 3.12 · MySQL 8.0 · Redis · Docker</sub>
</p>
