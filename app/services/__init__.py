"""
App Services - Backend Service Layer

Este paquete contiene la capa de servicios de la aplicación,
proporcionando lógica de negocio reutilizable.

Componentes principales:
- Utils: Utilidades reutilizables (filtros, períodos, estadísticas)
- Base: Clases base abstractas para servicios de reporte
- Servicios específicos: Implementaciones concretas (gastos, compras, ventas)

Para más información, ver README.md en este directorio.
"""

# Importar clases principales para facilitar el uso
from .filter_utils import FilterBuilder, FilterOptionsProvider
from .period_utils import (
    PeriodAggregator,
    StatisticsCalculator,
    AccumulatedCalculator,
    PeriodFormatter
)
from .base_report_service import BaseReportService, BaseReportServiceWithCategories
from .balance_service import BalanceAnalysisService

# Versión del paquete
__version__ = '1.0.0'

# Exponer API pública
__all__ = [
    # Utils
    'FilterBuilder',
    'FilterOptionsProvider',
    'PeriodAggregator',
    'StatisticsCalculator',
    'AccumulatedCalculator',
    'PeriodFormatter',
    
    # Base classes
    'BaseReportService',
    'BaseReportServiceWithCategories',
    
    # Servicios específicos
    'BalanceAnalysisService',
]
