#!/usr/bin/env python
"""
Script de prueba rápida para verificar estructura de categorías sugeridas
"""

# Simulación de una categoria_sugerida tal como la genera el servicio
categoria_sugerida = {
    'id': 46,  # Ahora es entero
    'nombre': 'Vehículos y Transporte'
}

# Simulación de categorías de Django
class MockCategoria:
    def __init__(self, id, nombre):
        self.id = id
        self.nombre = nombre

categorias_django = [
    MockCategoria(13, 'Alimentación'),
    MockCategoria(46, 'Vehículos y Transporte'),
    MockCategoria(54, 'Servicios Financieros'),
]

print("=== PROBANDO COMPARACIÓN DE CATEGORÍAS ===")
print(f"Categoría sugerida por IA: {categoria_sugerida}")
print()

for categoria in categorias_django:
    es_seleccionada = categoria.id == categoria_sugerida['id']
    estado = "SELECCIONADA" if es_seleccionada else "no seleccionada"
    print(f"Categoría Django ID {categoria.id} ({categoria.nombre}): {estado}")
    
    if es_seleccionada:
        print(f"  ✅ Esta categoría debería aparecer como 'selected' en el dropdown")
        print(f"  ✅ Mostrará: '{categoria.nombre} (Sugerida por IA)'")

print()
print("=== RESULTADO ESPERADO ===")
print("- El dropdown debería mostrar 'Vehículos y Transporte' como seleccionado")
print("- Debería tener fondo verde (bg-green-50)")
print("- Debería mostrar el badge 'IA' en la esquina")
print("- Debería mostrar '✨ Vehículos y Transporte' debajo del select")
