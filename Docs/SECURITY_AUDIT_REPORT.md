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
