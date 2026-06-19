from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from .models import CatInversion, Inversion, RendimientoInversion
from catalogo.models import Sucursal, Estado, Pais
from gastos.models import Cuenta, Banco


class CatInversionModelTest(TestCase):
    """Tests para el modelo CatInversion"""
    
    def setUp(self):
        self.categoria = CatInversion.objects.create(
            nombre="Capital de Trabajo",
            descripcion="Inversión en capital operativo"
        )
    
    def test_categoria_creacion(self):
        """Test de creación de categoría"""
        self.assertEqual(self.categoria.nombre, "Capital de Trabajo")
        self.assertTrue(self.categoria.activa)
    
    def test_categoria_str(self):
        """Test del método __str__"""
        self.assertEqual(str(self.categoria), "Capital de Trabajo")


class InversionModelTest(TestCase):
    """Tests para el modelo Inversion"""
    
    def setUp(self):
        # Crear datos necesarios
        pais = Pais.objects.create(siglas="MX", nombre="México")
        estado = Estado.objects.create(id="JAL", nombre="Jalisco", pais=pais)
        self.sucursal = Sucursal.objects.create(
            nombre="Sucursal Centro",
            id_estado=estado
        )
        
        banco = Banco.objects.create(nombre="Banco Test")
        self.cuenta = Cuenta.objects.create(
            id_banco=banco,
            id_sucursal=self.sucursal,
            numero_cuenta="1234567890"
        )
        
        self.categoria = CatInversion.objects.create(
            nombre="Inversión Financiera"
        )
        
        self.inversion = Inversion.objects.create(
            id_sucursal=self.sucursal,
            id_cat_inversion=self.categoria,
            id_cuenta_banco=self.cuenta,
            tipo_movimiento='SALIDA',
            monto=100000.00,
            descripcion="Inversión en acciones"
        )
    
    def test_inversion_creacion(self):
        """Test de creación de inversión"""
        self.assertEqual(self.inversion.tipo_movimiento, 'SALIDA')
        self.assertEqual(float(self.inversion.monto.amount), 100000.00)
    
    def test_inversion_str(self):
        """Test del método __str__"""
        expected = f"SALIDA - {self.sucursal.nombre} - {self.categoria.nombre} - MXN 100,000.00"
        self.assertIn("SALIDA", str(self.inversion))


class RendimientoInversionModelTest(TestCase):
    """Tests para el modelo RendimientoInversion"""
    
    def setUp(self):
        # Crear inversión
        pais = Pais.objects.create(siglas="MX", nombre="México")
        estado = Estado.objects.create(id="JAL", nombre="Jalisco", pais=pais)
        sucursal = Sucursal.objects.create(nombre="Sucursal Test", id_estado=estado)
        
        banco = Banco.objects.create(nombre="Banco Test")
        cuenta = Cuenta.objects.create(
            id_banco=banco,
            id_sucursal=sucursal,
            numero_cuenta="9876543210"
        )
        
        categoria = CatInversion.objects.create(nombre="Inversión Test")
        
        self.inversion = Inversion.objects.create(
            id_sucursal=sucursal,
            id_cat_inversion=categoria,
            id_cuenta_banco=cuenta,
            tipo_movimiento='SALIDA',
            monto=50000.00
        )
    
    def test_rendimiento_calculo_automatico(self):
        """Test de cálculo automático de porcentaje de rendimiento"""
        rendimiento = RendimientoInversion.objects.create(
            inversion=self.inversion,
            monto_rendimiento=5000.00,  # 10% de rendimiento
            tipo_rendimiento="Dividendo"
        )
        
        # El porcentaje debería calcularse automáticamente
        self.assertIsNotNone(rendimiento.porcentaje_rendimiento)
        self.assertEqual(float(rendimiento.porcentaje_rendimiento), 10.0)
