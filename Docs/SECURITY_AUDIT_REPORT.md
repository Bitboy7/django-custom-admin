# Auditoría de Seguridad — Django Custom Admin

**Sistema de Gestión Agrícola de la Costa San Luis**  
**Fecha:** 10 de Abril de 2026 · **Framework de análisis:** OWASP Top 10 2021  
**Tipo de análisis:** Revisión estática de código (SAST) · **Analista:** GitHub Copilot

---

## Resumen Ejecutivo

| Severidad  | Cantidad | Acción requerida                               |
| ---------- | -------- | ---------------------------------------------- |
| 🔴 Crítica | 3        | Resolver antes del próximo acceso a producción |
| 🟠 Alta    | 5        | Resolver antes del próximo deploy              |
| 🟡 Media   | 5        | Resolver en el siguiente sprint                |
| 🟢 Baja    | 4        | Mejora continua                                |
| **Total**  | **17**   |                                                |

**Base de seguridad general:** El sistema tiene una arquitectura correcta con SECRET_KEY externalizada,
middleware CSRF activo y un sistema de auditoría propio (`LogActividad`). Los hallazgos críticos
son concretos y con corrección directa.

---

## Estado de Controles Existentes

| Control                            | Estado            | Observación                  |
| ---------------------------------- | ----------------- | ---------------------------- |
| `SECRET_KEY` desde `.env`          | ✅ Correcto       | Variable de entorno          |
| `DEBUG` desde `.env`               | ✅ Correcto       |                              |
| `ALLOWED_HOSTS` desde `.env`       | ✅ Correcto       |                              |
| HSTS configurado (1 año)           | ✅ Correcto       | Solo en producción           |
| CSRF middleware activo             | ✅ Correcto       | Cubre todas las rutas        |
| Clickjacking middleware            | ⚠️ Parcial        | Solo se aplica en producción |
| Sistema `LogActividad`             | ✅ Existe         | Mejorar IP y datos sensibles |
| `AuthAuditMiddleware`              | ✅ Funcional      | Registra login/logout        |
| `AdminAuditMiddleware`             | ⚠️ Riesgo en logs | Ver HIGH-02                  |
| RBAC con `RoleManager`             | ⚠️ Bug en filtro  | Ver MED-04                   |
| `@login_required` en gastos        | ✅ Presente       |                              |
| `@staff_member_required` en perfil | ✅ Correcto       |                              |
| Credenciales de BD via `.env`      | ✅ Correcto       |                              |

---

## 🔴 HALLAZGOS CRÍTICOS

---

### [CRIT-01] Vistas de Ventas Accesibles sin Autenticación

**OWASP A01:2021 – Broken Access Control**  
**Archivos:** `ventas/views.py`, `ventas/urls.py`

**Descripción:**
Las vistas `lista_anticipos`, `crear_anticipo`, `detalle_venta`, `ventas_balances`,
`exportar_balances_xlsx` y `reporte_cobranza_global` no tienen ningún decorador de
autenticación. Cualquier usuario anónimo puede acceder a datos financieros de clientes
y sus anticipos visitando directamente `/ventas/anticipos/` o `/ventas/balances/`.

**Código vulnerable:**

```python
# ventas/views.py — SIN protección alguna
def lista_anticipos(request):          # ❌ Acceso público
    anticipos = Anticipo.objects.all()
    return render(request, 'lista_anticipos.html', {'anticipos': anticipos})

def crear_anticipo(request):           # ❌ Crea registros financieros sin autenticar
    if request.method == 'POST':
        form = AnticipoForm(request.POST)
        if form.is_valid():
            form.save()

def detalle_venta(request, venta_id):  # ❌ Expone datos de venta completos
    venta = get_object_or_404(Ventas, id=venta_id)
```

**Corrección — ventas/views.py:**

```python
from django.contrib.auth.decorators import login_required, permission_required

@login_required
@permission_required('ventas.view_anticipo', raise_exception=True)
def lista_anticipos(request):
    anticipos = Anticipo.objects.all()
    return render(request, 'lista_anticipos.html', {'anticipos': anticipos})

@login_required
@permission_required('ventas.add_anticipo', raise_exception=True)
def crear_anticipo(request):
    if request.method == 'POST':
        form = AnticipoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_anticipos')
    else:
        form = AnticipoForm()
    return render(request, 'crear_anticipo.html', {'form': form})

@login_required
@permission_required('ventas.view_ventas', raise_exception=True)
def detalle_venta(request, venta_id):
    venta = get_object_or_404(Ventas, id=venta_id)
    monto_final = venta.calcular_monto_final()
    return render(request, 'detalle_venta.html', {'venta': venta, 'monto_final': monto_final})

@login_required
@permission_required('ventas.view_ventas', raise_exception=True)
def ventas_balances(request):
    context = build_ventas_balances_context(request)
    return render(request, 'ventas/balances.html', context)

@login_required
@permission_required('ventas.view_ventas', raise_exception=True)
def exportar_balances_xlsx(request):
    # ... implementación existente
    pass

@login_required
@permission_required('ventas.view_ventas', raise_exception=True)
def reporte_cobranza_global(request):
    # ... implementación existente
    pass
```

---

### [CRIT-02] IP Spoofing en Logs de Auditoría

**OWASP A09:2021 – Security Logging and Monitoring Failures**  
**Archivo:** `auditoria/services.py`

**Descripción:**
La función `registrar_log` acepta directamente el primer valor de `HTTP_X_FORWARDED_FOR`
sin verificar que provenga de un proxy confiable. Un atacante puede establecer
`X-Forwarded-For: 127.0.0.1` y todos sus actos quedarán registrados bajo la IP
`127.0.0.1` (localhost), haciendo la auditoría inútil para investigaciones forenses.

**Código vulnerable:**

```python
# auditoria/services.py
x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
if x_forwarded_for:
    ip = x_forwarded_for.split(',')[0].strip()  # ❌ Cualquier cliente puede falsear esto
else:
    ip = request.META.get('REMOTE_ADDR')
```

**Corrección — auditoria/services.py:**

```python
import ipaddress

# Rangos IP de proxies internos confiables (ajustar según infraestructura)
_TRUSTED_PROXY_NETWORKS = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
]

def _get_real_ip(request):
    """
    Obtiene la IP real del cliente. Solo confía en X-Forwarded-For
    si REMOTE_ADDR pertenece a un proxy interno conocido.
    """
    remote_addr = request.META.get('REMOTE_ADDR', '')
    try:
        remote_ip = ipaddress.ip_address(remote_addr)
        is_trusted_proxy = any(remote_ip in net for net in _TRUSTED_PROXY_NETWORKS)
    except ValueError:
        return remote_addr

    if is_trusted_proxy:
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if forwarded_for:
            # Tomar la IP del cliente (primera en la cadena)
            client_ip = forwarded_for.split(',')[0].strip()
            try:
                ipaddress.ip_address(client_ip)  # Validar formato
                return client_ip
            except ValueError:
                return remote_addr

    return remote_addr


def registrar_log(request, tipo_accion, descripcion,
                  modelo_afectado=None, objeto_id=None, campos_modificados=None):
    usuario = request.user if request.user.is_authenticated else None
    nombre_usuario = usuario.username if usuario else 'Anónimo'
    ip = _get_real_ip(request)  # ✅ Usa la función segura
    navegador = request.META.get('HTTP_USER_AGENT', '')[:500]

    log = LogActividad.objects.create(
        usuario=usuario,
        nombre_usuario=nombre_usuario,
        tipo_accion=tipo_accion,
        descripcion=descripcion,
        modelo_afectado=modelo_afectado,
        objeto_id=objeto_id,
        campos_modificados=campos_modificados,
        direccion_ip=ip,
        navegador=navegador
    )
    return log
```

---

### [CRIT-03] Campo `cantidad` en Ventas es `CharField` — Corrupción de Datos Contables

**OWASP A04:2021 – Insecure Design**  
**Archivo:** `ventas/models.py`

**Descripción:**
El campo `cantidad` en el modelo `Ventas` es `CharField(max_length=50)`. Esto permite
guardar valores como `"veinte cajas"`, `"N/A"` o `"100 aprox"`. En un sistema financiero
agrícola, esto rompe cualquier cálculo de precio unitario, total de venta y reportes
de volumen. Es el equivalente a poder escribir texto en una celda de Excel vinculada
a una fórmula financiera.

**Código vulnerable:**

```python
# ventas/models.py
class Ventas(models.Model):
    cantidad = models.CharField(max_length=50)  # ❌ CharField en campo numérico crítico
```

**Corrección — ventas/models.py:**

```python
from django.core.validators import MinValueValidator
from decimal import Decimal

class Ventas(models.Model):
    cantidad = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text="Cantidad vendida (ej: 1500.000 kg)"
    )
```

**Pasos de migración seguros:**

```sql
-- 1. Verificar datos no numéricos existentes antes de migrar:
SELECT id, cantidad FROM ventas_ventas WHERE cantidad REGEXP '[^0-9.]';

-- 2. Corregir manualmente en BD si hay datos inválidos:
UPDATE ventas_ventas SET cantidad = '0' WHERE cantidad NOT REGEXP '^[0-9]+(\.[0-9]+)?$';
```

```bash
# 3. Crear y aplicar migration
python manage.py makemigrations ventas --name="cantidad_char_to_decimal"
python manage.py migrate
```

---

## 🟠 HALLAZGOS ALTOS

---

### [HIGH-01] Cookies de Sesión y CSRF No Seguras por Defecto en Producción

**OWASP A02:2021 – Cryptographic Failures**  
**Archivo:** `app/settings.py`

**Descripción:**
`SESSION_COOKIE_SECURE` y `CSRF_COOKIE_SECURE` están en `False` por defecto.
Si el equipo de DevOps despliega sin configurar estas variables de entorno, las
cookies de sesión viajarán en HTTP plano, permitiendo session hijacking con un
sniffer de red básico (Wireshark, mitmproxy).

**Código vulnerable:**

```python
# app/settings.py
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() in ["true", "1"]
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "False").lower() in ["true", "1"]
# ❌ Si la variable de entorno no está configurada → False → cookies inseguras en producción
```

**Corrección — app/settings.py:**

```python
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True").lower() in ["true", "1"]
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True    # ✅ True por defecto en producción — no depende de env
    CSRF_COOKIE_SECURE = True       # ✅ True por defecto en producción
    SESSION_COOKIE_HTTPONLY = True  # ✅ Previene acceso vía JavaScript (XSS)
    X_FRAME_OPTIONS = 'DENY'

# Fuera del bloque if not DEBUG (aplica siempre):
SESSION_COOKIE_AGE = 60 * 60 * 8       # 8 horas (jornada laboral)
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Sesión expira al cerrar navegador
SESSION_SAVE_EVERY_REQUEST = True       # Reinicia el timer en cada petición activa
```

---

### [HIGH-02] Auditoría Registra Datos POST Crudos — Posible Exposición de Contraseñas

**OWASP A09:2021 – Security Logging and Monitoring Failures**  
**Archivo:** `auditoria/admin_middleware.py`

**Descripción:**
`AdminAuditMiddleware` guarda en los logs todos los campos POST del formulario,
incluyendo potencialmente campos `password`, `password1`, `password2`. Esto convierte
la tabla `LogActividad` en un repositorio de contraseñas en texto plano si un
administrador cambia su clave desde el panel Django.

**Código vulnerable:**

```python
# auditoria/admin_middleware.py
campos_modificados = {k: v for k, v in request.POST.items()
                      if not k.startswith('_') and k != 'csrfmiddlewaretoken'}
# ❌ Incluye password, password1, password2, cualquier campo sensible
```

**Corrección — auditoria/admin_middleware.py:**

```python
import logging

logger = logging.getLogger('auditoria.middleware')

# Campos que NUNCA deben aparecer en logs de auditoría
_SENSITIVE_FIELDS = frozenset([
    'password', 'password1', 'password2', 'old_password', 'new_password',
    'confirm_password', 'secret_key', 'token', 'api_key', 'clave', 'pin',
])

def _sanitize_post_data(post_dict):
    """Redacta campos sensibles antes de registrarlos en auditoría."""
    sanitized = {}
    for key, value in post_dict.items():
        if key.startswith('_') or key == 'csrfmiddlewaretoken':
            continue
        if any(sensitive in key.lower() for sensitive in _SENSITIVE_FIELDS):
            sanitized[key] = '***REDACTED***'
        else:
            sanitized[key] = str(value)[:200] if value else value
    return sanitized

# En AdminAuditMiddleware.__call__(), reemplazar la línea de campos_modificados:
campos_modificados = _sanitize_post_data(dict(request.POST))
```

---

### [HIGH-03] Path Traversal Potencial en MediaServeMiddleware

**OWASP A01:2021 – Broken Access Control**  
**Archivo:** `app/middleware.py`

**Descripción:**
El middleware usa `os.path.commonpath()` sin normalizar la ruta con `os.path.realpath()`
primero. Los symlinks dentro de `MEDIA_ROOT` pueden apuntar a archivos fuera del
directorio, y un atacante con capacidad de crear symlinks podría leer archivos del
sistema (`/etc/passwd`, claves privadas, etc.).

**Código vulnerable:**

```python
# app/middleware.py
file_path = os.path.join(settings.MEDIA_ROOT, relative_path)
# ❌ No resuelve symlinks — commonpath() puede ser burlado
if os.path.exists(file_path) and os.path.commonpath([settings.MEDIA_ROOT, file_path]) == settings.MEDIA_ROOT:
```

**Corrección — app/middleware.py:**

```python
def process_request(self, request):
    if not settings.DEBUG and request.path.startswith(settings.MEDIA_URL):
        relative_path = request.path[len(settings.MEDIA_URL):]

        # Rechazar rutas con secuencias de escape peligrosas
        if '..' in relative_path or relative_path.startswith('/'):
            raise Http404("Ruta no válida")

        # Resolver rutas reales (seguir symlinks) y verificar contención
        media_root_real = os.path.realpath(settings.MEDIA_ROOT)
        file_path_real = os.path.realpath(os.path.join(media_root_real, relative_path))

        # La ruta resuelta DEBE comenzar con MEDIA_ROOT real + separador
        if not file_path_real.startswith(media_root_real + os.sep):
            raise Http404("Acceso denegado")

        if os.path.isfile(file_path_real):
            try:
                content_type, _ = mimetypes.guess_type(file_path_real)
                content_type = content_type or 'application/octet-stream'
                with open(file_path_real, 'rb') as f:
                    response = HttpResponse(f.read(), content_type=content_type)
                response['Cache-Control'] = 'private, no-cache'
                response['X-Content-Type-Options'] = 'nosniff'
                return response
            except (IOError, OSError):
                raise Http404("Archivo no encontrado")

        raise Http404("Archivo no encontrado")
    return None
```

---

### [HIGH-04] `balances_view` Expone Datos Financieros Solo con `@login_required`

**OWASP A01:2021 – Broken Access Control**  
**Archivo:** `app/views.py`

**Descripción:**
La vista `/balances/` está protegida con `@login_required` pero sin verificación de
permiso. Un usuario con rol `Vendedor` puede navegar directamente a `/balances/` y
ver el balance financiero completo de gastos, compras y flujo de caja. Esto viola
el principio de mínimo privilegio del RBAC definido en `app/permissions.py`.

**Código vulnerable:**

```python
# app/views.py
@login_required    # ❌ Solo verifica autenticación, no autorización por rol
def balances_view(request):
    balance_service = BalanceAnalysisService()
    context = balance_service.get_full_context(request)
    return render(request, 'gastos/balances.html', context)
```

**Corrección — app/views.py:**

```python
from django.contrib.auth.decorators import login_required, permission_required

@login_required
@permission_required('gastos.view_gastos', raise_exception=True)
def balances_view(request):
    balance_service = BalanceAnalysisService()
    context = balance_service.get_full_context(request)
    return render(request, 'gastos/balances.html', context)
```

---

### [HIGH-05] `USE_TZ = False` — Timestamps de Auditoría sin Zona Horaria

**OWASP A04:2021 – Insecure Design**  
**Archivo:** `app/settings.py`

**Descripción:**
Con `USE_TZ = False`, Django almacena las fechas en hora local del servidor. Si el
servidor tiene UTC y el negocio está en `America/Mexico_City` (UTC-6/UTC-7), los
registros de `LogActividad` tendrán una diferencia de 6-7 horas. En una auditoría
fiscal ante el SAT o en un proceso legal, los logs con hora incorrecta no tienen
valor probatorio válido.

**Corrección — app/settings.py:**

```python
# Cambiar:
USE_TZ = False
# Por:
USE_TZ = True   # Django almacena en UTC, muestra en America/Mexico_City
TIME_ZONE = "America/Mexico_City"
```

> **Importante:** Requiere actualizar todos los campos `DateTimeField` existentes en la BD.
> Ejecutar: `python manage.py migrate --run-syncdb` tras hacer la migration.

---

## 🟡 HALLAZGOS MEDIOS

---

### [MED-01] Política de Contraseñas Insuficiente para Sistema Financiero

**OWASP A07:2021 – Identification and Authentication Failures**  
**Archivo:** `app/settings.py`

**Descripción:**
Los validadores actuales no tienen longitud mínima explícita (usa el default de 8 caracteres)
y no exigen complejidad (mayúsculas, dígitos, símbolos). Para un sistema con acceso a
datos financieros, NIST SP 800-63B recomienda mínimo 12 caracteres.

**Corrección — app/settings.py:**

```python
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        "OPTIONS": {"max_similarity": 0.5},  # Más estricto que el default 0.7
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},  # ✅ 12 caracteres mínimo (NIST recomendación)
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]
```

---

### [MED-02] `AdminAuditMiddleware` Silencia Todas las Excepciones

**OWASP A09:2021 – Security Logging and Monitoring Failures**  
**Archivo:** `auditoria/admin_middleware.py`

**Descripción:**
El bloque `except Exception as e: pass` hace que errores en la auditoría sean
completamente invisibles. Si la BD de logs falla (disco lleno, conexión caída),
el sistema continúa sin registrar y sin alertar al administrador.

**Código vulnerable:**

```python
# auditoria/admin_middleware.py
except Exception as e:
    pass  # ❌ Falla silenciosa — el equipo nunca sabrá que la auditoría está rota
```

**Corrección:**

```python
import logging
logger = logging.getLogger('auditoria.middleware')

except Exception:
    logger.error(
        "Error en AdminAuditMiddleware | Usuario: %s | Path: %s",
        getattr(request.user, 'username', 'anónimo'),
        request.path,
        exc_info=True,  # Incluye traceback completo
    )
    # No re-lanzar — no interrumpir la respuesta al usuario
```

---

### [MED-03] Archivos Media Expuestos con `static()` Siempre Activo en `urls.py`

**OWASP A05:2021 – Security Misconfiguration**  
**Archivo:** `app/urls.py`

**Descripción:**
La línea `urlpatterns += static(settings.MEDIA_URL, ...)` se ejecuta siempre, incluso
en producción. Esto hace que Django sirva media directamente, sobreponiéndose a la
configuración de Nginx (que debería manejar archivos estáticos de forma más eficiente y segura).

**Código vulnerable:**

```python
# app/urls.py — Siempre activo, incluso en producción
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

**Corrección:**

```python
# Solo en desarrollo — en producción, Nginx/Apache gestiona los archivos
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

---

### [MED-04] Bug de Seguridad en `RoleManager.create_roles()` — Permisos Cruzados

**OWASP A01:2021 – Broken Access Control**  
**Archivo:** `app/permissions.py`

**Descripción:**
El filtro de permisos usa `codename__in` y `content_type__app_label__in` de forma
**independiente**. Esto puede asignar permisos cruzados: si `gastos` tiene un permiso
llamado `view_ventas`, el filtro lo asignaría incorrectamente al rol `Contador`.

**Código vulnerable:**

```python
# app/permissions.py
permissions = Permission.objects.filter(
    codename__in=[p.split('.')[-1] for p in role_data['permissions']],
    content_type__app_label__in=[p.split('.')[0] for p in role_data['permissions']]
)
# ❌ Filtro OR implícito entre app_label y codename — puede cruzar permisos
```

**Corrección:**

```python
from django.db.models import Q

@classmethod
def create_roles(cls):
    for role_name, role_data in cls.ROLES.items():
        group, created = Group.objects.get_or_create(name=role_name)

        if role_data['permissions'] == ['*']:
            permissions = Permission.objects.all()
        else:
            # ✅ Filtro AND por pares (app_label, codename) — sin cruces
            perm_filter = Q()
            for perm_string in role_data['permissions']:
                app_label, codename = perm_string.rsplit('.', 1)
                perm_filter |= Q(
                    content_type__app_label=app_label,
                    codename=codename
                )
            permissions = Permission.objects.filter(perm_filter)

        group.permissions.set(permissions)
```

---

### [MED-05] `SESSION_COOKIE_AGE` No Configurado — Sesiones de 2 Semanas

**OWASP A07:2021 – Identification and Authentication Failures**  
**Archivo:** `app/settings.py`

**Descripción:**
El default de Django para `SESSION_COOKIE_AGE` es **1,209,600 segundos (2 semanas)**.
En una empresa agrícola donde varios empleados pueden compartir una terminal, una
sesión abierta durante 2 semanas representa un riesgo real de acceso no autorizado.

**Corrección — app/settings.py:**

```python
# Agregar en settings.py (fuera del bloque if not DEBUG)
SESSION_COOKIE_AGE = 60 * 60 * 8       # 8 horas — jornada laboral completa
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Sesión termina al cerrar el navegador
SESSION_SAVE_EVERY_REQUEST = True       # Reinicia el timer en cada petición activa
```

---

## 🟢 HALLAZGOS BAJOS

---

### [LOW-01] `X_FRAME_OPTIONS` Solo Activo en Producción — Sin Protección Anti-Clickjacking en Dev

**Archivo:** `app/settings.py`

**Descripción:**
La directiva `X_FRAME_OPTIONS = 'DENY'` solo se asigna dentro del bloque `if not DEBUG`.
En entornos de desarrollo y staging, las páginas admin son vulnerables a clickjacking.

**Corrección:**

```python
# Mover fuera del bloque if not DEBUG — aplicar siempre
X_FRAME_OPTIONS = 'DENY'
```

---

### [LOW-02] Log Injection via `User-Agent` no Sanitizado

**Archivo:** `auditoria/services.py`

**Descripción:**
El `User-Agent` se registra directamente sin sanitizar. Un atacante puede incluir
caracteres de nueva línea (`\n`, `\r`) para falsear entradas de log e inyectar
registros falsos en la tabla `LogActividad`.

**Corrección:**

```python
def _sanitize_for_log(value, max_length=500):
    """Elimina caracteres de control para prevenir log injection."""
    if not value:
        return ''
    sanitized = value.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    return sanitized[:max_length]

# En registrar_log():
navegador = _sanitize_for_log(request.META.get('HTTP_USER_AGENT', ''))
```

---

### [LOW-03] `Content-Disposition` en Exportaciones Excel sin Sanitizar

**Archivo:** `app/services/utils.py`

**Descripción:**
El `filename_prefix` en la respuesta Excel no está sanitizado. Si se construye
dinámicamente desde parámetros de usuario, un atacante puede inyectar caracteres
especiales en el nombre del archivo.

**Corrección:**

```python
import re

@staticmethod
def create_excel_response(workbook, filename_prefix="reporte"):
    # Sanitizar el prefijo — solo alfanuméricos, guiones y guiones bajos
    safe_prefix = re.sub(r'[^\w\-]', '_', filename_prefix)[:50]
    current_date = datetime.now().strftime("%Y%m%d")
    filename = f"{safe_prefix}_{current_date}.xlsx"

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f"attachment; filename=\"{filename}\""
    workbook.save(response)
    return response
```

---

### [LOW-04] `Anticipo.monto` Acepta Valores de Cero o Negativos

**Archivo:** `ventas/models.py`

**Descripción:**
El campo `monto` en `Anticipo` usa `MoneyField` pero sin `MinValueValidator`.
Un usuario puede registrar anticipos de $0.00 o montos negativos que corrompan
el cálculo de crédito disponible del cliente.

**Corrección:**

```python
from django.core.validators import MinValueValidator
from decimal import Decimal

class Anticipo(models.Model):
    monto = MoneyField(
        max_digits=10,
        decimal_places=2,
        default_currency='MXN',
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Monto del anticipo (mínimo $0.01)"
    )
```

---

## Plan de Remediación Priorizado

```
SEMANA 1 — CRÍTICOS (resolver antes del próximo acceso en producción):
│
├── CRIT-01  Agregar @login_required + @permission_required a vistas de ventas
│            Archivos: ventas/views.py
│
├── CRIT-02  Refactorizar _get_real_ip() con validación de proxies confiables
│            Archivos: auditoria/services.py
│
└── CRIT-03  Migrar Ventas.cantidad de CharField → DecimalField
             Archivos: ventas/models.py + nueva migration

SEMANA 2 — ALTOS:
│
├── HIGH-01  SESSION_COOKIE_SECURE y CSRF_COOKIE_SECURE → True por defecto en prod
│            Archivos: app/settings.py
│
├── HIGH-02  Sanitizar campos POST sensibles en AdminAuditMiddleware
│            Archivos: auditoria/admin_middleware.py
│
├── HIGH-03  Refactorizar process_request() con os.path.realpath() en middleware
│            Archivos: app/middleware.py
│
├── HIGH-04  Agregar @permission_required('gastos.view_gastos') a balances_view
│            Archivos: app/views.py
│
└── HIGH-05  Habilitar USE_TZ = True + planificar migration de DateTimeField
             Archivos: app/settings.py

SEMANA 3 — MEDIOS:
│
├── MED-01   min_length = 12 en MinimumLengthValidator
├── MED-02   Reemplazar except: pass con logging.error() en AdminAuditMiddleware
├── MED-03   Condicionar static() a if settings.DEBUG en urls.py
├── MED-04   Corregir filtro de permisos en RoleManager.create_roles()
└── MED-05   SESSION_COOKIE_AGE = 8 horas

MEJORA CONTINUA — BAJOS:
│
├── LOW-01   Mover X_FRAME_OPTIONS fuera del bloque if not DEBUG
├── LOW-02   Sanitizar User-Agent con _sanitize_for_log()
├── LOW-03   Sanitizar Content-Disposition con re.sub() en create_excel_response()
└── LOW-04   MinValueValidator(0.01) en Anticipo.monto
```

---

## Respuesta a las Preguntas del Cliente

### ¿Cómo tiene el usuario el control de la seguridad en el sistema?

**A. Control de Acceso Basado en Roles (RBAC)**
El sistema tiene `RoleManager` en `app/permissions.py` con 5 roles predefinidos:
`Administrador`, `Gerente`, `Contador`, `Vendedor` y `Operador`. Cada rol tiene
permisos granulares sobre modelos específicos (ej: el `Vendedor` puede crear ventas
pero no eliminarlas ni ver gastos). **Acción pendiente:** Corregir bug de filtro [MED-04]
para que los permisos se asignen correctamente.

**B. Trazabilidad y Auditoría**
El sistema tiene dos capas de auditoría propias:

- `LogActividad` (modelo en `auditoria/`) registra login, logout, creación, edición y eliminación.
- `AuthAuditMiddleware` captura automáticamente login/logout.
- `AdminAuditMiddleware` registra cambios en el panel Admin.
  **Acción pendiente:** Reforzar IP logging [CRIT-02] y sanitizar logs [HIGH-02, LOW-02].

**C. Validación y Blindaje**
Los modelos usan `DecimalField` con `MinValueValidator` en la mayoría de campos
monetarios, y `MoneyField` para valores en moneda. `VentasAdminForm` valida que
ventas a crédito tengan término definido. **Punto crítico:** El campo `cantidad`
en `Ventas` es `CharField` [CRIT-03] — requiere migration urgente.

**D. Respaldos y Disponibilidad**
El sistema usa PostgreSQL/MySQL con contraseñas en variables de entorno (`.env`).
La infraestructura con Docker (`docker-compose.yml`) facilita respaldos automáticos.
Se recomienda configurar `pg_dump` o `mysqldump` en un `cron` diario hacia almacenamiento
externo (S3, Google Cloud Storage).

---

_Auditoría completada el 10 de Abril de 2026. Análisis estático (SAST) del código fuente._  
_Se recomienda complementar con pruebas dinámicas (DAST) y penetration testing antes del próximo release._

# Informe de Diagnóstico de Seguridad

## Aplicación: Agrícola de la Costa San Luis — Sistema Administrativo

**Framework**: Django 5.0.6 · **Base de datos**: MySQL 8.0 · **Caché**: Redis 7.2  
**Fecha de análisis**: 2 de abril de 2026  
**Analista**: GitHub Copilot — Análisis Estático de Código

---

## Resumen Ejecutivo

La aplicación tiene una **base de seguridad sólida** con Django como framework, manejo correcto de
variables de entorno y un sistema de auditoría robusto. Sin embargo, se identificaron
**2 hallazgos críticos** que requieren atención inmediata: endpoints del módulo `ventas` sin
autenticación y datos financieros sensibles sin cifrar en reposo. La puntuación general estimada
es **3.5 / 5** (nivel medio-alto, con brechas claras).

---

## Tabla de Puntuación OWASP Top 10

| #   | Categoría OWASP                                    | Nivel            | Puntuación | Estado                                                   |
| --- | -------------------------------------------------- | ---------------- | ---------- | -------------------------------------------------------- |
| A01 | Control de Acceso Deficiente                       | 🔴 **Crítico**   | 2/5        | Módulo ventas sin @login_required                        |
| A02 | Fallas Criptográficas                              | 🟠 **Medio**     | 2/5        | Campos sensibles sin cifrar en reposo                    |
| A03 | Inyección                                          | 🟢 **Bueno**     | 5/5        | ORM usado correctamente, sin SQL raw                     |
| A04 | Diseño Inseguro                                    | 🟡 **Aceptable** | 3/5        | Sin rate limiting, productorForm expone todos los campos |
| A05 | Configuración de Seguridad Deficiente              | 🟡 **Aceptable** | 3/5        | SESSION_COOKIE_SECURE no forzado                         |
| A06 | Componentes Vulnerables y Desactualizados          | 🟡 **Aceptable** | 3/5        | django-money, langchain requieren revisión               |
| A07 | Fallas de Autenticación e Identificación           | 🟡 **Aceptable** | 4/5        | RBAC implementado, contraseñas validadas                 |
| A08 | Fallos de Integridad de Software y Datos           | 🟡 **Aceptable** | 3/5        | Validación de archivos PDF incompleta                    |
| A09 | Registro y Monitoreo de Seguridad Deficientes      | 🟢 **Bueno**     | 5/5        | Auditoría completa implementada                          |
| A10 | Falsificación de Solicitudes del Lado del Servidor | 🟢 **Bueno**     | 4/5        | CSRF activo, orígenes configurados                       |

**Puntuación Total Estimada: 3.5 / 5.0**

---

## Hallazgos Críticos (P1 — Acción Inmediata)

### 🔴 C-01 — Módulo Ventas sin Autenticación Requerida

**Severidad**: Crítica  
**Categoría OWASP**: A01 — Control de Acceso Deficiente  
**Archivos afectados**: `ventas/views.py`, `ventas/urls.py`

**Descripción**:  
Las cinco vistas del módulo de ventas (`lista_anticipos`, `crear_anticipo`, `detalle_venta`,
`ventas_balances`, `reporte_cobranza_global`) **no tienen el decorador `@login_required`**.
Cualquier usuario no autenticado puede acceder a datos financieros de clientes, anticipos,
reportes de cobranza y balances de ventas.

**Evidencia**:

```python
# ventas/views.py — SIN protección
def lista_anticipos(request):
    anticipos = Anticipo.objects.all()  # Expone todos los anticipos
    return render(request, 'lista_anticipos.html', {'anticipos': anticipos})

def ventas_balances(request):
    # Código de ~400 líneas con datos financieros confidenciales
    # SIN @login_required arriba
```

**Impacto**:

- Exposición de información de crédito de clientes (`limite_credito`, `calificacion_credito`)
- Exposición de montos de ventas y anticipos pagados/pendientes
- Exposición del reporte de cuentas por cobrar sin autenticación

**Remediación**:

```python
# ventas/views.py — CORRECCIÓN
from django.contrib.auth.decorators import login_required

@login_required
def lista_anticipos(request):
    ...

@login_required
def crear_anticipo(request):
    ...

@login_required
def ventas_balances(request):
    ...

@login_required
def reporte_cobranza_global(request):
    ...
```

---

### 🔴 C-02 — Datos Financieros Sensibles sin Cifrar en Reposo

**Severidad**: Crítica  
**Categoría OWASP**: A02 — Fallas Criptográficas  
**Archivos afectados**: `gastos/models.py`, `catalogo/models.py`, `ventas/models.py`

**Descripción**:  
Los siguientes campos almacenan información financiera y personal identificable (PII) en
texto plano en la base de datos, sin ningún cifrado a nivel de campo:

| Modelo      | Campo                 | Tipo de dato                     | App      |
| ----------- | --------------------- | -------------------------------- | -------- |
| `Cuenta`    | `numero_cuenta`       | Número de cuenta bancaria        | gastos   |
| `Cuenta`    | `clabe`               | CLABE interbancaria (18 dígitos) | gastos   |
| `Cuenta`    | `rfc`                 | RFC (dato fiscal — PII)          | gastos   |
| `Cuenta`    | `numero_cliente`      | Número de cliente bancario       | gastos   |
| `Productor` | `num_cuenta`          | Número de cuenta                 | catalogo |
| `Productor` | `clabe_interbancaria` | CLABE interbancaria              | catalogo |
| `Cliente`   | `correo`              | Correo electrónico — PII         | ventas   |
| `Cliente`   | `limite_credito`      | Límite de crédito                | ventas   |

**Remediación**:  
Instalar y usar `django-encrypted-model-fields` para cifrar campos sensibles:

```bash
pip install django-encrypted-model-fields
```

```python
from encrypted_model_fields.fields import EncryptedCharField

class Cuenta(models.Model):
    numero_cuenta = EncryptedCharField(max_length=25)
    clabe = EncryptedCharField(max_length=25, blank=True, null=True)
    rfc = EncryptedCharField(max_length=15, blank=True, null=True)
```

---

## Hallazgos Medios (P2 — Corregir en el próximo sprint)

### 🟠 M-01 — Cookies de Sesión y CSRF No Seguras en Producción

**Severidad**: Media  
**Categoría OWASP**: A05 — Configuración de Seguridad Deficiente  
**Archivo**: `app/settings.py`

**Descripción**:  
Los valores por defecto de `SESSION_COOKIE_SECURE` y `CSRF_COOKIE_SECURE` son `False`.
Aunque están controlados por variables de entorno, si estas no se configuran explícitamente
en producción, las cookies se enviarán sobre HTTP, permitiendo ataques de
interceptación (Man-in-the-Middle).

**Evidencia**:

```python
# app/settings.py
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() in ["true", "1"]
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "False").lower() in ["true", "1"]
```

**Remediación**:  
Cambiar el valor por defecto a `True` cuando `DEBUG=False`:

```python
if not DEBUG:
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "True").lower() in ["true", "1"]
    CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "True").lower() in ["true", "1"]
```

---

### 🟠 M-02 — Módulo Catálogo sin Autenticación (Endpoints Públicos)

**Severidad**: Media  
**Categoría OWASP**: A01 — Control de Acceso Deficiente  
**Archivos**: `catalogo/views.py`, `catalogo/urls.py`

**Descripción**:  
Las siguientes vistas de catálogo son accesibles públicamente sin autenticación:

- `GET /catalogo/` — Lista productores y productos
- `GET /` (index) — Página principal
- `POST insertar_productor()` — Permite crear productores sin auth

La vista `insertar_productor` es especialmente crítica ya que permite modificar datos
(crear registros) en la base de datos sin ninguna autenticación.

**Remediación**:  
Evaluar si el catálogo debe ser público o requiere autenticación. Si es privado:

```python
@login_required
def catalogo_list(request):
    ...

@login_required
def insertar_productor(request):
    ...
```

---

### 🟠 M-03 — `ProductorForm` con `fields = '__all__'`

**Severidad**: Media  
**Categoría OWASP**: A04 — Diseño Inseguro  
**Archivo**: `catalogo/forms.py`

**Descripción**:  
El formulario `ProductorForm` usa `fields = '__all__'`, lo que expone todos los campos del
modelo incluidos los que podrían ser manipulados maliciosamente (como `fecha_creacion`,
claves interbancarias, etc.).

**Remediación**:

```python
class ProductorForm(forms.ModelForm):
    class Meta:
        model = Productor
        fields = ['nombre_completo', 'telefono', 'correo', 'nacimiento',
                  'id_sucursal', 'nacionalidad', 'imagen']
        # Excluir: num_cuenta, clabe_interbancaria, fecha_creacion
```

---

### 🟠 M-04 — Sin Rate Limiting en Endpoints Críticos

**Severidad**: Media  
**Categoría OWASP**: A04 — Diseño Inseguro  
**Archivos**: `app/views.py`, `gastos/views.py`

**Descripción**:  
Los endpoints de procesamiento de IA (`/ingresar-factura/`) y conversión de moneda
(`/api/currency-conversion/`) no tienen rate limiting. Esto permite:

1. Abusar de la API de Google Gemini (costos no controlados)
2. Ataques de fuerza bruta contra endpoints de autenticación
3. Ataques de denegación de servicio (DoS) a nivel de aplicación

**Remediación**:

```bash
pip install django-ratelimit
```

```python
# app/views.py
from django_ratelimit.decorators import ratelimit

@ratelimit(key='user', rate='10/m', block=True)
@login_required
def currency_conversion_api(request):
    ...

# gastos/views.py
@ratelimit(key='user', rate='5/m', block=True)
@login_required
def ingresar_gasto_factura(request):
    ...
```

---

### 🟠 M-05 — Validación de Archivos PDF Insuficiente

**Severidad**: Media  
**Categoría OWASP**: A08 — Fallos de Integridad de Software y Datos  
**Archivo**: `gastos/views.py`, `gastos/forms.py`

**Descripción**:  
El endpoint `/ingresar-factura/` acepta archivos y los procesa con Google Gemini AI y PyPDF.
No se valida suficientemente:

1. El tipo MIME real del archivo (solo el nombre/extensión)
2. El tamaño máximo por archivo individual (antes de escribir al disco)
3. Que el contenido sea realmente un PDF válido (magic bytes)

Un archivo malicioso con extensión `.pdf` pero contenido ejecutable podría pasar los filtros.

**Remediación**:

```python
# gastos/forms.py
import magic  # pip install python-magic-bin

def clean_documento_pdf(self):
    archivo = self.cleaned_data.get('documento_pdf')
    if archivo:
        if archivo.size > 10 * 1024 * 1024:  # 10 MB máx
            raise forms.ValidationError("El archivo no puede superar 10 MB.")
        # Verificar magic bytes (firma real del archivo)
        header = archivo.read(8)
        archivo.seek(0)
        if not header.startswith(b'%PDF'):
            raise forms.ValidationError("El archivo no es un PDF válido.")
    return archivo
```

---

## Hallazgos Bajos (P3 — Deuda técnica a gestionar)

### 🟡 B-01 — `SECURE_SSL_REDIRECT` Desactivado por Defecto

**Archivo**: `app/settings.py`  
La redirección HTTP → HTTPS no ocurre a nivel de Django. Actualmente se delega a Nginx,
lo cual es correcto, pero debe documentarse como política explícita.

### 🟡 B-02 — Session Timeout No Configurado Explícitamente

Django usa 2 semanas como tiempo de sesión por defecto (`SESSION_COOKIE_AGE = 1209600`).
Para una aplicación financiera, se recomienda reducirlo a 8 horas:

```python
SESSION_COOKIE_AGE = 28800  # 8 horas en segundos
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
```

### 🟡 B-03 — Dependencias de IA sin Versión Mínima de Seguridad Garantizada

`langchain==0.2.17`, `langchain-community==0.2.19` y `google-generativeai==0.7.2` son
versiones fijas antiguas. Se recomienda ejecutar `pip audit` o `safety check` periódicamente
para detectar CVEs conocidos.

### 🟡 B-04 — `django-cors-headers` Instalado pero No Configurado en settings.py

`django-cors-headers` aparece en `requirements.txt` pero no está visible en `INSTALLED_APPS`
ni en `MIDDLEWARE`. Si está activo con `CORS_ALLOW_ALL_ORIGINS = True`, permitiría
solicitudes cross-origin desde cualquier dominio.

---

## Aspectos de Seguridad Confirmados (Fortalezas)

| Aspecto                             | Descripción                                                       | Archivo              |
| ----------------------------------- | ----------------------------------------------------------------- | -------------------- |
| ✅ Secretos en variables de entorno | `SECRET_KEY`, `DB_PASSWORD`, `API_KEYS` via `.env`                | `app/settings.py`    |
| ✅ RBAC con 5 roles                 | Administrador, Gerente, Contador, Vendedor, Operador              | `app/permissions.py` |
| ✅ Sistema de auditoría completo    | Login, logout, CRUD con IP, User-Agent, timestamp                 | `auditoria/`         |
| ✅ HSTS configurado (1 año)         | `SECURE_HSTS_SECONDS = 31536000` con preload y subdomains         | `app/settings.py`    |
| ✅ X-Frame-Options: DENY            | Anti-clickjacking activo                                          | `app/settings.py`    |
| ✅ CSRF activo                      | `CsrfViewMiddleware` en posición correcta en middleware stack     | `app/settings.py`    |
| ✅ ORM exclusivo                    | Sin consultas SQL raw detectadas — protegido contra SQL Injection | Todo el código       |
| ✅ Docker non-root user             | Contenedor corre como `appuser`, no como `root`                   | `Dockerfile`         |
| ✅ Debug desactivable por env       | `DEBUG = os.getenv("DEBUG", "False")`                             | `app/settings.py`    |
| ✅ Passwordvalidators activos       | Similitud, longitud mínima, contraseñas comunes                   | `app/settings.py`    |
| ✅ Nginx con security headers       | X-Frame-Options, X-XSS-Protection, CSP, cache headers             | `nginx.conf`         |
| ✅ Redis con contraseña             | `requirepass` configurado en docker-compose                       | `docker-compose.yml` |
| ✅ Path traversal protegido         | `os.path.commonpath()` en media middleware                        | `app/middleware.py`  |

---

## Plan de Remediación Priorizado

### P1 — Inmediato (antes del próximo release)

| ID   | Acción                                                                                  | Esfuerzo | Impacto |
| ---- | --------------------------------------------------------------------------------------- | -------- | ------- |
| C-01 | Agregar `@login_required` a todas las vistas de `ventas/views.py`                       | 30 min   | Crítico |
| C-02 | Evaluar cifrado de campos con `django-encrypted-model-fields`                           | 2-4 h    | Crítico |
| M-01 | Cambiar defaults de `SESSION_COOKIE_SECURE` y `CSRF_COOKIE_SECURE` a `True` en no-DEBUG | 15 min   | Alto    |

### P2 — Próximo Sprint

| ID   | Acción                                                                 | Esfuerzo | Impacto |
| ---- | ---------------------------------------------------------------------- | -------- | ------- |
| M-02 | Decidir política de autenticación para módulo catálogo                 | 1 h      | Alto    |
| M-03 | Reemplazar `fields = '__all__'` en `ProductorForm` con lista explícita | 30 min   | Medio   |
| M-04 | Implementar rate limiting con `django-ratelimit`                       | 2 h      | Medio   |
| M-05 | Agregar validación de magic bytes en upload de PDFs                    | 2 h      | Medio   |

### P3 — Deuda Técnica

| ID   | Acción                                            | Esfuerzo | Impacto |
| ---- | ------------------------------------------------- | -------- | ------- |
| B-01 | Documentar política de SSL/HTTPS                  | 30 min   | Bajo    |
| B-02 | Configurar `SESSION_COOKIE_AGE = 28800` (8 horas) | 15 min   | Medio   |
| B-03 | Agregar `pip audit` en pipeline CI/CD             | 1 h      | Medio   |
| B-04 | Auditar configuración de `django-cors-headers`    | 1 h      | Medio   |

---

## Metodología

Este análisis se realizó mediante **revisión estática de código** (SAST manual) revisando:

- Configuración de Django (`settings.py`, middleware stack)
- Controladores y vistas (decoradores de autenticación y permisos)
- Modelos (tipos de datos, campos sensibles)
- Formularios (validación, campos expuestos)
- Infraestructura (Docker, Nginx, Redis)
- Referencias cruzadas con el [OWASP Top 10 2021](https://owasp.org/www-project-top-ten/)

No se realizaron pruebas de penetración activas ni análisis dinámico (DAST).

---

_Generado el 2 de abril de 2026 — Para uso interno. Contiene información sensible sobre la arquitectura de seguridad del sistema._
