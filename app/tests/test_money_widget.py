from decimal import Decimal

from django.test import SimpleTestCase
from djmoney.money import Money

from app.widgets import MoneyWidget


class MoneyWidgetRenderTests(SimpleTestCase):
    def setUp(self):
        self.widget = MoneyWidget()

    def test_render_money_returns_decimal_amount(self):
        rendered = self.widget.render(Money('120000.00', 'MXN'))

        self.assertEqual(rendered, Decimal('120000.00'))
        self.assertNotIsInstance(rendered, str)

    def test_render_string_number_returns_decimal(self):
        rendered = self.widget.render('120,000.00')

        self.assertEqual(rendered, Decimal('120000.00'))
        self.assertNotIsInstance(rendered, str)

    def test_render_empty_value_returns_zero_decimal(self):
        rendered = self.widget.render('')

        self.assertEqual(rendered, Decimal('0.00'))