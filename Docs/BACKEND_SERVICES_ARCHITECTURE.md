# Arquitectura de Servicios Backend Modulares

## 📋 Resumen

Este documento describe la arquitectura modular de servicios backend implementada para reutilizar código común entre diferentes módulos de reportes (gastos, compras, ventas, etc.).

## 🎯 Objetivo

Crear una arquitectura escalable que permita:

- **Reutilizar código** entre módulos similares
- **Reducir duplicación** de lógica de filtrado, agregación y estadísticas
- **Facilitar mantenimiento** centralizando funcionalidad común
- **Acelerar desarrollo** de nuevos módulos de reportes

## 📊 Comparación: Antes vs Después

### Antes (Enfoque Monolítico)

```
balance_service.py (316 líneas)
├── get_filter_data() - Lógica específica
├── build_filters() - Validación manual de parámetros
├── get_balances_by_period() - Agregación específica
├── calculate_accumulated() - Lógica de acumulados
├── calculate_statistics() - Cálculos estadísticos
└── process_request_parameters() - Procesamiento manual

compras_service.py (estimado 300+ líneas) ❌ NO EXISTE
├── [Duplicaría 80% del código de balance_service.py]
└── [Solo 20% sería específico de compras]

ventas_service.py (estimado 300+ líneas) ❌ NO EXISTE
├── [Duplicaría 80% del código de balance_service.py]
└── [Solo 20% sería específico de ventas]
```

**Problemas:**

- ❌ Duplicación masiva de código
- ❌ Mantenimiento multiplicado (bugs en 3+ lugares)
- ❌ Desarrollo lento de nuevos módulos
- ❌ Inconsistencias entre módulos

### Después (Enfoque Modular)

```
app/services/
├── filter_utils.py (250 líneas) ✅ REUTILIZABLE
│   ├── FilterBuilder - Construcción de filtros
│   └── FilterOptionsProvider - Opciones de UI
│
├── period_utils.py (300 líneas) ✅ REUTILIZABLE
│   ├── PeriodAggregator - Agregación temporal
│   ├── StatisticsCalculator - Estadísticas
│   ├── AccumulatedCalculator - Acumulados
│   └── PeriodFormatter - Formateo
│
├── base_report_service.py (350 líneas) ✅ REUTILIZABLE
│   ├── BaseReportService - Clase base abstracta
│   └── BaseReportServiceWithCategories - Con categorías
│
├── balance_service.py (~180 líneas) ✅ 43% REDUCCIÓN
│   └── Solo código específico de Gastos
│
├── compras_service.py (~50 líneas) ✅ NUEVO
│   └── Solo código específico de Compras
│
└── ventas_service.py (~80 líneas) ✅ NUEVO
    └── Solo código específico de Ventas
```

**Beneficios:**

- ✅ Código reutilizable centralizado
- ✅ Un solo lugar para arreglar bugs
- ✅ Nuevos módulos en ~50-80 líneas
- ✅ Consistencia garantizada

## 🏗️ Arquitectura de Capas

```
┌─────────────────────────────────────────────────┐
│             CAPA DE VISTAS (views.py)           │
│  - Maneja requests HTTP                         │
│  - Renderiza templates                          │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│        CAPA DE SERVICIOS ESPECÍFICOS            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │ Balance     │  │ Compras     │  │ Ventas  │ │
│  │ Service     │  │ Service     │  │ Service │ │
│  │ (Gastos)    │  │             │  │         │ │
│  └──────┬──────┘  └──────┬──────┘  └────┬────┘ │
│         │                │                │      │
│         └────────────────┴────────────────┘      │
│                          │                       │
└──────────────────────────┼───────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────┐
│         CAPA DE SERVICIOS BASE                  │
│  ┌──────────────────────────────────────────┐   │
│  │  BaseReportService (Abstracta)           │   │
│  │  - get_model() ← abstracto               │   │
│  │  - get_date_field() ← abstracto          │   │
│  │  - get_amount_field() ← abstracto        │   │
│  │  - get_group_fields() ← abstracto        │   │
│  │  + get_filter_data() ← implementado      │   │
│  │  + build_filters() ← implementado        │   │
│  │  + get_balances_by_period() ← impl.      │   │
│  │  + calculate_accumulated() ← impl.       │   │
│  │  + calculate_statistics() ← impl.        │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │  BaseReportServiceWithCategories         │   │
│  │  Extiende: BaseReportService             │   │
│  │  + get_category_field() ← abstracto      │   │
│  │  + get_statistics_by_category() ← impl.  │   │
│  └──────────────────────────────────────────┘   │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│           CAPA DE UTILIDADES                    │
│  ┌────────────────┐  ┌─────────────────────┐   │
│  │ FilterBuilder  │  │ PeriodAggregator    │   │
│  │ - validate_*() │  │ - aggregate_by_*()  │   │
│  │ - build_*()    │  │ - get_truncator()   │   │
│  └────────────────┘  └─────────────────────┘   │
│  ┌────────────────┐  ┌─────────────────────┐   │
│  │ Statistics     │  │ Accumulated         │   │
│  │ Calculator     │  │ Calculator          │   │
│  └────────────────┘  └─────────────────────┘   │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│              CAPA DE DATOS (ORM)                │
│  - Modelos Django (Gastos, Compras, Ventas)    │
│  - Consultas a PostgreSQL                      │
└─────────────────────────────────────────────────┘
```

## 📦 Componentes Principales

### 1. filter_utils.py

Proporciona utilidades para construcción y validación de filtros.

**Clases:**

- `FilterBuilder`: Construye y valida filtros de consulta
- `FilterOptionsProvider`: Obtiene opciones para dropdowns de UI

**Funciones principales:**

```python
# Validación
FilterBuilder.validate_year(year, default=None)
FilterBuilder.validate_month(month)
FilterBuilder.validate_id(value)

# Construcción de filtros
FilterBuilder.build_standard_filters(
    year=None,
    month=None,
    cuenta_id=None,
    sucursal_id=None,
    # ... más parámetros
)

# Extracción desde request
FilterBuilder.extract_filters_from_request(request, filter_fields=None)

# Opciones para UI
FilterOptionsProvider.get_filter_options(
    model,
    include_cuentas=True,
    include_sucursales=True,
    # ... más opciones
)
```

### 2. period_utils.py

Proporciona utilidades para agregación temporal y estadísticas.

**Clases:**

- `PeriodAggregator`: Agrupa datos por período (diario, semanal, mensual)
- `StatisticsCalculator`: Calcula estadísticas (sum, avg, max, min, mediana)
- `AccumulatedCalculator`: Calcula valores acumulados y porcentajes
- `PeriodFormatter`: Formatea fechas según el período

**Funciones principales:**

```python
# Agregación por período
PeriodAggregator.aggregate_by_period(
    queryset,
    periodo='mensual',
    group_fields=['categoria', 'sucursal'],
    sum_field='monto',
    annotation_name='total'
)

# Estadísticas
StatisticsCalculator.calculate_extended_stats(queryset, field='monto')
# Retorna: {total, promedio, maximo, minimo, cantidad, mediana}

# Acumulados
AccumulatedCalculator.calculate_accumulated(
    data,
    value_field='total',
    accumulated_field='acumulado'
)

# Porcentajes
AccumulatedCalculator.calculate_percentage_of_total(
    data,
    value_field='total',
    percentage_field='porcentaje'
)

# Formateo
PeriodFormatter.format_period_display('mensual', date_value)
# Retorna: "Enero 2024"
```

### 3. base_report_service.py

Define las clases base abstractas para servicios de reporte.

**Clases:**

#### `BaseReportService` (Abstracta)

Clase base para todos los servicios de reporte.

**Métodos abstractos (DEBEN implementarse):**

```python
def get_model(self):
    """Retorna el modelo Django"""
    pass

def get_date_field(self) -> str:
    """Retorna el nombre del campo de fecha"""
    pass

def get_amount_field(self) -> str:
    """Retorna el nombre del campo de monto"""
    pass

def get_group_fields(self, periodo: str) -> List[str]:
    """Retorna campos de agrupación según período"""
    pass
```

**Métodos implementados (heredables):**

```python
# Filtros
service.get_filter_data()
service.build_filters(**kwargs)
service.extract_filters_from_request(request)

# Agregación
service.get_balances_by_period(filters, periodo)

# Estadísticas
service.calculate_statistics(filters)
service.get_grouped_statistics(filters, group_field)

# Acumulados
service.calculate_accumulated(balances)
service.calculate_percentage_distribution(balances)

# Formateo
service.format_period(periodo, date_value)
```

#### `BaseReportServiceWithCategories`

Extiende `BaseReportService` para entidades con categorías.

**Método abstracto adicional:**

```python
def get_category_field(self) -> str:
    """Retorna el nombre del campo de categoría"""
    pass
```

**Métodos adicionales:**

```python
service.get_statistics_by_category(filters)
```

## 🔧 Uso: Crear Nuevo Servicio

### Ejemplo 1: Servicio Simple (Sin Categorías)

```python
from app.services.base_report_service import BaseReportService

class MiNuevoService(BaseReportService):
    """Servicio para mi nueva entidad"""

    # 1. Implementar métodos abstractos (OBLIGATORIO)
    def get_model(self):
        from mi_app.models import MiModelo
        return MiModelo

    def get_date_field(self) -> str:
        return 'fecha'

    def get_amount_field(self) -> str:
        return 'monto'

    def get_group_fields(self, periodo: str):
        base = ['campo1', 'campo2']
        if periodo == 'diario':
            base.append('fecha')
        return base

    # 2. Personalizar si es necesario (OPCIONAL)
    def get_filter_fields(self):
        """Añadir campos de filtro específicos"""
        fields = super().get_filter_fields()
        fields.append('mi_campo_especial_id')
        return fields

    # 3. Añadir métodos personalizados (OPCIONAL)
    def mi_metodo_especial(self, filters):
        """Lógica específica de mi módulo"""
        return self.get_grouped_statistics(
            filters,
            'mi_campo_especial'
        )
```

### Ejemplo 2: Servicio con Categorías

```python
from app.services.base_report_service import BaseReportServiceWithCategories

class ServicioConCategorias(BaseReportServiceWithCategories):
    """Servicio para entidad con categorías"""

    # Implementar métodos abstractos
    def get_model(self):
        from mi_app.models import MiModelo
        return MiModelo

    def get_date_field(self) -> str:
        return 'fecha'

    def get_amount_field(self) -> str:
        return 'total'

    def get_category_field(self) -> str:
        return 'id_categoria__nombre'  # ← Específico para categorías

    def get_group_fields(self, periodo: str):
        return [
            'id_categoria__nombre',
            'id_sucursal__nombre'
        ]

    # ¡Listo! Ya tienes:
    # - service.get_statistics_by_category(filters)
    # - Filtrado por categoria_id automático
    # - Y toda la funcionalidad base
```

## 📝 Ejemplo Completo: Vista con Servicio

```python
# views.py
from django.shortcuts import render
from app.services.mi_nuevo_service import MiNuevoService

def mi_reporte_view(request):
    # 1. Instanciar servicio
    service = MiNuevoService()

    # 2. Obtener datos para filtros (dropdowns, etc.)
    filter_data = service.get_filter_data()

    # 3. Extraer parámetros del request
    params = service.extract_filters_from_request(request)

    # 4. Construir filtros validados
    filters = service.build_filters(**params)

    # 5. Obtener datos agregados por período
    periodo = request.GET.get('periodo', 'mensual')
    datos = service.get_balances_by_period(filters, periodo)

    # 6. Calcular acumulados (opcional)
    datos = service.calculate_accumulated(datos)

    # 7. Calcular estadísticas (opcional)
    stats = service.calculate_statistics(filters)

    # 8. Análisis adicionales (opcional)
    por_categoria = service.get_statistics_by_category(filters)

    # 9. Construir contexto
    context = {
        'datos': datos,
        'estadisticas': stats,
        'por_categoria': por_categoria,
        **filter_data,  # Incluye cuentas, sucursales, años, etc.
        'periodo': periodo
    }

    return render(request, 'mi_app/reporte.html', context)
```

## 🧪 Testing

### Test de Servicio Personalizado

```python
# tests/test_mi_service.py
from django.test import TestCase
from app.services.mi_nuevo_service import MiNuevoService
from mi_app.models import MiModelo

class MiServiceTest(TestCase):
    def setUp(self):
        self.service = MiNuevoService()
        # Crear datos de prueba...

    def test_build_filters(self):
        """Prueba construcción de filtros"""
        filters = self.service.build_filters(
            year=2024,
            month=5,
            sucursal_id=1
        )

        self.assertEqual(filters['fecha__year'], 2024)
        self.assertEqual(filters['fecha__month'], 5)
        self.assertEqual(filters['id_sucursal_id'], 1)

    def test_get_balances_by_period(self):
        """Prueba agregación por período"""
        filters = {'fecha__year': 2024}
        balances = self.service.get_balances_by_period(
            filters,
            'mensual'
        )

        self.assertTrue(len(balances) > 0)
        self.assertIn('total_mi_modelo', balances[0])

    def test_calculate_statistics(self):
        """Prueba cálculo de estadísticas"""
        filters = {}
        stats = self.service.calculate_statistics(filters)

        self.assertIn('total', stats)
        self.assertIn('promedio', stats)
        self.assertIn('maximo', stats)
```

## 🚀 Migración de Servicios Existentes

### Paso 1: Identificar Código Reutilizable

Revisa tu servicio existente y marca:

- ✅ Código que puede moverse a utils
- ⚠️ Código específico del modelo
- 🔧 Código que necesita personalización

### Paso 2: Crear Nuevo Servicio Heredado

```python
# Antes (monolítico)
class MiServiceAntiguo:
    def build_filters(self, ...):
        # 100 líneas de validación manual
        ...

    def aggregate_data(self, ...):
        # 80 líneas de agregación
        ...

    def calculate_stats(self, ...):
        # 60 líneas de estadísticas
        ...

    # Total: ~300 líneas

# Después (modular)
from app.services.base_report_service import BaseReportService

class MiServiceNuevo(BaseReportService):
    def get_model(self):
        return MiModelo

    def get_date_field(self):
        return 'fecha'

    def get_amount_field(self):
        return 'monto'

    def get_group_fields(self, periodo):
        return ['campo1', 'campo2']

    # Métodos específicos si es necesario
    def mi_logica_especial(self):
        # Solo código único
        ...

    # Total: ~80 líneas (73% reducción!)
```

### Paso 3: Actualizar Vistas

```python
# Antes
from mi_app.services import MiServiceAntiguo

def mi_vista(request):
    service = MiServiceAntiguo()
    # El resto del código probablemente no cambia
    ...

# Después
from mi_app.services import MiServiceNuevo  # ← Solo cambiar el import

def mi_vista(request):
    service = MiServiceNuevo()  # ← Y el nombre aquí
    # El resto del código NO cambia (misma interfaz)
    ...
```

## 📊 Métricas de Impacto

### Reducción de Código

| Módulo             | Antes (Líneas)  | Después (Líneas) | Reducción |
| ------------------ | --------------- | ---------------- | --------- |
| balance_service.py | 316             | ~180             | **43%**   |
| compras_service.py | ~300 (estimado) | ~50              | **83%**   |
| ventas_service.py  | ~300 (estimado) | ~80              | **73%**   |
| **TOTAL**          | **~916**        | **~310 + utils** | **~50%**  |

### Código Compartido

- `filter_utils.py`: **250 líneas** reutilizables
- `period_utils.py`: **300 líneas** reutilizables
- `base_report_service.py`: **350 líneas** reutilizables
- **Total utils**: **900 líneas** → usadas por N servicios

### Beneficio Compuesto

Cada nuevo servicio:

- ❌ Antes: ~300 líneas de código
- ✅ Ahora: ~50-80 líneas de código
- 🎉 **Ahorro: ~220 líneas por servicio**

Con 10 servicios:

- ❌ Sin arquitectura: 3000 líneas
- ✅ Con arquitectura: ~900 (utils) + ~650 (10 servicios) = 1550 líneas
- 🚀 **Ahorro total: ~50% de código**

## 🎓 Patrones de Diseño Utilizados

1. **Template Method Pattern**

   - `BaseReportService` define el esqueleto de algoritmos
   - Subclases implementan pasos específicos

2. **Strategy Pattern**

   - `PeriodAggregator` encapsula diferentes estrategias de agregación
   - `FilterBuilder` encapsula estrategias de validación

3. **Dependency Injection**

   - Servicios reciben dependencias en `__init__`
   - Facilita testing con mocks

4. **Single Responsibility Principle**

   - Cada clase tiene una responsabilidad única
   - `FilterBuilder` → filtros
   - `PeriodAggregator` → agregación
   - `StatisticsCalculator` → estadísticas

5. **Open/Closed Principle**
   - Clases abiertas para extensión (herencia)
   - Cerradas para modificación (código base estable)

## ⚠️ Advertencias y Consideraciones

### 1. No Sobre-abstraer

❌ **MAL:**

```python
# Heredar cuando no es necesario
class MiServiceMuySimple(BaseReportService):
    # Solo necesito filtrar por fecha, no necesito toda la base
    ...
```

✅ **BIEN:**

```python
# Usar utils directamente si es simple
from app.services.filter_utils import FilterBuilder

def mi_funcion_simple(request):
    builder = FilterBuilder()
    filters = builder.build_standard_filters(
        year=request.GET.get('year')
    )
    return MiModelo.objects.filter(**filters)
```

### 2. Evitar Dependencias Circulares

❌ **MAL:**

```python
# En filter_utils.py
from app.services.balance_service import BalanceAnalysisService  # ← ERROR
```

✅ **BIEN:**

```python
# En filter_utils.py
# No importar servicios, solo modelos y Django ORM
from django.db.models import Sum
```

### 3. Mantener Compatibilidad

Si tienes código existente que usa servicios:

```python
# Mantener método antiguo por compatibilidad
class MiServiceNuevo(BaseReportService):
    # ... métodos abstractos ...

    # Método viejo (deprecated)
    def metodo_antiguo(self, param1, param2):
        """DEPRECATED: Usar nuevo_metodo() en su lugar"""
        import warnings
        warnings.warn(
            "metodo_antiguo() está deprecated, usar nuevo_metodo()",
            DeprecationWarning
        )
        return self.nuevo_metodo(param1, param2)
```

## 📚 Recursos Adicionales

### Documentos Relacionados

- `Docs/DATATABLES_MIGRATION.md` - Migración frontend (similar)
- `Docs/BALANCES_MIGRATION_SUMMARY.md` - Ejemplo de refactorización
- `static/js/README_DATATABLES.md` - Arquitectura frontend modular

### Referencias de Código

- `balance_service.py` - Ejemplo completo de migración
- `compras_service.py` - Ejemplo de nuevo servicio simple
- `ventas_service.py` - Ejemplo de servicio con personalizaciones

## 🤝 Contribución

Al añadir funcionalidad nueva:

1. **Pregunta:** ¿Es específico de un módulo o reutilizable?

   - Reutilizable → Añadir a utils
   - Específico → Añadir al servicio específico

2. **Prueba:** Asegúrate de que no rompes servicios existentes

   - Ejecutar tests de todos los servicios
   - Verificar vistas que usan servicios

3. **Documenta:** Actualiza este documento si añades:
   - Nuevos métodos a clases base
   - Nuevas clases de utilidades
   - Nuevos patrones de uso

## 📞 Soporte

Si tienes dudas sobre:

- Cómo implementar un nuevo servicio
- Cómo migrar código existente
- Cómo extender funcionalidad base

Consulta los ejemplos en `compras_service.py` y `ventas_service.py`.

---

**Creado:** Diciembre 2024  
**Última actualización:** Diciembre 2024  
**Versión:** 1.0
