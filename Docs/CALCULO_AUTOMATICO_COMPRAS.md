# Cálculo automático de monto total en formularios de compra

## Descripción

Esta funcionalidad permite calcular automáticamente el monto total de una compra multiplicando la cantidad por el precio unitario cuando el usuario ingresa estos valores en el formulario.

## Características implementadas

### 1. JavaScript automático (`compra_calculator.js`)

- Detecta campos de cantidad, precio unitario y monto total
- Calcula automáticamente: `monto_total = cantidad × precio_unitario`
- Funciona en múltiples contextos (admin de Django, formularios personalizados)
- Incluye validación de entrada y efectos visuales
- Observer de mutaciones para formularios dinámicos

### 2. Formulario mejorado (`CompraForm`)

- Campo `monto_total` configurado como solo lectura
- Validación automática en el método `clean()`
- Cálculo automático en el método `save()`
- IDs específicos para mejor compatibilidad con JavaScript

### 3. Modelo actualizado (`Compra`)

- Método `save()` sobrescrito para garantizar cálculo correcto
- Validación a nivel de modelo

### 4. Estilos CSS personalizados

- Campo calculado con fondo especial
- Efectos visuales para indicar cálculos
- Tooltips informativos

## Uso

### En el admin de Django

1. Ir a Admin > Compras > Agregar compra
2. Ingresar cantidad (ej: 100)
3. Ingresar precio unitario (ej: 25.50)
4. El monto total se calculará automáticamente (2,550.00)

### En formularios personalizados

El JavaScript se carga automáticamente y detecta campos con nombres:

- `cantidad`, `precio_unitario`, `monto_total`
- O IDs que contengan estas palabras

## Archivos modificados

- `gastos/forms.py` - CompraForm mejorado
- `gastos/models.py` - Modelo Compra con save() automático
- `gastos/admin.py` - Incluir JavaScript y CSS
- `static/js/compra_calculator.js` - Nueva calculadora
- `static/js/scripts.js` - JavaScript mejorado
- `static/css/admin_custom.css` - Estilos personalizados
- `templates/_base.html` - Incluir script globalmente

## Ventajas

1. **Automatización**: Elimina errores de cálculo manual
2. **Usabilidad**: Feedback inmediato al usuario
3. **Consistencia**: Funciona en diferentes contextos
4. **Validación**: Multiple niveles de validación
5. **Accesibilidad**: Tooltips y indicadores visuales

## Compatibilidad

- Django Admin
- Formularios personalizados
- Formularios dinámicos (AJAX)
- Dispositivos móviles (responsive)
