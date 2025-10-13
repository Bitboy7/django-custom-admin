# Templates HTML - Módulo Capital e Inversiones

## 📁 Archivos Creados

```
templates/capital_inversiones/
├── dashboard.html                          # Dashboard principal
├── reporte_acumulado_sucursal.html        # Reporte por sucursal
├── reporte_acumulado_categoria.html       # Reporte por categoría
└── reporte_rendimientos.html              # Análisis de rendimientos
```

## 🎨 Características de los Templates

### ✅ Tecnologías Utilizadas

- **Tailwind CSS**: Framework CSS utility-first
- **Font Awesome 6**: Iconos
- **Chart.js 4**: Gráficos interactivos
- **DataTables**: Tablas con búsqueda, ordenamiento y exportación
- **jQuery**: Manipulación DOM
- **SweetAlert2**: Alertas elegantes

### ✅ Características Generales

**Responsive Design:**

- Mobile-first
- Grids adaptables
- Componentes responsivos

**Interactividad:**

- Gráficos dinámicos
- Tablas con DataTables
- Filtros en tiempo real
- Exportación a Excel/PDF

**UX/UI:**

- Cards con hover effects
- Gradientes modernos
- Badges de colores
- Iconos contextuales
- Animaciones suaves

---

## 📊 Dashboard Principal (`dashboard.html`)

### Secciones:

1. **Filtros de Fecha**

   - Rango de fechas personalizado
   - Botón de limpiar filtros

2. **Tarjetas de Estadísticas**

   - Total Entradas (verde)
   - Total Salidas (rojo)
   - Balance Neto (azul)
   - Total Movimientos (morado)

3. **Gráficos**

   - Balance Mensual (líneas) - Últimos 12 meses
   - Distribución por Categoría (donut/pie)

4. **Tablas**

   - Balance por Sucursal
   - Balance por Categoría
   - Top Inversiones con Rendimientos

5. **Botones de Acción**
   - Nueva Inversión
   - Reportes
   - Ver Admin

### APIs Utilizadas:

- `/api/balance-mensual/` - Datos para gráfico de líneas
- `/api/distribucion-categorias/` - Datos para gráfico de pie

---

## 🏢 Reporte por Sucursal (`reporte_acumulado_sucursal.html`)

### Características:

1. **Filtros Avanzados**

   - Fecha inicio/fin
   - Selector de sucursal
   - Período (diario, semanal, mensual, anual)

2. **Cards de Resumen**

   - Totales por sucursal
   - Cantidad de movimientos

3. **Tabla DataTable**

   - Búsqueda
   - Ordenamiento
   - Paginación
   - Exportación a Excel/CSV

4. **Badges de Tipo**
   - Verde para ENTRADA
   - Rojo para SALIDA

---

## 🏷️ Reporte por Categoría (`reporte_acumulado_categoria.html`)

### Características:

1. **Filtros**

   - Fecha inicio/fin
   - Selector de categoría
   - Período

2. **Cards de Categorías**

   - Diseño tipo "card flip"
   - Hover effects
   - Entradas/Salidas/Balance por categoría

3. **Tabla Detallada**

   - DataTable con búsqueda
   - Badges de categoría (morado)
   - Iconos de tipo de movimiento

4. **Gráfico de Barras**
   - Balance por categoría
   - Chart.js interactivo

---

## 💰 Análisis de Rendimientos (`reporte_rendimientos.html`)

### Características:

1. **Tarjetas de Resumen**

   - Total Invertido
   - Total Rendimientos
   - ROI Promedio

2. **Cards de Inversiones**

   - Badge de ROI (verde positivo, rojo negativo)
   - Información detallada
   - Historial de rendimientos
   - Link a detalle

3. **Gráfico de ROI**

   - Barras horizontales
   - Colores según ROI (verde/rojo)
   - Chart.js

4. **Tabla Resumen**
   - ROI por inversión
   - Estado de rendimientos
   - Links a edición

---

## 🎨 Paleta de Colores

```
Entradas/Positivo:   #10b981 (green-500)
Salidas/Negativo:    #ef4444 (red-500)
Balance/Neutro:      #3b82f6 (blue-500)
Categorías:          #8b5cf6 (purple-500)
Rendimientos:        #eab308 (yellow-500)
Sucursales:          #10b981 (green-500)
```

---

## 📱 Responsive Breakpoints

```css
sm:  640px
md:  768px
lg:  1024px
xl:  1280px
2xl: 1536px
```

---

## 🔧 Personalización

### Cambiar Colores:

Buscar en los templates:

```html
<!-- Verde -->
bg-green-500, text-green-600, border-green-500

<!-- Rojo -->
bg-red-500, text-red-600, border-red-500

<!-- Azul -->
bg-blue-500, text-blue-600, border-blue-500
```

### Modificar Gráficos:

Editar las opciones de Chart.js:

```javascript
options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { ... },
    scales: { ... }
}
```

---

## 📊 Integración con Backend

### Context Variables Esperadas:

**dashboard.html:**

```python
{
    'resumen': {
        'total_entradas': Decimal,
        'total_salidas': Decimal,
        'balance': Decimal,
        'cantidad_entradas': int,
        'cantidad_salidas': int,
        'total_movimientos': int
    },
    'balance_sucursales': QuerySet,
    'balance_categorias': QuerySet,
    'inversiones_rendimientos': QuerySet,
    'fecha_inicio': str,
    'fecha_fin': str
}
```

**reporte_acumulado_sucursal.html:**

```python
{
    'resultados': QuerySet,
    'periodo': str,
    'fecha_inicio': str,
    'fecha_fin': str,
    'sucursales': QuerySet,
    'sucursal_seleccionada': str
}
```

**reporte_acumulado_categoria.html:**

```python
{
    'resultados': QuerySet,
    'periodo': str,
    'fecha_inicio': str,
    'fecha_fin': str,
    'categorias': QuerySet,
    'categoria_seleccionada': str
}
```

**reporte_rendimientos.html:**

```python
{
    'inversiones': QuerySet,  # con anotaciones: total_rendimientos, cantidad_rendimientos, roi
    'total_invertido': Decimal,
    'total_rendimientos': Decimal,
    'roi_promedio': float,
    'fecha_inicio': str,
    'fecha_fin': str
}
```

---

## 🚀 Instalación y Uso

### 1. Asegurarse que las vistas están configuradas

Las vistas en `capital_inversiones/views.py` deben retornar el context correcto.

### 2. Verificar URLs

```python
# capital_inversiones/urls.py
urlpatterns = [
    path('dashboard/', views.dashboard_inversiones, name='dashboard'),
    path('reporte/sucursal/', views.reporte_acumulado_sucursal, name='reporte_sucursal'),
    path('reporte/categoria/', views.reporte_acumulado_categoria, name='reporte_categoria'),
    path('reporte/rendimientos/', views.reporte_rendimientos, name='reporte_rendimientos'),
    # APIs
    path('api/balance-mensual/', views.api_balance_mensual, name='api_balance_mensual'),
    path('api/distribucion-categorias/', views.api_distribucion_categorias, name='api_distribucion_categorias'),
]
```

### 3. Acceder a las URLs

```
http://localhost:8000/es/capital-inversiones/dashboard/
http://localhost:8000/es/capital-inversiones/reporte/sucursal/
http://localhost:8000/es/capital-inversiones/reporte/categoria/
http://localhost:8000/es/capital-inversiones/reporte/rendimientos/
```

---

## 🔗 Navegación Entre Páginas

Todos los templates incluyen botones de navegación en el footer:

- Dashboard
- Reporte por Sucursal
- Reporte por Categoría
- Análisis de Rendimientos
- Admin de Inversiones

---

## 📦 Dependencias CDN

```html
<!-- Tailwind CSS -->
<link
  rel="stylesheet"
  href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css"
/>

<!-- Font Awesome 6 -->
<link
  rel="stylesheet"
  href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
/>

<!-- Chart.js 4 -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>

<!-- jQuery 3.7 -->
<script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>

<!-- DataTables 1.13 -->
<link
  rel="stylesheet"
  href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.css"
/>
<script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>

<!-- DataTables Buttons -->
<link
  rel="stylesheet"
  href="https://cdn.datatables.net/buttons/2.4.1/css/buttons.dataTables.min.css"
/>
<script src="https://cdn.datatables.net/buttons/2.4.1/js/dataTables.buttons.min.js"></script>
<script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.html5.min.js"></script>

<!-- JSZip (para exportar Excel) -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>

<!-- SweetAlert2 -->
<script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
```

---

## ✅ Checklist de Verificación

- [x] Dashboard con gráficos interactivos
- [x] Filtros de fecha funcionales
- [x] Tablas con DataTables
- [x] Exportación a Excel
- [x] Responsive design
- [x] Badges de colores por tipo
- [x] Navegación entre páginas
- [x] Hover effects
- [x] Iconos Font Awesome
- [x] Context variables documentadas

---

## 🎯 Próximas Mejoras Sugeridas

1. **Modo Oscuro**

   - Implementar dark mode con Tailwind

2. **Más Gráficos**

   - Gráficos de tendencias
   - Comparativas año vs año
   - Proyecciones

3. **Filtros Avanzados**

   - Múltiples sucursales
   - Múltiples categorías
   - Rango de montos

4. **Exportación PDF**

   - Generar PDFs con reportes
   - Logo personalizado
   - Gráficos incluidos

5. **WebSockets**
   - Actualización en tiempo real
   - Notificaciones de nuevos rendimientos

---

**¡Templates Listos para Producción!** ✅

Los templates están completamente funcionales y listos para usar. Solo ejecuta las migraciones, carga los datos y accede a las URLs.
