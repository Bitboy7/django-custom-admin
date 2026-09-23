from datetime import date

from django.test import SimpleTestCase

from app.services.filter_utils import FilterBuilder


class MonthlyRangeFilterTests(SimpleTestCase):
    def test_month_range_replaces_year_and_month_filters(self):
        filters = FilterBuilder.build_standard_filters(
            periodo='mensual',
            year=2026,
            month=1,
            mes_inicio='2025-10',
            mes_fin='2026-01',
        )

        self.assertIn('fecha__range', filters)
        self.assertEqual(filters['fecha__range'][0], date(2025, 10, 1))
        self.assertEqual(filters['fecha__range'][1], date(2026, 1, 31))
        self.assertNotIn('fecha__year', filters)
        self.assertNotIn('fecha__month', filters)
        self.assertNotIn('fecha__month__in', filters)

    def test_future_or_current_month_is_capped_to_today(self):
        today = date.today()
        current_month = f"{today.year}-{today.month:02d}"

        filters = FilterBuilder.build_standard_filters(
            periodo='mensual',
            mes_inicio='2025-10',
            mes_fin=current_month,
        )

        self.assertEqual(filters['fecha__range'][1], today)

    def test_default_year_and_month_behavior_preserved(self):
        filters = FilterBuilder.build_standard_filters(
            periodo='mensual',
            year=2025,
            selected_months=[10, 11, 12],
            use_default_year=False,
        )

        self.assertEqual(filters['fecha__year'], 2025)
        self.assertEqual(filters['fecha__month__in'], [10, 11, 12])
        self.assertNotIn('fecha__range', filters)

    def test_invalid_month_range_is_ignored(self):
        filters = FilterBuilder.build_standard_filters(
            periodo='mensual',
            year=2026,
            mes_inicio='2025-10',
            mes_fin='no-es-un-mes',
        )

        self.assertNotIn('fecha__range', filters)
        self.assertEqual(filters['fecha__year'], 2026)

    def test_inverted_range_is_ignored(self):
        filters = FilterBuilder.build_standard_filters(
            periodo='mensual',
            mes_inicio='2026-09',
            mes_fin='2025-10',
        )

        self.assertNotIn('fecha__range', filters)
