from django.test import TestCase, SimpleTestCase
from django.utils import timezone
from .models import Gastos, CatGastos
from .forms import GastoForm
from app.services.balance_service import BalanceAnalysisService

class GastosModelTest(TestCase):
	def setUp(self):
		self.cat_gastos = CatGastos.objects.create(nombre="Transporte")
		self.gasto = Gastos.objects.create(
			monto=100.0,
			fecha_registro=timezone.now(),
			descripcion="Taxi",
			id_cat_gastos=self.cat_gastos
		)

	def test_gastos_creation(self):
		self.assertTrue(isinstance(self.gasto, Gastos))
		self.assertEqual(self.gasto.__str__(), self.gasto.descripcion)

class GastoFormTest(TestCase):
	def test_valid_form(self):
		cat_gastos = CatGastos.objects.create(nombre="Transporte")
		data = {
			'monto': 100.0,
			'fecha_registro': timezone.now(),
			'descripcion': "Taxi",
			'id_cat_gastos': cat_gastos.id
		}
		form = GastoForm(data=data)
		self.assertTrue(form.is_valid())

	def test_invalid_form(self):
		data = {
			'monto': '',
			'fecha_registro': '',
			'descripcion': '',
			'id_cat_gastos': ''
		}
		form = GastoForm(data=data)
		self.assertFalse(form.is_valid())


class BalanceAnalysisAccumulationTest(SimpleTestCase):
	def setUp(self):
		self.service = BalanceAnalysisService()
		self.balances = [
			{'id_sucursal__nombre': 'Norte', 'id_cat_gastos__nombre': 'Transporte', 'total_gastos': 100},
			{'id_sucursal__nombre': 'Norte', 'id_cat_gastos__nombre': 'Renta', 'total_gastos': 50},
			{'id_sucursal__nombre': 'Sur', 'id_cat_gastos__nombre': 'Transporte', 'total_gastos': 30},
			{'id_sucursal__nombre': None, 'id_cat_gastos__nombre': None, 'total_gastos': 20},
		]

	def test_accumulated_by_category(self):
		result = self.service.get_accumulated_by_category(self.balances)
		self.assertEqual(result[0], {'categoria': 'Transporte', 'total': 130.0})
		self.assertEqual(
			sum(item['total'] for item in result),
			200.0,
		)

	def test_accumulated_by_category_per_sucursal(self):
		result = self.service.get_accumulated_by_category_per_sucursal(self.balances)
		self.assertEqual(result['sucursales'], ['Norte', 'Sin sucursal', 'Sur'])
		self.assertEqual(result['categorias'], ['Renta', 'Sin categoría', 'Transporte'])
		self.assertEqual(result['matrix'][('Norte', 'Transporte')], 100.0)
		self.assertEqual(result['matrix'][('Sin sucursal', 'Sin categoría')], 20.0)
