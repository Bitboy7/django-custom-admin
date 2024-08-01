from django.test import TestCase
from django.utils import timezone
from .models import Gastos, CatGastos
from .forms import GastoForm

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
