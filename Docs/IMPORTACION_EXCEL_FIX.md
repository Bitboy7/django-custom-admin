# Guía de Importación/Exportación de Archivos Excel

## Problemas Solucionados: Errores de Conversión de Campos MoneyField

### Descripción de los Problemas

#### 1. Error de Importación: `decimal.ConversionSyntax`

Al intentar importar archivos Excel (.xlsx) que fueron exportados desde el mismo sistema admin, aparecían múltiples errores del tipo:

```
decimal.ConversionSyntax
```

#### 2. Error de Exportación: `TypeError` en `MoneyWidget.render()`

Al intentar exportar datos, aparecía el error:

```
TypeError: MoneyWidget.render() got an unexpected keyword argument 'export_fields'
```

### Causas de los Problemas

1. **Importación**: Los campos `MoneyField` se exportan como valores flotantes, pero al importar, django-import-export no podía convertir correctamente estos valores decimales de vuelta a objetos `Money`.

2. **Exportación**: El método `render()` del widget personalizado no aceptaba argumentos adicionales que django-import-export pasa automáticamente durante la exportación.

3. **Formato Excel**: Excel puede almacenar números con formatos específicos que no siempre son compatibles con la conversión directa de Python.

### Solución Implementada

#### 1. Widget Personalizado `MoneyWidget` Mejorado

Se creó un widget robusto en `app/widgets.py` que maneja la conversión bidireccional entre valores de Excel y objetos `Money`:

**Características:**

- **Limpieza de valores**: Remueve símbolos de moneda ($), comas, espacios
- **Validación robusta**: Maneja casos especiales como NaN, infinito, valores vacíos
- **Soporte múltiple**: Acepta strings, floats, ints, Decimals y objetos Money
- **Logging de errores**: Registra valores problemáticos para debugging
- **Fallback seguro**: Devuelve Money(0, 'MXN') en caso de error
- **Compatibilidad**: Acepta argumentos adicionales en el método `render()` usando `**kwargs`

#### 2. Actualización Completa de Resources

Se actualizaron todos los recursos de import-export para usar el widget personalizado:

**Archivos modificados:**

- `gastos/admin.py`:
  - `GastosResource` (campo `monto`)
  - `ComprasResource` (campos `precio_unitario`, `monto_total`)
  - `SaldoMensualResource` (campos `saldo_inicial`, `saldo_final`)
- `ventas/admin.py`:
  - `VentasResource` (campo `monto`)
  - `AnticiposResource` (campo `monto`)

#### 3. Mejora del Servicio de Exportación

#### 3. Mejora del Servicio de Exportación

Se mejoró `excel_service.py` para generar valores más limpios:

- Redondeo a 2 decimales
- Formato numérico consistente

#### 4. Fix del Error de Exportación

Se corrigió el método `render()` de `MoneyWidget` para aceptar argumentos adicionales:

- Agregado `**kwargs` para manejar argumentos como `export_fields`
- Mantiene compatibilidad con versiones futuras de django-import-export

### Campos Afectados

| Modelo       | Campo           | Tipo       | Widget      |
| ------------ | --------------- | ---------- | ----------- |
| Gastos       | monto           | MoneyField | MoneyWidget |
| Compra       | precio_unitario | MoneyField | MoneyWidget |
| Compra       | monto_total     | MoneyField | MoneyWidget |
| Ventas       | monto           | MoneyField | MoneyWidget |
| Anticipo     | monto           | MoneyField | MoneyWidget |
| SaldoMensual | saldo_inicial   | MoneyField | MoneyWidget |
| SaldoMensual | saldo_final     | MoneyField | MoneyWidget |

### Cómo Usar

1. **Exportar**: Usar la función de exportación normal del admin (ya no genera errores)
2. **Importar**: Los archivos Excel exportados ahora se pueden reimportar sin errores

### Validación

Para validar que funciona correctamente:

1. Exportar datos de cualquier modelo con campos MoneyField
2. Modificar algunos valores en el Excel exportado
3. Reimportar el archivo
4. Verificar que los datos se importen correctamente sin errores de conversión

### Errores Solucionados

#### Error de Importación

```
Número de línea: X - [<class 'decimal.ConversionSyntax'>]
```

**Estado**: ✅ **SOLUCIONADO**

#### Error de Exportación

```
TypeError: MoneyWidget.render() got an unexpected keyword argument 'export_fields'
```

**Estado**: ✅ **SOLUCIONADO**

### Logs y Debugging

Si hay problemas de conversión, el sistema registrará warnings en los logs:

```
No se puede convertir 'valor_problemático' (tipo: tipo) a Money: descripción_error
```

Estos logs ayudan a identificar valores específicos que causan problemas.

### Mejoras Futuras

1. **Formato de moneda**: Agregar soporte para múltiples monedas en importación
2. **Validación de rangos**: Agregar validación de rangos válidos para montos
3. **Formato personalizado**: Permitir configurar el formato de exportación por modelo
4. **Interfaz de usuario**: Mostrar mejores mensajes de error en la interfaz

### Notas Técnicas

- El widget usa `Decimal` internamente para evitar problemas de precisión de punto flotante
- Se utiliza regex para limpiar strings de manera más robusta
- El sistema es compatible con archivos Excel generados por otras aplicaciones
- Mantiene compatibilidad hacia atrás con datos existentes

### Testing

Para probar la funcionalidad:

```python
# Ejemplo de test
from app.widgets import MoneyWidget

widget = MoneyWidget()

# Test casos válidos
assert widget.clean("1234.56") == Money(Decimal("1234.56"), "MXN")
assert widget.clean(1234.56) == Money(Decimal("1234.56"), "MXN")
assert widget.clean("$1,234.56") == Money(Decimal("1234.56"), "MXN")

# Test casos problemáticos
assert widget.clean("") == Money(0, "MXN")
assert widget.clean("invalid") == Money(0, "MXN")
```
