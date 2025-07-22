from django.core.management.base import BaseCommand
from django.template import Template, Context
from django.template.loader import get_template
from decimal import Decimal


class Command(BaseCommand):
    help = 'Test US number formatting'

    def handle(self, *args, **options):
        # Test the custom template filter
        template_str = """
        {% load gastos_tags %}
        Test Numbers:
        {{ test_number|us_currency:2 }}
        {{ test_large_number|us_currency:2 }}
        {{ test_decimal|us_number:3 }}
        """
        
        template = Template(template_str)
        context = Context({
            'test_number': Decimal('1234.56'),
            'test_large_number': Decimal('1000000.789'),
            'test_decimal': Decimal('12345.6789')
        })
        
        result = template.render(context)
        self.stdout.write(self.style.SUCCESS('Number formatting test results:'))
        self.stdout.write(result)
        
        # Verify the expected format
        expected_results = [
            '1,234.56',     # Should use comma as thousand separator, period as decimal
            '1,000,000.79', # Should handle large numbers properly
            '12,345.679'    # Should respect decimal places parameter
        ]
        
        self.stdout.write(self.style.SUCCESS('Expected US format:'))
        for expected in expected_results:
            self.stdout.write(f"  {expected}")
