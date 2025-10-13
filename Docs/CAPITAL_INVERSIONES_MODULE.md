# Módulo de Capital e Inversiones

## 📋 Descripción General

El módulo de **Capital e Inversiones** es un sistema completo para gestionar y rastrear movimientos de capital empresarial, inversiones y sus rendimientos. Este módulo permite llevar un control detallado de entradas y salidas de capital, categorizado por tipo de inversión, con reportes acumulados por sucursal, categoría y período.

## 🎯 Características Principales

### 1. **Gestión de Categorías de Inversión**

- Sistema independiente de categorías específicas para inversiones
- Categorías predefinidas incluyen:
  - Capital de Trabajo
  - Activos Fijos
  - Inversión Financiera
  - Inversión Inmobiliaria
  - Reinversión de Utilidades
  - Aportación de Socios
  - Investigación y Desarrollo
  - Expansión de Negocio
  - Tecnología e Infraestructura
  - Capacitación y Desarrollo

### 2. **Registro de Inversiones**

- **Dos tipos de movimiento:**
  - **ENTRADA**: Ingresos de capital (aportaciones, retornos)
  - **SALIDA**: Inversiones realizadas
- Campos principales:
  - Sucursal
  - Categoría de inversión
  - Cuenta bancaria
  - Monto (con soporte multi-moneda)
  - Fecha del movimiento
  - Descripción detallada
  - Notas adicionales
  - Documentos de soporte (PDF, Word, Excel, imágenes)

### 3. **Seguimiento de Rendimientos**

- Registro de rendimientos por inversión
- Cálculo automático de porcentaje de retorno (ROI)
- Tipos de rendimiento:
  - Dividendos
  - Intereses
  - Ganancias de capital
  - Otros rendimientos

### 4. **Reportes Acumulados**

Siguiendo la misma arquitectura de reportes que los módulos de gastos y ventas:

#### Por Sucursal:

- Totales acumulados por sucursal
- Balance de entradas vs salidas
- Agrupación por período (diario, semanal, mensual, anual)

#### Por Categoría:

- Distribución de inversiones por categoría
- Comparativa de montos por tipo de inversión
- Análisis temporal por categoría

#### Por Período:

- **Diario**: Movimientos día por día
- **Semanal**: Resumen semanal
- **Mensual**: Consolidado mensual
- **Anual**: Totales anuales

### 5. **Dashboard de Inversiones**

- Resumen general del período
- Gráficos de balance mensual
- Distribución por categorías (gráfico de pie)
- ROI promedio
- Top inversiones con mejor rendimiento

## 🏗️ Arquitectura Técnica

### Modelos de Datos

#### CatInversion

```python
- id (AutoField)
- nombre (CharField, unique)
- descripcion (TextField)
- activa (BooleanField)
- fecha_registro (DateTimeField)
```

#### Inversion

```python
- id_sucursal (ForeignKey → Sucursal)
- id_cat_inversion (ForeignKey → CatInversion)
- id_cuenta_banco (ForeignKey → Cuenta)
- tipo_movimiento (ENTRADA/SALIDA)
- monto (MoneyField)
- fecha (DateField)
- descripcion (TextField)
- notas (TextField)
- documento_soporte (FileField)
- fecha_registro (DateTimeField)
- ultima_modificacion (DateTimeField)
```

#### RendimientoInversion

```python
- inversion (ForeignKey → Inversion)
- fecha_rendimiento (DateField)
- monto_rendimiento (MoneyField)
- porcentaje_rendimiento (DecimalField) - Calculado automáticamente
- tipo_rendimiento (CharField)
- descripcion (TextField)
- fecha_registro (DateTimeField)
```

### Servicios

#### InversionesReportService

Hereda de `BaseReportService` y proporciona:

**Métodos principales:**

- `get_balance_por_sucursal()` - Balance entradas/salidas por sucursal
- `get_balance_por_categoria()` - Balance por categoría
- `get_inversiones_con_rendimientos()` - Inversiones con ROI
- `get_resumen_general()` - Estadísticas generales
- `get_accumulated_report()` - Reportes acumulados por período

### Vistas y URLs

**URLs disponibles:**

- `/capital-inversiones/dashboard/` - Dashboard principal
- `/capital-inversiones/reporte/sucursal/` - Reporte por sucursal
- `/capital-inversiones/reporte/categoria/` - Reporte por categoría
- `/capital-inversiones/reporte/rendimientos/` - Análisis de rendimientos
- `/capital-inversiones/api/balance-mensual/` - API para gráficos
- `/capital-inversiones/api/distribucion-categorias/` - API distribución

## 📦 Instalación y Configuración

### 1. Aplicar Migraciones

```powershell
python manage.py makemigrations capital_inversiones
python manage.py migrate capital_inversiones
```

### 2. Cargar Categorías Predeterminadas

```powershell
python manage.py cargar_categorias_inversiones
```

Este comando carga las 10 categorías predefinidas en la base de datos.

### 3. Verificar Instalación

Acceder al panel de administración:

- http://localhost:8000/admin/capital_inversiones/

Deberías ver tres secciones:

- Categorías de Inversión
- Inversiones y Capital
- Rendimientos de Inversiones

## 🔧 Uso del Sistema

### Registrar una Inversión

1. Ir a **Admin → Capital e Inversiones → Inversiones**
2. Hacer clic en "Agregar Inversión"
3. Completar el formulario:
   - Seleccionar sucursal
   - Elegir categoría
   - Seleccionar cuenta bancaria
   - Tipo de movimiento (Entrada/Salida)
   - Ingresar monto
   - Fecha del movimiento
   - Descripción y notas
   - Adjuntar documento (opcional)
4. Guardar

### Registrar Rendimientos

**Opción 1 - Desde la inversión:**

1. Abrir la inversión existente
2. En la sección "Rendimientos de Inversión" al final del formulario
3. Agregar fila con los datos del rendimiento
4. El porcentaje se calcula automáticamente

**Opción 2 - Directamente:**

1. Ir a **Admin → Capital e Inversiones → Rendimientos**
2. Crear nuevo rendimiento
3. Seleccionar la inversión relacionada
4. Ingresar datos del rendimiento

### Generar Reportes

#### Reporte por Sucursal:

```
/capital-inversiones/reporte/sucursal/?fecha_inicio=2024-01-01&fecha_fin=2024-12-31&periodo=mensual
```

#### Reporte por Categoría:

```
/capital-inversiones/reporte/categoria/?fecha_inicio=2024-01-01&fecha_fin=2024-12-31&periodo=mensual
```

#### Dashboard:

```
/capital-inversiones/dashboard/
```

## 📊 Integración con Otros Módulos

### Relaciones con módulos existentes:

**Catalogo:**

- Usa el modelo `Sucursal` para asociar inversiones

**Gastos:**

- Usa el modelo `Cuenta` (cuentas bancarias)
- Comparte la arquitectura de reportes (`BaseReportService`)

**App (servicios):**

- Hereda de `BaseReportService`
- Usa `FilterBuilder`, `PeriodAggregator`, etc.

## 🎨 Interfaz de Administración

### Características del Admin:

**CatInversion:**

- Lista con filtros por activa/inactiva
- Búsqueda por nombre
- Importar/Exportar (Excel, CSV)

**Inversion:**

- Badge de color según tipo de movimiento
  - Verde (↓) para ENTRADA
  - Rojo (↑) para SALIDA
- Indicador de documento adjunto
- Contador de rendimientos
- Filtros avanzados por sucursal, categoría, fecha
- Jerarquía por fecha
- Acciones masivas: marcar como entrada/salida
- Inline de rendimientos

**RendimientoInversion:**

- Link directo a la inversión relacionada
- Porcentaje formateado con color
- Cálculo automático de ROI
- Filtros por tipo de rendimiento

## 📈 Casos de Uso Comunes

### 1. Inversión en Activos Fijos

```
Tipo: SALIDA
Categoría: Activos Fijos
Monto: $500,000.00 MXN
Descripción: Compra de maquinaria para producción
Documento: Factura y contrato adjuntos
```

### 2. Aportación de Socios

```
Tipo: ENTRADA
Categoría: Aportación de Socios
Monto: $1,000,000.00 MXN
Descripción: Aportación de capital por socio mayoritario
```

### 3. Inversión Financiera con Rendimientos

```
Inversión:
  Tipo: SALIDA
  Categoría: Inversión Financiera
  Monto: $200,000.00 MXN
  Descripción: Compra de CETES 28 días

Rendimiento (después de 28 días):
  Monto: $2,100.00 MXN
  Tipo: Interés
  ROI calculado automáticamente: 1.05%
```

## 🔐 Permisos y Seguridad

El módulo respeta el sistema de permisos de Django:

- `capital_inversiones.view_catinversion`
- `capital_inversiones.add_catinversion`
- `capital_inversiones.change_catinversion`
- `capital_inversiones.delete_catinversion`
- `capital_inversiones.view_inversion`
- `capital_inversiones.add_inversion`
- `capital_inversiones.change_inversion`
- `capital_inversiones.delete_inversion`
- `capital_inversiones.view_rendimientoinversion`
- `capital_inversiones.add_rendimientoinversion`
- `capital_inversiones.change_rendimientoinversion`
- `capital_inversiones.delete_rendimientoinversion`

## 🧪 Testing

Ejecutar los tests del módulo:

```powershell
python manage.py test capital_inversiones
```

Tests incluidos:

- Creación de categorías
- Creación de inversiones
- Cálculo automático de ROI
- Validaciones de datos

## 📊 Exportación de Datos

Todos los modelos tienen soporte completo para Import/Export:

**Formatos soportados:**

- Excel (XLSX)
- CSV
- JSON
- YAML
- TSV
- ODS

**Widgets personalizados:**

- MoneyWidget para campos de monto
- ForeignKeyWidget para relaciones

## 🚀 Ventajas de la Arquitectura Elegida

### ✅ Tabla de Categorías Separada

**Ventajas:**

1. **Separación semántica**: Categorías de inversión vs gastos operativos
2. **Escalabilidad**: Agregar campos específicos sin afectar gastos
3. **Integridad**: No mezclar conceptos diferentes
4. **Flexibilidad**: Reglas de negocio independientes
5. **Mantenibilidad**: Cambios aislados por módulo

### ✅ Arquitectura Basada en Servicios

**Beneficios:**

- Reutilización de código (hereda de BaseReportService)
- Facilita testing
- Lógica de negocio centralizada
- Fácil extensión de funcionalidades

### ✅ Modelo de Rendimientos Separado

**Razones:**

- Una inversión puede tener múltiples rendimientos
- Facilita análisis histórico de ROI
- Permite diferentes tipos de rendimiento
- Mejor trazabilidad

## 🔮 Posibles Extensiones Futuras

1. **Dashboard interactivo con gráficos en tiempo real**
2. **Alertas de vencimiento de inversiones**
3. **Proyecciones de rendimiento**
4. **Comparación con benchmarks**
5. **Integración con APIs de mercados financieros**
6. **Generación automática de reportes PDF**
7. **Notificaciones de rendimientos**

## 📞 Soporte

Para dudas o problemas con el módulo, revisar:

- Logs en `logs/`
- Tests en `capital_inversiones/tests.py`
- Documentación de servicios en `capital_inversiones/services/`

---

**Versión:** 1.0.0  
**Fecha:** Octubre 2025  
**Autor:** Sistema de Capital e Inversiones - Django Custom Admin
