# AGENTS.md — django-custom-admin

## Project

Django 5.1 / Python 3.12+ / MySQL 8.0 / Redis. ERP-style admin for "Agrícola de la Costa San Luis" (Sinaloa, MX). Spanish (es-MX) default, English available.

## Settings & entrypoints

- Settings: `DJANGO_SETTINGS_MODULE=app.settings` — loads `.env` via python-dotenv
- WSGI: `app.wsgi:application`
- Root URLconf: `app.urls` — uses `i18n_patterns` (admin at `/es/admin/`, `/en/admin/`)
- Login: `two_factor:login` (2FA required for all admin access)
- Custom admin site: `app.admin_site.CustomAdminSite` (enforces 2FA via `AdminSiteOTPRequiredMixin`)

## Apps

| App                    | Purpose                                                                               |
| ---------------------- | ------------------------------------------------------------------------------------- |
| `app/`                 | Core — settings, urls, views, middleware, services, custom admin, management commands |
| `auditoria/`           | Audit logging (LogActividad, UserProfile, SiteConfiguration), middleware              |
| `catalogo/`            | Catalog — products, producers, countries, states, branches                            |
| `gastos/`              | Expenses, purchases, AI invoice recognition (LangChain + Google Gemini)               |
| `ventas/`              | Sales, clients, accounts receivable, payment tracking                                 |
| `capital_inversiones/` | Capital and investments                                                               |
| `reportes/`            | AI executive reports, email dispatch                                                  |

## Services layer

All in `app/services/`:

- `cache_service.py` — centralized Redis caching with `@cache_result` decorator, key hashing, warm-up, pattern invalidation
- `base_report_service.py` — abstract `BaseReportService` with template method pattern for balance/statistics/period aggregation
- `balance_service.py` — concrete for Gastos
- `compras_service.py`, `ventas_service.py` — additional concrete services
- `excel_service.py` — Excel report generation

## Dev commands

```bash
# Local
python manage.py runserver

# Windows shortcut
runserver.bat

# Docker dev (MySQL on port 3307, Redis on 6379)
make dev-up           # docker-compose -f docker-compose.dev.yml up -d
make migrate-dev
make superuser-dev
make shell-dev

# Docker production
make up              # docker-compose up -d
make migrate
make setup-roles     # python manage.py setup_roles --create-roles
```

## Django admin commands

```bash
# Role management
python manage.py setup_roles --create-roles
python manage.py setup_roles --assign-role <username> Administrador
python manage.py setup_roles --list-roles
python manage.py setup_roles --show-user-role <username>

# Other
python manage.py compilemessages
python manage.py collectstatic --noinput --clear
python manage.py optimize_database
```

## Testing

```bash
pytest                                          # all tests (--tb=short by default)
pytest app/tests/test_money_widget.py            # single file
pytest app/tests/test_cache_service.py           # cache unit tests
pytest app/tests/test_cache_integration.py       # cache integration tests (needs Redis)
pytest app/tests/test_integration.py             # cross-app integration tests
pytest app/tests/test_security.py                # OWASP coverage tests
pytest -m slow                                   # slow tests only
pytest -m performance                            # performance tests only

# Per-app tests (need DB)
pytest gastos/tests.py ventas/tests.py

# Integration tests (per-app, need DB)
pytest gastos/tests_integration.py ventas/tests_integration.py capital_inversiones/tests_integration.py

# Standalone scripts (NOT pytest)
python app/tests/test_normalizacion.py
python app/tests/test_categoria_seleccion.py
python app/tests/test_ai_system.py
```

### Test markers

- `slow` — long-running tests
- `performance` — stress/performance tests
- Filter warnings: `DeprecationWarning` ignored globally

## Features to know

- **Admin theme**: Uses **Jazzmin** (configured in settings.py, ~300 lines). NOT Django Unfold (README is misleading).
- **2FA**: `django-two-factor-auth` + `django-otp`. All admin access requires TOTP setup. Login at `/account/login/`, redirected to `two_factor:login`.
- **Brute-force protection**: `django-axes` — 5 attempts, 1h cooldown, locked per username+IP.
- **Redis cache**: 3 logical DBs (default `/1`, sessions `/2`, static `/3`). Falls back to `LocMemCache` if `REDIS_URL` unset.
- **i18n**: URLs use `i18n_patterns` (language prefix). PO files in `locale/{en,es,pt,de,fr}/LC_MESSAGES/`.
- **Currency**: `django-money` with MXN default, US number format (`.` decimal, `,` thousands).
- **Template tags**: in `gastos/templatetags/` and `ventas/templatetags/` (NOT in `app/`).
- **Static files**: WhiteNoise in production (`CompressedStaticFilesStorage`). CSS: `static/css/admin_custom.css` + Tailwind (no tailwind.config.js found).

## Docker dev quirks

- MySQL port `3307:3306` (avoid local MySQL conflict)
- Redis port `127.0.0.1:6379:6379`
- Code mounted live via volume (edit locally, reload in container)

## Dependency management

- `requirements.txt` — used by Docker and `pip install` (actively maintained)
- `pyproject.toml` — Poetry config (AI deps commented out; use requirements.txt for those)

## Middleware stack (order matters)

1. SecurityMiddleware
2. WhiteNoiseMiddleware
3. SessionMiddleware
4. LocaleMiddleware
5. CommonMiddleware
6. CsrfViewMiddleware
7. AuthenticationMiddleware
8. OTPMiddleware (2FA)
9. MessageMiddleware
10. XFrameOptionsMiddleware
11. CacheMiddleware (app.middleware.cache_middleware)
12. DatabaseCacheInvalidationMiddleware
13. AuthAuditMiddleware (auditoria.middleware)
14. AdminAuditMiddleware (auditoria.admin_middleware)
15. AxesMiddleware (brute-force)

## Known issues

- **C-01**: `ventas/views.py` views lack `@login_required` decorators (documented in `test_security.py`)
- AI dependencies active in `requirements.txt` but commented out in `pyproject.toml` (build issue)
- 3 standalone test scripts in `app/tests/` are NOT pytest-compatible
