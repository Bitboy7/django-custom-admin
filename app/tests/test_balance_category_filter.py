from django.test import SimpleTestCase

from app.services.balance_service import BalanceAnalysisService


class BalanceCategoryFilterTests(SimpleTestCase):
    def setUp(self):
        self.service = BalanceAnalysisService()

    def test_categoria_id_maps_to_id_cat_gastos_id(self):
        filters = self.service.build_filters(
            categoria_id='7',
            periodo='diario',
        )

        self.assertEqual(filters.get('id_cat_gastos_id'), 7)
        self.assertNotIn('id_categoria_id', filters)

    def test_categoria_id_invalido_se_ignora(self):
        filters = self.service.build_filters(
            categoria_id='no-es-id',
            periodo='diario',
        )

        self.assertNotIn('id_cat_gastos_id', filters)

    def test_sin_categoria_no_aplica_filtro(self):
        filters = self.service.build_filters(
            periodo='diario',
        )

        self.assertNotIn('id_cat_gastos_id', filters)
