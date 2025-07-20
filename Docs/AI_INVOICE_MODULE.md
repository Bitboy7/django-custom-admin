# Módulo de Reconocimiento de Documentos con IA

## Descripción

Este módulo permite el reconocimiento automático de facturas y estados de cuenta utilizando LangChain y la API de Google Gemini para extraer información y registrar gastos automáticamente en el sistema.

## Características Principales

### 🔍 Reconocimiento de Documentos

- **Facturas individuales**: Extrae información de facturas PDF para crear un gasto único
- **Estados de cuenta**: Analiza estados de cuenta bancarios y extrae múltiples transacciones
- **Detección automática**: Identifica automáticamente el tipo de documento

### 🤖 Inteligencia Artificial

- **Motor**: LangChain + Google Gemini 2.0 Flash Experimental
- **Procesamiento**: Análisis de contenido PDF con extracción estructurada
- **Modelos Pydantic**: Validación de datos extraídos con esquemas estructurados

### 🎨 Interfaz de Usuario

- **Diseño moderno**: Interfaz con Tailwind CSS y componentes responsivos
- **Proceso guiado**: Flujo paso a paso para confirmación de datos
- **Gestión por lotes**: Selección y edición de múltiples transacciones

## Estructura del Módulo

### Servicios

```
gastos/services/invoice_recognition_service.py
├── GastoFactura (Pydantic Model)
├── MovimientoEstadoCuenta (Pydantic Model)
├── EstadoCuentaCompleto (Pydantic Model)
├── reconocer_factura_pdf()
├── reconocer_estado_cuenta_pdf()
└── detectar_tipo_documento()
```

### Formularios

```
gastos/forms.py
└── FacturaUploadForm
    ├── documento_pdf (FileField)
    └── tipo_documento (ChoiceField)
```

### Vistas

```
gastos/views.py
├── ingresar_gasto_factura()      # Manejo de subida y procesamiento
└── guardar_gastos_estado_cuenta() # Guardado por lotes
```

### Templates

```
templates/gastos/
├── ingresar_gasto_factura.html    # Formulario de subida
├── confirmar_gasto_factura.html   # Confirmación de factura individual
├── confirmar_estado_cuenta.html   # Tabla de transacciones multiple
└── resultado_estado_cuenta.html   # Resultados del procesamiento
```

### Template Tags

```
gastos/templatetags/gastos_tags.py
├── get_cat_gastos()  # Obtiene categorías de gastos
└── get_cuentas()     # Obtiene cuentas bancarias
```

## Modelos de Datos

### GastoFactura (Pydantic)

```python
{
    "fecha": "2024-01-15",
    "monto": 150.50,
    "proveedor": "Proveedor XYZ",
    "descripcion": "Servicios de consultoría",
    "categoria_sugerida": "Servicios profesionales"
}
```

### EstadoCuentaCompleto (Pydantic)

```python
{
    "banco": "Banco Nacional",
    "numero_cuenta": "****1234",
    "periodo": "Enero 2024",
    "movimientos": [
        {
            "fecha": "2024-01-15",
            "descripcion": "Pago servicios",
            "monto": -250.00,
            "saldo": 1500.00
        }
    ]
}
```

## Configuración Requerida

### Variables de Entorno

```python
# En settings.py o .env
GOOGLE_API_KEY = "tu_clave_de_api_de_google"
```

### Dependencias

```python
# pyproject.toml
langchain = "^0.2.0"
langchain-google-genai = "^1.0.10"
pypdf = "^4.0.0"
pydantic = "^2.0.0"
```

### Unfold Navigation

```python
# settings.py
UNFOLD = {
    "SIDEBAR": {
        "navigation": [
            {
                "title": "Gestión de Gastos",
                "items": [
                    {
                        "title": "Subir Factura (IA)",
                        "icon": "upload",
                        "link": reverse_lazy("gastos:ingresar_gasto_factura"),
                    },
                ]
            }
        ]
    }
}
```

## URLs

```python
# gastos/urls.py
urlpatterns = [
    path('ingresar-factura/', views.ingresar_gasto_factura, name='ingresar_gasto_factura'),
    path('guardar-estado-cuenta/', views.guardar_gastos_estado_cuenta, name='guardar_gastos_estado_cuenta'),
]
```

## Flujo de Trabajo

### Para Facturas

1. **Subida**: Usuario sube archivo PDF
2. **Detección**: Sistema identifica que es una factura
3. **Procesamiento**: IA extrae datos (fecha, monto, proveedor, etc.)
4. **Confirmación**: Usuario revisa y confirma la información
5. **Guardado**: Se crea el registro de gasto en la base de datos

### Para Estados de Cuenta

1. **Subida**: Usuario sube archivo PDF del estado de cuenta
2. **Detección**: Sistema identifica que es un estado de cuenta
3. **Procesamiento**: IA extrae múltiples transacciones
4. **Selección**: Usuario selecciona qué transacciones registrar
5. **Edición**: Usuario puede editar categorías y cuentas
6. **Guardado**: Se crean múltiples registros de gastos

## Características Técnicas

### Seguridad

- Validación de archivos PDF
- Sanitización de datos extraídos
- Autenticación requerida (login_required)

### Performance

- Procesamiento asíncrono opcional
- Validación de datos con Pydantic
- Manejo de errores robusto

### UX/UI

- Interfaz responsiva con Tailwind CSS
- Feedback visual con iconos y colores
- Formularios intuitivos con ayuda contextual
- Gestión de estados (loading, success, error)

## Extensibilidad

El módulo está diseñado para ser fácilmente extensible:

1. **Nuevos tipos de documento**: Agregar modelos Pydantic y detectores
2. **Otras APIs de IA**: Cambiar el proveedor en el servicio
3. **Campos adicionales**: Extender los modelos Pydantic
4. **Validaciones custom**: Implementar en los formularios Django

## Mantenimiento

### Logs

- Los errores se registran en `logs/app.log`
- Seguimiento de procesamiento de documentos

### Monitoreo

- Estadísticas de uso en templates
- Tracking de errores y éxitos

### Actualizaciones

- Versiones de LangChain gestionadas en pyproject.toml
- API de Google Gemini con versionado
