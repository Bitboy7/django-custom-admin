# Services - Backend Service Layer

## 📁 Estructura del directorio

```
app/services/
├── README.md                        ← Este archivo
├── filter_utils.py                  ← Utilidades de filtrado
├── period_utils.py                  ← Utilidades de períodos y estadísticas
├── base_report_service.py           ← Clase base abstracta para reportes
├── balance_service.py               ← Servicio de balances/gastos (refactorizado)
├── compras_service.py               ← Ejemplo: Servicio de compras
└── ventas_service.py                ← Ejemplo: Servicio de ventas
```

## 🎯 Propósito

Este directorio contiene la **capa de servicios** de la aplicación, implementando lógica de negocio reutilizable independiente de las vistas.

### ¿Por qué una capa de servicios?

```
❌ SIN capa de servicios:
Views.py
├── 200 líneas de lógica de negocio
├── 100 líneas de queries complejas
├── 80 líneas de cálculos
└── 50 líneas de renderizado
Total: 430 líneas - Difícil de mantener y testear

✅ CON capa de servicios:
Views.py (50 líneas)
├── service.get_filter_data()
├── service.build_filters()
├── service.get_balances()
└── render()

Services.py (reutilizable)
├── Lógica de negocio
├── Queries complejas
└── Cálculos
```

**Beneficios:**

- ✅ **Reusabilidad**: Misma lógica en múltiples vistas/APIs
- ✅ **Testabilidad**: Tests unitarios sin setup de HTTP
- ✅ **Mantenibilidad**: Lógica separada de presentación
- ✅ **Consistencia**: Mismas reglas en toda la app

## 🧩 Componentes

### 1. Utils (Utilidades Reutilizables)

#### `filter_utils.py`

Construcción y validación de filtros para queries.

```python
from app.services.filter_utils import FilterBuilder, FilterOptionsProvider

# Construir filtros validados
builder = FilterBuilder()
filters = builder.build_standard_filters(
    year=2024,
    month=5,
    cuenta_id=1,
    sucursal_id=2
)
# → {'fecha__year': 2024, 'fecha__month': 5, 'id_cuenta_banco_id': 1, ...}

# Obtener opciones para UI
provider = FilterOptionsProvider()
options = provider.get_filter_options(
    model=MiModelo,
    include_cuentas=True,
    include_sucursales=True
)
# → {'cuentas': QuerySet, 'sucursales': QuerySet, 'available_years': [...]}
```

**Casos de uso:**

- Validar parámetros de usuario
- Construir filtros de Django ORM
- Obtener opciones para dropdowns

#### `period_utils.py`

Agregación temporal y cálculos estadísticos.

```python
from app.services.period_utils import (
    PeriodAggregator,
    StatisticsCalculator,
    AccumulatedCalculator
)

# Agregar por período
aggregator = PeriodAggregator()
datos = aggregator.aggregate_by_period(
    queryset=MiModelo.objects.all(),
    periodo='mensual',
    group_fields=['categoria', 'sucursal'],
    sum_field='monto'
)

# Calcular estadísticas
calculator = StatisticsCalculator()
stats = calculator.calculate_extended_stats(
    queryset=MiModelo.objects.all(),
    field='monto'
)
# → {'total': 1000, 'promedio': 100, 'maximo': 200, 'mediana': 95, ...}

# Calcular acumulados
accumulated = AccumulatedCalculator()
datos_con_acumulado = accumulated.calculate_accumulated(
    data=[{'total': 100}, {'total': 200}],
    value_field='total'
)
# → [{'total': 100, 'acumulado': 100}, {'total': 200, 'acumulado': 300}]
```

**Casos de uso:**

- Reportes por día/semana/mes
- Estadísticas descriptivas
- Valores acumulados y porcentajes

### 2. Base Classes (Clases Base Reutilizables)

#### `base_report_service.py`

Define la estructura base para servicios de reporte.

```python
from app.services.base_report_service import BaseReportService

class MiReporteService(BaseReportService):
    """
    Hereda toda la funcionalidad común, solo implementa lo específico
    """

    # Métodos abstractos (OBLIGATORIOS)
    def get_model(self):
        return MiModelo

    def get_date_field(self) -> str:
        return 'fecha'

    def get_amount_field(self) -> str:
        return 'monto'

    def get_group_fields(self, periodo: str):
        return ['categoria', 'sucursal']

    # ¡Ya está! Ahora tienes:
    # - service.get_filter_data()
    # - service.build_filters()
    # - service.get_balances_by_period()
    # - service.calculate_statistics()
    # - Y mucho más...
```

**Para entidades con categorías:**

```python
from app.services.base_report_service import BaseReportServiceWithCategories

class MiServicioConCategorias(BaseReportServiceWithCategories):
    # Mismo código anterior +
    def get_category_field(self) -> str:
        return 'id_categoria__nombre'

    # Ahora también tienes:
    # - service.get_statistics_by_category()
    # - Filtrado por categoria_id automático
```

### 3. Servicios Específicos

#### `balance_service.py`

Servicio para análisis de balances y gastos (refactorizado).

```python
from app.services.balance_service import BalanceAnalysisService

service = BalanceAnalysisService()

# En una vista
def balances_view(request):
    service = BalanceAnalysisService()

    # Obtener contexto completo
    context = service.get_full_context(request)

    return render(request, 'gastos/balances.html', context)
```

**Estado:**

- ✅ Refactorizado para usar arquitectura modular
- ✅ Reducido de 316 a ~180 líneas (43% reducción)
- ✅ Mantiene compatibilidad con código existente

#### `compras_service.py` (Ejemplo)

Servicio de ejemplo para compras.

```python
from app.services.compras_service import ComprasAnalysisService

service = ComprasAnalysisService()

# Obtener compras por proveedor
stats = service.get_compras_por_proveedor(filters)
```

**Estado:**

- 📝 Ejemplo de implementación
- ⚠️ Requiere modelo Compras para funcionar

#### `ventas_service.py` (Ejemplo)

Servicio de ejemplo para ventas.

```python
from app.services.ventas_service import VentasAnalysisService

service = VentasAnalysisService()

# Top 10 clientes
top_clientes = service.get_top_clientes(filters, limit=10)

# Ventas por producto
por_producto = service.get_ventas_por_producto(filters)
```

**Estado:**

- 📝 Ejemplo de implementación avanzada
- ⚠️ Requiere modelo Ventas para funcionar

## 🚀 Quick Start

### Crear un Nuevo Servicio

**Paso 1:** Crear archivo en `app/services/`

```python
# mi_servicio.py
from app.services.base_report_service import BaseReportService

class MiServicio(BaseReportService):
    def get_model(self):
        from mi_app.models import MiModelo
        return MiModelo

    def get_date_field(self) -> str:
        return 'fecha'

    def get_amount_field(self) -> str:
        return 'monto'

    def get_group_fields(self, periodo: str):
        return ['campo1', 'campo2']
```

**Paso 2:** Usar en una vista

```python
# views.py
from app.services.mi_servicio import MiServicio

def mi_vista(request):
    service = MiServicio()

    # Obtener opciones para filtros
    filter_options = service.get_filter_data()

    # Construir filtros desde request
    filters = service.build_filters(
        year=request.GET.get('year'),
        month=request.GET.get('month')
    )

    # Obtener datos agregados
    datos = service.get_balances_by_period(filters, 'mensual')

    # Estadísticas
    stats = service.calculate_statistics(filters)

    context = {
        'datos': datos,
        'stats': stats,
        **filter_options
    }

    return render(request, 'mi_template.html', context)
```

**¡Eso es todo!** Con ~20 líneas tienes un servicio completo.

## 📖 Documentación Completa

Para documentación detallada, ver:

📄 **[BACKEND_SERVICES_ARCHITECTURE.md](../Docs/BACKEND_SERVICES_ARCHITECTURE.md)**

Incluye:

- 🏗️ Arquitectura completa
- 📊 Comparación antes/después
- 🔧 Guías de uso
- 🧪 Ejemplos de testing
- 🚀 Guía de migración
- 📚 Patrones de diseño

## 🔄 Comparación con Frontend

Esta arquitectura es paralela a la modularización frontend:

| Aspecto         | Frontend                 | Backend                              |
| --------------- | ------------------------ | ------------------------------------ |
| **Utils**       | `datatables-utils.js`    | `filter_utils.py`, `period_utils.py` |
| **Base**        | Funciones reutilizables  | `BaseReportService`                  |
| **Específicos** | `balances-datatables.js` | `balance_service.py`                 |
| **Reducción**   | 33% código               | 43% código                           |
| **Objetivo**    | Reutilización JS         | Reutilización Python                 |

## 💡 Mejores Prácticas

### ✅ DO (Hacer)

```python
# Usar servicios para lógica de negocio
class MiVista(View):
    def get(self, request):
        service = MiServicio()
        datos = service.get_balances_by_period(filters, periodo)
        return render(request, 'template.html', {'datos': datos})

# Heredar de clases base
class NuevoServicio(BaseReportService):
    # Solo implementar lo específico
    ...

# Extender funcionalidad
class ServicioPersonalizado(BaseReportService):
    def mi_metodo_extra(self):
        # Código específico
        ...
```

### ❌ DON'T (No hacer)

```python
# NO poner lógica de negocio en vistas
def mi_vista(request):
    # ❌ 100 líneas de queries y cálculos aquí
    gastos = Gastos.objects.filter(...)
    total = sum(...)
    promedio = ...
    # Difícil de testear y reutilizar

# NO duplicar código
class ServicioA:
    def build_filters(self):
        # Código duplicado
        ...

class ServicioB:
    def build_filters(self):
        # Mismo código duplicado ❌
        ...

# Usar FilterBuilder en su lugar ✅

# NO crear dependencias circulares
# En filter_utils.py
from app.services.balance_service import ...  # ❌
```

## 🧪 Testing

```python
# tests/test_mi_servicio.py
from django.test import TestCase
from app.services.mi_servicio import MiServicio

class MiServicioTest(TestCase):
    def setUp(self):
        self.service = MiServicio()

    def test_build_filters(self):
        filters = self.service.build_filters(
            year=2024,
            month=5
        )
        self.assertEqual(filters['fecha__year'], 2024)

    def test_calculate_statistics(self):
        # Crear datos de prueba
        ...

        stats = self.service.calculate_statistics({})
        self.assertIn('total', stats)
        self.assertIn('promedio', stats)
```

## 📞 Preguntas Frecuentes

### ¿Cuándo crear un nuevo servicio?

Crea un nuevo servicio cuando:

- ✅ Tienes lógica de negocio compleja
- ✅ La lógica se reutiliza en múltiples vistas
- ✅ Quieres tests unitarios independientes
- ✅ La entidad tiene reportes/agregaciones

NO creas un servicio si:

- ❌ Es una query simple de 1-2 líneas
- ❌ Solo se usa en un lugar
- ❌ Es solo formateo de datos

### ¿Heredar o usar utils directamente?

**Heredar de BaseReportService:**

- ✅ Reportes completos con filtros, agregaciones, estadísticas
- ✅ Múltiples métodos relacionados
- ✅ Consistencia con otros servicios

**Usar utils directamente:**

- ✅ Funcionalidad puntual (solo filtros, solo stats)
- ✅ Scripts o comandos management
- ✅ Casos simples sin necesidad de estructura completa

### ¿Cómo añadir funcionalidad nueva?

1. **¿Es reutilizable?** → Añadir a utils
2. **¿Es para todos los reportes?** → Añadir a base class
3. **¿Es específico de un módulo?** → Añadir al servicio específico

### ¿Afecta al código existente?

No. Los servicios refactorizados mantienen la misma interfaz pública:

```python
# Código viejo sigue funcionando
service = BalanceAnalysisService()
context = service.get_full_context(request)  # ✅ Sigue funcionando
```

Internamente usa la nueva arquitectura, pero las vistas no necesitan cambios.

## 📝 Changelog

### v1.0 (Diciembre 2024)

- ✨ Arquitectura modular inicial
- ✨ `filter_utils.py` creado
- ✨ `period_utils.py` creado
- ✨ `base_report_service.py` creado
- ♻️ `balance_service.py` refactorizado (43% reducción)
- 📝 `compras_service.py` ejemplo creado
- 📝 `ventas_service.py` ejemplo creado
- 📚 Documentación completa

## 🤝 Contribuir

Al modificar servicios:

1. ✅ Ejecutar tests existentes
2. ✅ Añadir tests para funcionalidad nueva
3. ✅ Actualizar documentación
4. ✅ Mantener compatibilidad con código existente

---

**Para más información:** Ver `Docs/BACKEND_SERVICES_ARCHITECTURE.md`
