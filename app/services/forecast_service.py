"""
Servicio de predicciones financieras usando scikit-learn.

Utiliza los servicios de reporte existentes (BaseReportService) para
obtener series historicas y proyecta tendencias a futuro con modelos
de regresion lineal y polinomial.

Cache Redis integrado para evitar recalculo innecesario.
"""
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Dict, List, Optional, Any, Tuple
import logging

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline

from .base_report_service import BaseReportService
from .cache_service import cache_service

logger = logging.getLogger(__name__)

MONTHS_ES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]


class ForecastService:
    """
    Servicio de predicciones financieras.

    Toma cualquier subclase de BaseReportService, extrae sus series
    historicas mensuales y proyecta hacia adelante usando regresion.

    Uso:
        from app.services.balance_service import BalanceAnalysisService
        from app.services.forecast_service import ForecastService

        gastos_service = BalanceAnalysisService()
        forecast = ForecastService()

        result = forecast.forecast_from_service(
            service=gastos_service,
            filters={'fecha__year': 2026},
            months_ahead=6,
            model_type='polynomial'
        )
    """

    def __init__(self):
        self.default_months_ahead = 6

    def _extract_monthly_totals(
        self,
        service: BaseReportService,
        filters: Dict[str, Any],
        months_back: int = 36
    ) -> List[Dict[str, Any]]:
        """
        Extrae totales mensuales de cualquier servicio de reporte.

        Usa el propio queryset del servicio y agrega por mes
        para obtener la serie temporal historica.

        Args:
            service: Instancia de BaseReportService (o subclase)
            filters: Filtros base (ej: {'fecha__year': 2026})
            months_back: Cuantos meses hacia atras extraer

        Returns:
            Lista de dicts con {month_index, periodo_label, total}
            ordenada cronologicamente.
        """
        from django.db.models import Sum
        from django.db.models.functions import TruncMonth

        model = service.get_model()
        date_field = service.get_date_field()
        amount_field = service.get_amount_field()
        annotation_name = service.get_total_annotation_name()

        queryset = model.objects.filter(**filters)

        monthly = (
            queryset
            .annotate(periodo=TruncMonth(date_field))
            .values('periodo')
            .annotate(**{annotation_name: Sum(amount_field)})
            .order_by('periodo')
        )

        result = []
        for i, entry in enumerate(monthly):
            periodo_date = entry['periodo']
            total = float(entry[annotation_name] or 0)
            label = f"{MONTHS_ES[periodo_date.month - 1]} {periodo_date.year}"
            result.append({
                'month_index': i,
                'periodo': periodo_date,
                'periodo_label': label,
                'total': total,
                'year': periodo_date.year,
                'month': periodo_date.month,
            })

        return result

    def _prepare_training_data(
        self,
        historical: List[Dict[str, Any]]
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]:
        """
        Prepara arrays numpy para scikit-learn.

        Args:
            historical: Lista de datos historicos de _extract_monthly_totals

        Returns:
            (X, y, future_X, labels) donde:
              - X: indices de meses historicos (2D)
              - y: valores totales historicos
              - future_X: indices para prediccion
              - labels: etiquetas de los periodos historicos
        """
        if len(historical) < 3:
            raise ValueError(
                f"Se necesitan al menos 3 meses de datos historicos, "
                f"se encontraron {len(historical)}"
            )

        X = np.array([[d['month_index']] for d in historical], dtype=float)
        y = np.array([d['total'] for d in historical], dtype=float)
        labels = [d['periodo_label'] for d in historical]

        return X, y, labels

    def _build_future_indices(
        self,
        X: np.ndarray,
        months_ahead: int,
        last_date: datetime
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Construye los indices y etiquetas para los meses futuros.

        Args:
            X: Indices historicos
            months_ahead: Meses a predecir
            last_date: Ultima fecha historica

        Returns:
            (future_X, future_labels)
        """
        last_idx = int(X[-1][0])
        future_X = np.array(
            [[last_idx + 1 + i] for i in range(months_ahead)],
            dtype=float
        )
        future_labels = []
        for i in range(1, months_ahead + 1):
            future_date = last_date + relativedelta(months=i)
            future_labels.append(
                f"{MONTHS_ES[future_date.month - 1]} {future_date.year}"
            )

        return future_X, future_labels

    def _calculate_confidence_band(
        self,
        model,
        X: np.ndarray,
        y: np.ndarray,
        future_X: np.ndarray,
        predictions: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, float]:
        """
        Calcula banda de confianza basada en residuos historicos.

        Returns:
            (lower_bound, upper_bound, residual_std)
        """
        residuals = y - model.predict(X)
        residual_std = self._sanitize_float(np.std(residuals), 0)

        z_score = 1.96
        margin = z_score * residual_std

        lower = predictions - margin
        upper = predictions + margin

        lower = np.maximum(lower, 0)

        return lower, upper, residual_std

    def forecast_from_service(
        self,
        service: BaseReportService,
        filters: Dict[str, Any],
        months_ahead: int = 3,
        model_type: str = 'polynomial',
        polynomial_degree: int = 2,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Genera predicciones a partir de un servicio de reporte.

        Este es el metodo principal. Toma cualquier servicio que herede
        de BaseReportService, extrae su historico mensual, entrena un modelo
        y proyecta hacia el futuro.

        Args:
            service: Instancia de BaseReportService (BalanceAnalysisService,
                     ComprasAnalysisService, etc.)
            filters: Filtros Django para el queryset historico
                     (ej: {'fecha__year': 2026,
                           'id_sucursal_id': 1})
            months_ahead: Meses a proyectar (default: 3, max: 12)
            model_type: 'linear' o 'polynomial'
            polynomial_degree: Grado del polinomio si model_type='polynomial'
            force_refresh: Si True, ignora cache y recalcula

        Returns:
            Diccionario con:
              - service_name: nombre del modelo analizado
              - historical: serie historica [{periodo_label, total}, ...]
              - predictions: serie predicha [{periodo_label, predicted, lower, upper}, ...]
              - metrics: {r2_score, residual_std, trend_direction, trend_strength}
              - model_info: {model_type, polynomial_degree, months_ahead, data_points}
        """
        model_name = service.get_model()._meta.model_name
        months_ahead = max(1, min(months_ahead, 12))

        cache_key = cache_service._generate_cache_key(
            'forecast', model_name,
            months_ahead=months_ahead,
            model_type=model_type,
            degree=polynomial_degree,
            **filters
        )

        if not force_refresh:
            cached = cache_service.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit para forecast {model_name}")
                return cached

        logger.info(
            f"Generando forecast para {model_name} "
            f"({months_ahead} meses, modelo={model_type})"
        )

        historical = self._extract_monthly_totals(service, filters)

        X, y, historical_labels = self._prepare_training_data(historical)
        last_date = historical[-1]['periodo'] if historical else datetime.now()

        future_X, future_labels = self._build_future_indices(
            X, months_ahead, last_date
        )

        if model_type == 'polynomial' and len(historical) >= 6:
            poly_degree = min(polynomial_degree, len(historical) - 1, 4)
            model = make_pipeline(
                PolynomialFeatures(degree=poly_degree),
                LinearRegression()
            )
        else:
            model_type = 'linear'
            model = LinearRegression()

        model.fit(X, y)
        r2_score = float(model.score(X, y))
        predictions = model.predict(future_X)
        lower, upper, residual_std = self._calculate_confidence_band(
            model, X, y, future_X, predictions
        )

        trend_direction, trend_strength = self._analyze_trend(predictions, y)

        result = {
            'service_name': model_name,
            'historical': [
                {'periodo_label': lbl, 'total': self._sanitize_float(val, 0)}
                for lbl, val in zip(historical_labels, y.tolist())
            ],
            'predictions': [
                {
                    'periodo_label': lbl,
                    'predicted': round(self._sanitize_float(pred, 0), 2),
                    'lower': round(self._sanitize_float(lo, 0), 2),
                    'upper': round(self._sanitize_float(up, 0), 2),
                }
                for lbl, pred, lo, up in zip(
                    future_labels, predictions, lower, upper
                )
            ],
            'metrics': {
                'r2_score': round(self._sanitize_float(r2_score, 0), 4),
                'residual_std': round(self._sanitize_float(residual_std, 0), 2),
                'trend_direction': trend_direction,
                'trend_strength': round(self._sanitize_float(trend_strength, 0), 2),
                'last_historical_value': round(self._sanitize_float(y[-1], 0), 2),
                'next_predicted_value': round(self._sanitize_float(predictions[0], 0), 2),
                'predicted_change_pct': self._pct_change(y[-1], predictions[0]),
            },
            'model_info': {
                'model_type': model_type,
                'polynomial_degree': (
                    poly_degree if model_type == 'polynomial' else None
                ),
                'months_ahead': months_ahead,
                'data_points': len(historical),
                'generated_at': datetime.now().isoformat(),
            },
        }

        timeout = cache_service.timeouts.get('reportes', 1800)
        cache_service.set(cache_key, result, timeout)
        logger.info(f"Forecast generado y cacheado para {model_name}")

        return result

    def generate_all_forecasts(
        self,
        year: int = None,
        sucursal_id: Any = None,
        months_ahead: int = 3,
        model_type: str = 'polynomial',
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Genera predicciones para gastos, ventas, compras y balance neto.

        Usa los servicios de reporte existentes para cada dominio y
        consolida todas las predicciones en un solo resultado.

        Args:
            year: Ano base para datos historicos (default: ano actual)
            sucursal_id: ID de sucursal para filtrar (None = todas)
            months_ahead: Meses a proyectar
            model_type: 'linear' o 'polynomial'
            force_refresh: Ignorar cache

        Returns:
            Diccionario con predicciones por dominio + balance neto proyectado
        """
        if year is None:
            year = datetime.now().year

        cache_key = cache_service._generate_cache_key(
            'forecast_all',
            year=year,
            sucursal=sucursal_id,
            months_ahead=months_ahead,
            model_type=model_type
        )

        if not force_refresh:
            cached = cache_service.get(cache_key)
            if cached is not None:
                return cached

        base_filters = {}
        if year:
            base_filters['fecha__year__gte'] = max(year - 2, 2020)
            base_filters['fecha__year__lte'] = year
        if sucursal_id:
            base_filters['id_sucursal_id'] = sucursal_id

        forecasts = {}

        try:
            from .balance_service import BalanceAnalysisService
            gastos_service = BalanceAnalysisService()
            gastos_filters = dict(base_filters)
            gastos_filters.pop('fecha__year__gte', None)
            gastos_filters['fecha__year'] = year
            gastos_filters['fecha__year__gte'] = max(year - 2, 2020)
            forecasts['gastos'] = self.forecast_from_service(
                gastos_service, gastos_filters,
                months_ahead=months_ahead,
                model_type=model_type,
                force_refresh=force_refresh
            )
        except Exception as e:
            logger.warning(f"No se pudo generar forecast de gastos: {e}")
            forecasts['gastos'] = None

        try:
            from .compras_service import ComprasAnalysisService
            compras_service = ComprasAnalysisService()
            compras_filters = {'fecha_compra__year__gte': max(year - 2, 2020)}
            forecasts['compras'] = self.forecast_from_service(
                compras_service, compras_filters,
                months_ahead=months_ahead,
                model_type=model_type,
                force_refresh=force_refresh
            )
        except Exception as e:
            logger.warning(f"No se pudo generar forecast de compras: {e}")
            forecasts['compras'] = None

        try:
            from ventas.models import Ventas
            from .base_report_service import BaseReportService

            class VentasForecastAdapter(BaseReportService):
                def get_model(self):
                    return Ventas

                def get_date_field(self) -> str:
                    return 'fecha_salida_manifiesto'

                def get_amount_field(self) -> str:
                    return 'monto'

                def get_group_fields(self, periodo: str):
                    return ['id_sucursal__nombre']

            ventas_adapter = VentasForecastAdapter()
            ventas_filters = {
                'fecha_salida_manifiesto__year__gte': max(year - 2, 2020)
            }
            forecasts['ventas'] = self.forecast_from_service(
                ventas_adapter, ventas_filters,
                months_ahead=months_ahead,
                model_type=model_type,
                force_refresh=force_refresh
            )
        except Exception as e:
            logger.warning(f"No se pudo generar forecast de ventas: {e}")
            forecasts['ventas'] = None

        forecasts['balance_neto'] = self._compute_net_balance_forecast(
            forecasts, months_ahead
        )

        result = {
            'forecasts': forecasts,
            'params': {
                'year': year,
                'sucursal_id': sucursal_id,
                'months_ahead': months_ahead,
                'model_type': model_type,
                'generated_at': datetime.now().isoformat(),
            },
        }

        timeout = cache_service.timeouts.get('reportes', 1800)
        cache_service.set(cache_key, result, timeout)

        return result

    def _compute_net_balance_forecast(
        self,
        forecasts: Dict[str, Any],
        months_ahead: int
    ) -> Optional[Dict[str, Any]]:
        """
        Calcula balance neto proyectado (ventas - gastos - compras).
        """
        predictions = []
        for i in range(months_ahead):
            ventas_pred = 0
            if forecasts.get('ventas') and forecasts['ventas']:
                ventas_pred = forecasts['ventas']['predictions'][i]['predicted']

            gastos_pred = 0
            if forecasts.get('gastos') and forecasts['gastos']:
                gastos_pred = forecasts['gastos']['predictions'][i]['predicted']

            compras_pred = 0
            if forecasts.get('compras') and forecasts['compras']:
                compras_pred = forecasts['compras']['predictions'][i]['predicted']

            neto = round(ventas_pred - gastos_pred - compras_pred, 2)

            label = ""
            if forecasts.get('ventas') and forecasts['ventas']:
                label = forecasts['ventas']['predictions'][i]['periodo_label']
            elif forecasts.get('gastos') and forecasts['gastos']:
                label = forecasts['gastos']['predictions'][i]['periodo_label']

            predictions.append({
                'periodo_label': label,
                'predicted': neto,
                'ventas': ventas_pred,
                'gastos': gastos_pred,
                'compras': compras_pred,
            })

        return {
            'service_name': 'balance_neto',
            'predictions': predictions,
            'metrics': {
                'r2_score': None,
                'trend_direction': (
                    'creciente' if predictions and predictions[-1]['predicted'] > predictions[0]['predicted']
                    else 'decreciente'
                ),
            },
        }

    @staticmethod
    def _sanitize_float(value, default: float = 0.0) -> float:
        """
        Convierte a float seguro, reemplazando NaN/Inf por default.
        Evita que valores no serializables lleguen al frontend.
        """
        try:
            result = float(value)
            if result != result or result == float('inf') or result == float('-inf'):
                return default
            return result
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _analyze_trend(
        predictions: np.ndarray,
        historical_y: np.ndarray
    ) -> Tuple[str, float]:
        """
        Determina direccion y fuerza de la tendencia.

        Returns:
            (direction, strength_pct)
        """
        if len(predictions) < 2:
            return 'estable', 0.0

        last_historical = ForecastService._sanitize_float(historical_y[-1])
        last_predicted = ForecastService._sanitize_float(predictions[-1])

        if last_historical == 0:
            return 'estable', 0.0

        change_pct = ((last_predicted - last_historical) / last_historical) * 100

        if abs(change_pct) < 2:
            direction = 'estable'
        elif change_pct > 0:
            direction = 'creciente'
        else:
            direction = 'decreciente'

        return direction, round(abs(change_pct), 2)

    @staticmethod
    def _pct_change(from_val: float, to_val: float) -> float:
        from_val = ForecastService._sanitize_float(from_val)
        to_val = ForecastService._sanitize_float(to_val)
        if from_val == 0:
            return 0.0
        return round(((to_val - from_val) / from_val) * 100, 2)

    def invalidate_forecast_cache(self, model_name: str = None) -> None:
        """
        Invalida el cache de predicciones cuando hay cambios en los datos.

        Args:
            model_name: Nombre del modelo a invalidar (None = todos)
        """
        patterns = []
        if model_name:
            patterns.append(f"*forecast*{model_name}*")
        else:
            patterns.append("*forecast*")

        for pattern in patterns:
            cache_service.clear_pattern(pattern)
            logger.info(f"Cache de forecast invalidado: {pattern}")
