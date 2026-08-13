from django.http import QueryDict
from django.test import SimpleTestCase

from ventas.views import _parse_selected_months


class VentasBalanceMonthFilterTests(SimpleTestCase):
    def test_accepts_comma_separated_months_from_frontend(self):
        params = QueryDict('months=1%2C3%2C12')

        self.assertEqual(_parse_selected_months(params), ['1', '3', '12'])

    def test_accepts_repeated_parameters_and_ignores_invalid_values(self):
        params = QueryDict('months=2&months=2%2C5&months=0%2C13%2Ctexto')

        self.assertEqual(_parse_selected_months(params), ['2', '5'])