from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test

from .services.excel_service import ExcelReportService
from .services.balance_service import BalanceAnalysisService
from .services.utils import UtilService


@user_passes_test(UtilService.is_admin)
def export_full_report_to_excel(request):
    """
    Exporta un informe completo con gastos, compras, ventas, anticipos y un balance mensual.
    """
    excel_service = ExcelReportService()
    workbook = excel_service.create_full_report()
    
    return UtilService.create_excel_response(
        workbook, 
        filename_prefix="reporte_financiero"
    )


@login_required
def balances_view(request):
    """
    Vista principal para el análisis de balances y gastos
    """
    balance_service = BalanceAnalysisService()
    context = balance_service.get_full_context(request)
    
    return render(request, 'balances.html', context)


