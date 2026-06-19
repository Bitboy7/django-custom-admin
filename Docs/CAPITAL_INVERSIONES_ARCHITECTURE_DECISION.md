# Decisión de Arquitectura: Tabla de Categorías Separada

## 🎯 Contexto

El cliente solicitó un módulo para manejar **Capital e Inversiones** con funcionalidad similar a **Gastos**, incluyendo:

- Sistema de categorías
- Reportes acumulados por sucursal, día, mes, año
- Misma arquitectura de servicios

**Pregunta clave:** ¿Reutilizar la tabla de categorías de Gastos (`CatGastos`) o crear una nueva tabla (`CatInversion`)?

## ✅ Decisión: Tabla de Categorías Separada

Se decidió crear **`CatInversion`** como una tabla independiente de **`CatGastos`**.

---

## 📊 Análisis Comparativo

### Opción 1: Reutilizar `CatGastos` ❌

**Ventajas:**

- ✓ Menos tablas en la base de datos
- ✓ Código ligeramente más simple
- ✓ No requiere crear nuevos modelos

**Desventajas:**

- ✗ **Mezcla conceptual**: Gastos operativos ≠ Inversiones de capital
- ✗ **Baja cohesión semántica**: "Limpieza" y "Inversión en acciones" en la misma tabla
- ✗ **Rigidez futura**: No se pueden agregar campos específicos para inversiones
- ✗ **Complejidad de validación**: Necesitaría lógica para separar tipos
- ✗ **Reportes confusos**: Categorías mezcladas dificultan análisis
- ✗ **Alto acoplamiento**: Cambios en una afectan a la otra

### Opción 2: Tabla Separada `CatInversion` ✅

**Ventajas:**

- ✓ **Separación clara de responsabilidades**
- ✓ **Alta cohesión semántica**: Cada tabla tiene un propósito único
- ✓ **Escalabilidad**: Se pueden agregar campos específicos sin afectar gastos
- ✓ **Integridad de datos**: No se pueden mezclar categorías incorrectas
- ✓ **Flexibilidad**: Reglas de negocio independientes por módulo
- ✓ **Mantenibilidad**: Cambios aislados, menos riesgo de efectos secundarios
- ✓ **Mejor UX**: Usuarios ven solo categorías relevantes en cada contexto

**Desventajas:**

- ✗ Una tabla adicional en la base de datos (impacto mínimo)

---

## 🏗️ Principios de Diseño Aplicados

### 1. **Single Responsibility Principle (SRP)**

Cada modelo tiene una única responsabilidad clara:

- `CatGastos` → Categorizar gastos operativos
- `CatInversion` → Categorizar inversiones de capital

### 2. **Domain-Driven Design (DDD)**

Los conceptos del negocio están claramente separados:

- **Dominio de Gastos**: Operaciones diarias, costos recurrentes
- **Dominio de Inversiones**: Capital, activos, rendimientos a largo plazo

### 3. **Low Coupling, High Cohesion**

- **Bajo acoplamiento**: Cambios en gastos no afectan inversiones
- **Alta cohesión**: Cada módulo agrupa conceptos relacionados

### 4. **Open/Closed Principle**

Abierto a extensión, cerrado a modificación:

- Se puede extender `CatInversion` sin tocar `CatGastos`

---

## 📈 Ejemplos Concretos

### Categorías de Gastos (CatGastos)

```
- Nomina
- Servicios públicos
- Mantenimiento
- Limpieza
- Papelería
- Transporte
- Marketing
```

### Categorías de Inversión (CatInversion)

```
- Capital de trabajo
- Activos fijos
- Inversión financiera
- Inversión inmobiliaria
- Reinversión de utilidades
- Aportación de socios
- Investigación y desarrollo
```

**¿Tendría sentido mezclarlas?** ❌ **NO**

---

## 🔮 Escalabilidad Futura

### Escenario: Agregar campo "Tipo de Riesgo" a inversiones

**Con tabla compartida:**

```python
class CatGastos(models.Model):
    nombre = models.CharField(max_length=50)
    tipo_riesgo = models.CharField(...)  # ¿Para gastos también? ❌
    # O agregar validaciones complejas para saber cuándo aplicar
```

**Con tabla separada:**

```python
class CatInversion(models.Model):
    nombre = models.CharField(max_length=100)
    tipo_riesgo = models.CharField(...)  # Solo aplica aquí ✅
    rendimiento_esperado = models.DecimalField(...)
    plazo = models.CharField(...)
```

### Escenario: Reportes específicos de inversiones

**Con tabla separada:**

```python
# Fácil filtrar solo categorías de inversión
inversiones = Inversion.objects.filter(
    id_cat_inversion__activa=True
)

# Sin riesgo de incluir categorías de gastos
```

---

## 🎨 Impacto en la Base de Datos

### Estructura Final

```
┌──────────────────┐
│   CatGastos      │
├──────────────────┤
│ id               │
│ nombre           │
│ fecha_registro   │
└──────────────────┘
        ↑
        │
        │ FK
        │
┌──────────────────┐
│     Gastos       │
├──────────────────┤
│ id               │
│ id_cat_gastos    │───┐
│ ...              │   │
└──────────────────┘   │
                       │
                       │ NO HAY RELACIÓN
                       │
┌──────────────────┐   │
│  CatInversion    │   │
├──────────────────┤   │
│ id               │   │
│ nombre           │   │
│ descripcion      │   │
│ activa           │   │
└──────────────────┘   │
        ↑              │
        │              │
        │ FK           │
        │              │
┌──────────────────┐   │
│   Inversion      │   │
├──────────────────┤   │
│ id               │   │
│ id_cat_inversion │───┘
│ ...              │
└──────────────────┘
```

### Costo de Almacenamiento

**Ejemplo con 100 categorías totales:**

**Opción compartida:**

```
CatGastos: 100 categorías × ~100 bytes = 10 KB
```

**Opción separada:**

```
CatGastos: 60 categorías × ~100 bytes = 6 KB
CatInversion: 40 categorías × ~150 bytes = 6 KB
Total: 12 KB
```

**Diferencia:** ~2 KB → **Despreciable** en bases de datos modernas

---

## 🧪 Testing y Mantenibilidad

### Con tabla separada:

```python
# Test aislado para inversiones
def test_categoria_inversion_valida():
    cat = CatInversion.objects.create(
        nombre="Capital de Trabajo",
        descripcion="..."
    )
    # No hay riesgo de conflicto con CatGastos

# Test aislado para gastos
def test_categoria_gasto_valida():
    cat = CatGastos.objects.create(
        nombre="Limpieza"
    )
    # Completamente independiente
```

### Con tabla compartida:

```python
# Test debe considerar ambos tipos
def test_categoria_valida():
    # ¿Es para gasto o inversión?
    # ¿Qué campos son obligatorios?
    # Mayor complejidad
```

---

## 📚 Referencias de Buenas Prácticas

### Libros y Conceptos:

1. **"Clean Code" - Robert C. Martin**
   - _Principio de Responsabilidad Única_
2. **"Domain-Driven Design" - Eric Evans**
   - _Separación de bounded contexts_
3. **"Design Patterns" - Gang of Four**
   - _Alta cohesión, bajo acoplamiento_

### Análogos en Software Popular:

**Django Admin:**

- `auth.Group` vs `auth.Permission` (separados)
- No mezcla usuarios con grupos

**WordPress:**

- `wp_posts` vs `wp_comments` (separados)
- No mezcla contenido con comentarios

**E-commerce:**

- `Products` vs `Orders` (separados)
- No mezcla productos con pedidos, aunque están relacionados

---

## 💡 Conclusión

La decisión de crear **`CatInversion`** como tabla separada se basa en:

1. **Principios SOLID** ✅
2. **Domain-Driven Design** ✅
3. **Escalabilidad futura** ✅
4. **Mantenibilidad** ✅
5. **Separación de responsabilidades** ✅
6. **Mejores prácticas de la industria** ✅

**Costo adicional:**

- ~1 tabla adicional
- ~2 KB de almacenamiento
- ~50 líneas de código extra

**Beneficios:**

- Código más limpio y mantenible
- Fácil de extender sin efectos secundarios
- Mejor experiencia de usuario
- Reportes más claros
- Testing más simple
- Menor riesgo de bugs

## 🎓 Lección Aprendida

> "A veces lo que parece una optimización (reutilizar tablas) se convierte en deuda técnica. La separación clara de responsabilidades es una inversión en el futuro del código."

---

**Decisión aprobada:** ✅ Tabla separada `CatInversion`  
**Fecha:** Octubre 2025  
**Principio aplicado:** _"Make it work, make it right, make it fast"_ - Kent Beck
