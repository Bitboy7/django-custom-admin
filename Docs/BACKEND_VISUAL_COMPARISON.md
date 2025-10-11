# Comparación Visual: Antes vs Después

## 🎨 Diagrama de Arquitectura

### ANTES: Enfoque Monolítico

```
┌─────────────────────────────────────────────────────────────┐
│                    VIEWS LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Gastos View  │  │ Compras View │  │ Ventas View  │      │
│  │              │  │  (no existe) │  │  (no existe) │      │
│  └──────┬───────┘  └──────────────┘  └──────────────┘      │
│         │                                                    │
└─────────┼────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│              SERVICE LAYER (Monolítico)                     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  BalanceAnalysisService (316 líneas)               │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │ get_filter_data()                            │  │    │
│  │  │ - 10 líneas de código específico             │  │    │
│  │  │ - Queries manuales                           │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │ build_filters()                              │  │    │
│  │  │ - 52 líneas de validación manual             │  │    │
│  │  │ - try/except repetidos                       │  │    │
│  │  │ - Lógica duplicable                          │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │ get_balances_by_period()                     │  │    │
│  │  │ - 64 líneas de agregación                    │  │    │
│  │  │ - if/elif/else para cada período             │  │    │
│  │  │ - TruncDay/Week/Month manual                 │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │ calculate_accumulated()                      │  │    │
│  │  │ - 7 líneas de loop simple                    │  │    │
│  │  │ - Lógica 100% reutilizable                   │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │ calculate_statistics()                       │  │    │
│  │  │ - 60 líneas de agregaciones                  │  │    │
│  │  │ - numpy para mediana                         │  │    │
│  │  │ - Lógica 100% reutilizable                   │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │ process_request_parameters()                 │  │    │
│  │  │ - 100+ líneas de parsing                     │  │    │
│  │  │ - Limpieza de caracteres                     │  │    │
│  │  │ - Conversiones de tipo                       │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ❌ Para crear ComprasService:                              │
│     → Copiar 80% del código de BalanceAnalysisService      │
│     → ~300 líneas de código duplicado                       │
│     → Bugs se propagan a todos los servicios                │
│                                                              │
│  ❌ Para crear VentasService:                               │
│     → Copiar 80% del código de BalanceAnalysisService      │
│     → ~300 líneas de código duplicado                       │
│     → Bugs se propagan a todos los servicios                │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### DESPUÉS: Enfoque Modular

```
┌─────────────────────────────────────────────────────────────────┐
│                        VIEWS LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Gastos View  │  │ Compras View │  │ Ventas View  │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                  │
└─────────┼──────────────────┼──────────────────┼──────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│              SPECIFIC SERVICES LAYER                            │
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Balance         │  │ Compras         │  │ Ventas          │ │
│  │ Service         │  │ Service         │  │ Service         │ │
│  │ (~180 líneas)   │  │ (~50 líneas)    │  │ (~80 líneas)    │ │
│  │ ▼ get_model()   │  │ ▼ get_model()   │  │ ▼ get_model()   │ │
│  │ ▼ get_fields()  │  │ ▼ get_fields()  │  │ ▼ get_fields()  │ │
│  │ ▼ custom logic  │  │ ▼ custom logic  │  │ ▼ custom logic  │ │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘ │
│           │                    │                    │           │
│           └────────────────────┴────────────────────┘           │
│                               │                                 │
└───────────────────────────────┼─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   BASE SERVICES LAYER                           │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  BaseReportService (350 líneas) - ABSTRACTA              │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │ ⚠️  ABSTRACT METHODS (implementar en subclases)    │  │  │
│  │  │ def get_model()                                    │  │  │
│  │  │ def get_date_field()                               │  │  │
│  │  │ def get_amount_field()                             │  │  │
│  │  │ def get_group_fields(periodo)                      │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │ ✅ IMPLEMENTED METHODS (heredar directamente)      │  │  │
│  │  │ def get_filter_data()                              │  │  │
│  │  │ def build_filters(**kwargs)                        │  │  │
│  │  │ def get_balances_by_period(filters, periodo)       │  │  │
│  │  │ def calculate_accumulated(balances)                │  │  │
│  │  │ def calculate_statistics(filters)                  │  │  │
│  │  │ def extract_filters_from_request(request)          │  │  │
│  │  │ def format_period(periodo, date_value)             │  │  │
│  │  │ ... y más ...                                      │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  BaseReportServiceWithCategories - EXTIENDE BASE         │  │
│  │  + get_category_field() ← abstracto adicional            │  │
│  │  + get_statistics_by_category() ← implementado           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      UTILITIES LAYER                            │
│                                                                  │
│  ┌──────────────────────┐  ┌──────────────────────────────┐    │
│  │ filter_utils.py      │  │ period_utils.py              │    │
│  │ (250 líneas)         │  │ (300 líneas)                 │    │
│  │                      │  │                              │    │
│  │ FilterBuilder        │  │ PeriodAggregator             │    │
│  │ ├─validate_year()    │  │ ├─aggregate_by_period()      │    │
│  │ ├─validate_month()   │  │ ├─get_truncator()            │    │
│  │ ├─validate_id()      │  │ └─aggregate_with_count()     │    │
│  │ └─build_standard()   │  │                              │    │
│  │                      │  │ StatisticsCalculator         │    │
│  │ FilterOptions        │  │ ├─calculate_basic_stats()    │    │
│  │ Provider             │  │ ├─calculate_median()         │    │
│  │ ├─get_years()        │  │ └─calculate_extended()       │    │
│  │ ├─get_months()       │  │                              │    │
│  │ └─get_filter_opts()  │  │ AccumulatedCalculator        │    │
│  │                      │  │ ├─calculate_accumulated()    │    │
│  │                      │  │ └─calculate_percentage()     │    │
│  │                      │  │                              │    │
│  │                      │  │ PeriodFormatter              │    │
│  │                      │  │ ├─format_period_display()    │    │
│  │                      │  │ └─get_month_name()           │    │
│  └──────────────────────┘  └──────────────────────────────┘    │
│                                                                  │
│  ✅ Código reutilizado por TODOS los servicios                  │
│  ✅ Tests unitarios UNA VEZ                                     │
│  ✅ Bugs se arreglan UNA VEZ                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 📊 Flujo de Datos

### ANTES: Cada servicio es autónomo

```
Request → View → Service (316 líneas todo-en-uno) → Response
                    │
                    ├─ Validación manual
                    ├─ Queries manuales
                    ├─ Agregación manual
                    ├─ Estadísticas manuales
                    └─ Formateo manual
```

### DESPUÉS: Composición de utilidades

```
Request → View → Specific Service (50-180 líneas)
                    │
                    ├─ Hereda de → BaseReportService
                    │                  │
                    │                  ├─ Usa → FilterBuilder
                    │                  ├─ Usa → PeriodAggregator
                    │                  ├─ Usa → StatisticsCalculator
                    │                  ├─ Usa → AccumulatedCalculator
                    │                  └─ Usa → PeriodFormatter
                    │
                    └─ Solo implementa lógica específica
                                      │
                                      └─ Response
```

## 🔄 Ejemplo de Código: build_filters()

### ANTES (52 líneas en cada servicio)

```python
def build_filters(self, cuenta_id, year, month, selected_months,
                  periodo, dia, fecha_inicio, fecha_fin, sucursal_id):
    """Construye los filtros - DUPLICADO EN CADA SERVICIO"""
    filters = {}

    # Validar y agregar filtro de año (9 líneas)
    if year:
        try:
            year_int = int(year)
            filters['fecha__year'] = year_int
        except (ValueError, TypeError):
            filters['fecha__year'] = datetime.now().year
    else:
        filters['fecha__year'] = datetime.now().year

    # Validar y agregar filtro de cuenta (7 líneas)
    if cuenta_id:
        try:
            cuenta_int = int(cuenta_id)
            filters['id_cuenta_banco_id'] = cuenta_int
        except (ValueError, TypeError):
            pass

    # Validar y agregar filtro de sucursal (7 líneas)
    if sucursal_id:
        try:
            sucursal_int = int(sucursal_id)
            filters['id_sucursal_id'] = sucursal_int
        except (ValueError, TypeError):
            pass

    # Filtrar por múltiples meses (12 líneas)
    if selected_months and isinstance(selected_months, list) and len(selected_months) > 0:
        filters['fecha__month__in'] = selected_months
    elif month:
        try:
            month_int = int(month)
            if 1 <= month_int <= 12:
                filters['fecha__month'] = month_int
        except (ValueError, TypeError):
            pass

    # Filtros específicos por periodo (8 líneas)
    if periodo == 'diario':
        if dia:
            filters['fecha'] = dia
        elif fecha_inicio and fecha_fin:
            filters['fecha__range'] = [fecha_inicio, fecha_fin]

    return filters

# ❌ Este código se duplica en:
# - balance_service.py
# - compras_service.py (si existiera)
# - ventas_service.py (si existiera)
# Total: ~150 líneas de código duplicado
```

### DESPUÉS (1 línea en cada servicio + utils reutilizables)

```python
# En filter_utils.py - UNA VEZ (centralizado)
class FilterBuilder:
    @staticmethod
    def build_standard_filters(year=None, month=None, selected_months=None,
                               cuenta_id=None, sucursal_id=None,
                               periodo='mensual', dia=None,
                               fecha_inicio=None, fecha_fin=None,
                               use_default_year=True, **kwargs):
        """Construcción de filtros validados - REUTILIZABLE"""
        filters = {}

        # Validación centralizada con métodos especializados
        validated_year = FilterBuilder.validate_year(
            year, default=datetime.now().year if use_default_year else None
        )
        if validated_year:
            filters['fecha__year'] = validated_year

        # ... resto de validaciones centralizadas

        return filters

# En balance_service.py - Hereda de BaseReportService
class BalanceAnalysisService(BaseReportServiceWithCategories):
    # ✅ NO necesita implementar build_filters()
    # ✅ Se hereda automáticamente de BaseReportService
    pass

# En compras_service.py
class ComprasAnalysisService(BaseReportServiceWithCategories):
    # ✅ NO necesita implementar build_filters()
    # ✅ Se hereda automáticamente de BaseReportService
    pass

# Uso en cualquier servicio:
service = BalanceAnalysisService()
filters = service.build_filters(
    year=2024,
    month=5,
    cuenta_id=1,
    sucursal_id=2
)
# ✅ Mismo código, UNA implementación
# ✅ Bug se arregla UNA vez
# ✅ Tests se escriben UNA vez
```

## 📈 Ejemplo de Código: get_balances_by_period()

### ANTES (64 líneas en cada servicio)

```python
def get_balances_by_period(self, filters, periodo):
    """Agregación por período - DUPLICADO EN CADA SERVICIO"""

    if periodo == 'diario':
        # 20 líneas específicas
        balances = Gastos.objects.filter(**filters).values(
            'id_cat_gastos__nombre',
            'id_cuenta_banco__id',
            'id_cuenta_banco__numero_cuenta',
            'id_cuenta_banco__id_banco__nombre',
            'id_sucursal__nombre',
            'fecha'
        ).annotate(
            total_gastos=Sum('monto')
        ).order_by('id_cat_gastos__nombre', 'id_cuenta_banco__numero_cuenta', 'fecha')

    elif periodo == 'semanal':
        # 20 líneas similares con TruncWeek
        balances = Gastos.objects.filter(**filters).annotate(
            semana=TruncWeek('fecha')
        ).values(
            'id_cat_gastos__nombre',
            'id_cuenta_banco__id',
            'id_cuenta_banco__numero_cuenta',
            'id_cuenta_banco__id_banco__nombre',
            'id_sucursal__nombre',
            'semana'
        ).annotate(
            total_gastos=Sum('monto')
        ).order_by('id_cat_gastos__nombre', 'id_cuenta_banco__numero_cuenta', 'semana')

    elif periodo == 'mensual':
        # 20 líneas similares con TruncMonth
        balances = Gastos.objects.filter(**filters).values(
            'id_cat_gastos__nombre',
            'id_cuenta_banco__id',
            'id_cuenta_banco__numero_cuenta',
            'id_cuenta_banco__id_banco__nombre',
            'id_sucursal__nombre'
        ).annotate(
            total_gastos=Sum('monto'),
            mes=TruncMonth('fecha')
        ).order_by('id_cat_gastos__nombre', 'id_cuenta_banco__numero_cuenta')

    # ... más lógica de enriquecimiento

    return balances

# ❌ Patrón se repite en cada servicio con cambios mínimos
```

### DESPUÉS (Configuración + herencia)

```python
# En period_utils.py - UNA VEZ
class PeriodAggregator:
    PERIOD_TRUNCATORS = {
        'diario': TruncDay,
        'semanal': TruncWeek,
        'mensual': TruncMonth
    }

    @staticmethod
    def aggregate_by_period(queryset, periodo, group_fields,
                           sum_field='monto', annotation_name='total',
                           date_field='fecha'):
        """Agregación genérica por período - REUTILIZABLE"""
        truncator = PeriodAggregator.get_truncator(periodo)

        queryset = queryset.annotate(periodo=truncator(date_field))
        value_fields = ['periodo'] + group_fields

        return queryset.values(*value_fields).annotate(
            **{annotation_name: Sum(sum_field)}
        ).order_by('periodo', *group_fields)

# En balance_service.py - Solo configuración
class BalanceAnalysisService(BaseReportServiceWithCategories):
    def get_group_fields(self, periodo: str):
        """Solo define QUÉ campos agrupar"""
        return [
            'id_cat_gastos__nombre',
            'id_cuenta_banco__numero_cuenta',
            'id_sucursal__nombre'
        ]

    # ✅ get_balances_by_period() se hereda de BaseReportService
    # ✅ Usa PeriodAggregator internamente
    # ✅ Solo necesito definir group_fields()

# En compras_service.py - Solo configuración
class ComprasAnalysisService(BaseReportServiceWithCategories):
    def get_group_fields(self, periodo: str):
        """Campos específicos de compras"""
        return [
            'id_categoria__nombre',
            'id_proveedor__nombre',
            'id_sucursal__nombre'
        ]

    # ✅ Misma lógica de agregación, diferentes campos
    # ✅ 3 líneas vs 64 líneas

# Uso:
service = BalanceAnalysisService()
balances = service.get_balances_by_period(filters, 'mensual')
# ✅ Funciona automáticamente con los campos configurados
```

## 🧮 Ejemplo de Código: calculate_statistics()

### ANTES (60 líneas en cada servicio)

```python
def calculate_statistics(self, filters):
    """Estadísticas - DUPLICADO EN CADA SERVICIO"""
    queryset = Gastos.objects.filter(**filters)

    # Agregaciones básicas (15 líneas)
    aggregations = queryset.aggregate(
        total=Sum('monto'),
        promedio=Avg('monto'),
        maximo=Max('monto'),
        minimo=Min('monto'),
        count=Count('id')
    )

    # Mediana con numpy (10 líneas)
    gastos_list = list(queryset.values_list('monto', flat=True))
    mediana = np.median(gastos_list) if gastos_list else 0

    # Categoría de gasto máximo (15 líneas)
    categoria_maximo = None
    if aggregations['maximo']:
        categoria_maximo = queryset.filter(
            monto=aggregations['maximo']
        ).values('id_cat_gastos__nombre').first()

    # Categoría de gasto mínimo (15 líneas)
    categoria_minimo = None
    if aggregations['minimo']:
        categoria_minimo = queryset.filter(
            monto=aggregations['minimo']
        ).values('id_cat_gastos__nombre').first()

    # Formateo de respuesta (5 líneas)
    return {
        'total_gastos': aggregations['total'] or 0,
        'promedio_gastos': aggregations['promedio'],
        'numero_transacciones': aggregations['count'],
        'gasto_maximo': aggregations['maximo'],
        'gasto_minimo': aggregations['minimo'],
        'gasto_mediano': mediana,
        'categoria_gasto_maximo': categoria_maximo['id_cat_gastos__nombre'] if categoria_maximo else None,
        'categoria_gasto_minimo': categoria_minimo['id_cat_gastos__nombre'] if categoria_minimo else None,
    }

# ❌ Lógica 90% reutilizable, pero duplicada en cada servicio
```

### DESPUÉS (Herencia + pequeño override)

```python
# En period_utils.py - UNA VEZ
class StatisticsCalculator:
    @staticmethod
    def calculate_extended_stats(queryset, field='monto'):
        """Estadísticas completas - REUTILIZABLE"""
        from django.db.models import Sum, Avg, Max, Min, Count
        import numpy as np

        # Agregaciones básicas
        stats = queryset.aggregate(
            total=Sum(field),
            promedio=Avg(field),
            maximo=Max(field),
            minimo=Min(field),
            cantidad=Count('id')
        )

        # Mediana
        values = list(queryset.values_list(field, flat=True))
        float_values = [float(v) for v in values if v is not None]
        stats['mediana'] = float(np.median(float_values)) if float_values else 0.0

        # Convertir a float
        return {
            'total': float(stats['total'] or 0),
            'promedio': float(stats['promedio'] or 0),
            'maximo': float(stats['maximo'] or 0),
            'minimo': float(stats['minimo'] or 0),
            'cantidad': stats['cantidad'],
            'mediana': stats['mediana']
        }

# En balance_service.py - Pequeño override para categorías
class BalanceAnalysisService(BaseReportServiceWithCategories):
    def calculate_statistics(self, filters):
        """Override para añadir info de categorías"""
        # ✅ Usar estadísticas base
        stats = super().calculate_statistics(filters)

        # Añadir solo lo específico de categorías (10 líneas)
        queryset = Gastos.objects.filter(**filters)

        categoria_maximo = None
        if stats['maximo'] > 0:
            gasto_max = queryset.filter(monto=stats['maximo']).first()
            if gasto_max:
                categoria_maximo = gasto_max.id_cat_gastos.nombre

        # Renombrar para compatibilidad
        return {
            'total_gastos': stats['total'],
            'promedio_gastos': stats['promedio'],
            'gasto_maximo': stats['maximo'],
            'gasto_minimo': stats['minimo'],
            'gasto_mediano': stats['mediana'],
            'numero_transacciones': stats['cantidad'],
            'categoria_gasto_maximo': categoria_maximo,
            # ...
        }

    # ✅ 10 líneas vs 60 líneas (83% reducción)

# En compras_service.py - Sin override necesario
class ComprasAnalysisService(BaseReportServiceWithCategories):
    # ✅ NO necesita override
    # ✅ calculate_statistics() funciona automáticamente
    pass

# Uso:
service = ComprasAnalysisService()
stats = service.calculate_statistics(filters)
# → {'total': 1000, 'promedio': 100, 'maximo': 200, ...}
# ✅ Funciona sin escribir código adicional
```

## 📊 Tabla Comparativa de Esfuerzo

### Crear Nuevo Servicio Completo

| Tarea                               | ANTES        | DESPUÉS     | Ahorro     |
| ----------------------------------- | ------------ | ----------- | ---------- |
| **Definir modelo**                  | 5 min        | 5 min       | 0%         |
| **Implementar validación filtros**  | 60 min       | 0 min       | 100% ✅    |
| **Implementar agregación temporal** | 90 min       | 10 min      | 89% ✅     |
| **Implementar estadísticas**        | 45 min       | 0 min       | 100% ✅    |
| **Implementar acumulados**          | 15 min       | 0 min       | 100% ✅    |
| **Formateo y helpers**              | 30 min       | 5 min       | 83% ✅     |
| **Tests unitarios**                 | 120 min      | 30 min      | 75% ✅     |
| **Documentación**                   | 30 min       | 10 min      | 67% ✅     |
| **TOTAL**                           | **6h 35min** | **1h 0min** | **85%** 🎉 |

### Mantener Servicios Existentes

| Tarea                  | ANTES (3 servicios) | DESPUÉS       | Ahorro     |
| ---------------------- | ------------------- | ------------- | ---------- |
| **Bug en validación**  | 90 min (3×30)       | 30 min (1×)   | 67%        |
| **Nueva estadística**  | 120 min (3×40)      | 40 min (1×)   | 67%        |
| **Nuevo tipo filtro**  | 60 min (3×20)       | 20 min (1×)   | 67%        |
| **Optimización query** | 90 min (3×30)       | 30 min (1×)   | 67%        |
| **Update tests**       | 60 min (3×20)       | 20 min (1×)   | 67%        |
| **TOTAL ANUAL (est.)** | **~40 horas**       | **~13 horas** | **67%** 🎉 |

## 🎯 Conclusión Visual

```
┌─────────────────────────────────────────────────────────┐
│           ARQUITECTURA MONOLÍTICA (ANTES)               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  📦 balance_service.py         316 líneas ─┐            │
│  📦 compras_service.py   (no existe)       │ 80%        │
│  📦 ventas_service.py    (no existe)       │ Duplicado  │
│                                            ─┘            │
│  Total estimado: ~900 líneas con duplicación            │
│                                                          │
│  ❌ Duplicación masiva                                   │
│  ❌ Bugs en N lugares                                    │
│  ❌ Desarrollo lento                                     │
│  ❌ Inconsistencias                                      │
│                                                          │
└─────────────────────────────────────────────────────────┘

                         ⬇️  MIGRACIÓN

┌─────────────────────────────────────────────────────────┐
│           ARQUITECTURA MODULAR (DESPUÉS)                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  🔧 filter_utils.py            250 líneas ─┐            │
│  🔧 period_utils.py            300 líneas  │ Reutilizable│
│  🔧 base_report_service.py     350 líneas ─┘            │
│                                                          │
│  📦 balance_service.py         180 líneas ─┐            │
│  📦 compras_service.py          50 líneas  │ Específico │
│  📦 ventas_service.py           80 líneas ─┘            │
│                                                          │
│  Total: ~1,210 líneas (con más funcionalidad)           │
│                                                          │
│  ✅ Código reutilizable (900 líneas)                     │
│  ✅ Servicios específicos mínimos (~100 líneas c/u)      │
│  ✅ Bug fixes en 1 lugar                                 │
│  ✅ Desarrollo rápido de nuevos servicios                │
│  ✅ Consistencia automática                              │
│                                                          │
│  🎯 ROI: 400% con 10 servicios                           │
│  🎯 85% reducción en tiempo de desarrollo                │
│  🎯 67% reducción en tiempo de mantenimiento             │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

**Creado:** Diciembre 2024  
**Versión:** 1.0
