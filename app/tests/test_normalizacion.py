#!/usr/bin/env python
"""
Script de prueba para verificar la normalización de montos
"""

def normalizar_monto(monto_str):
    """Convierte formato de número con coma a formato con punto para float"""
    if isinstance(monto_str, str):
        # Remover espacios y signos de moneda
        monto_limpio = monto_str.strip().replace('$', '').replace(' ', '')
        
        # Si contiene solo números, punto y/o signo negativo, ya está en formato correcto
        if ',' not in monto_limpio:
            return monto_limpio
        
        # Determinar si la coma es separador decimal o de miles
        # Si hay punto Y coma, la coma probablemente es decimal
        if '.' in monto_limpio and ',' in monto_limpio:
            # Formato como 1.234,56 - punto para miles, coma para decimales
            partes = monto_limpio.split(',')
            if len(partes) == 2:
                parte_entera = partes[0].replace('.', '')  # Remover puntos de miles
                parte_decimal = partes[1]
                monto_limpio = f"{parte_entera}.{parte_decimal}"
        else:
            # Solo hay comas, probablemente es separador decimal
            monto_limpio = monto_limpio.replace(',', '.')
        
        return monto_limpio
    return monto_str

def test_normalizacion():
    print("=== PROBANDO NORMALIZACIÓN DE MONTOS ===")
    print("Casos específicos del error reportado:")
    
    casos_error = [
        "-5986,81",  # Error reportado
        "-3000,0",   # Error reportado
    ]
    
    for caso in casos_error:
        try:
            normalizado = normalizar_monto(caso)
            como_float = float(normalizado)
            print(f"✅ '{caso}' → '{normalizado}' → {como_float}")
        except Exception as e:
            print(f"❌ '{caso}' → ERROR: {e}")
    
    print("\nOtros casos de prueba:")
    casos_adicionales = [
        "$-239,00",
        "1.234,56",
        "12.345.678,90",
        "-1000",
        "500.25",
        "1,234.56",  # Formato americano
        "1.234.567,89"  # Formato europeo
    ]
    
    for caso in casos_adicionales:
        try:
            normalizado = normalizar_monto(caso)
            como_float = float(normalizado)
            print(f"✅ '{caso}' → '{normalizado}' → {como_float}")
        except Exception as e:
            print(f"❌ '{caso}' → ERROR: {e}")

if __name__ == "__main__":
    test_normalizacion()
