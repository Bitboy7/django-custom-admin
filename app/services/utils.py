"""
Utilidades y funciones auxiliares
"""
from django.http import HttpResponse
from datetime import datetime


class UtilService:
    """Servicio de utilidades generales"""
    
    @staticmethod
    def is_admin(user):
        """Verifica si el usuario es administrador"""
        return user.is_superuser
    
    @staticmethod
    def create_excel_response(workbook, filename_prefix="reporte"):
        """Crea una respuesta HTTP con un archivo Excel"""
        current_date = datetime.now().strftime("%Y%m%d")
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename_prefix}_{current_date}.xlsx"'
        workbook.save(response)
        return response
    
    @staticmethod
    def safe_float_conversion(value):
        """Convierte un valor a float de manera segura"""
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    @staticmethod
    def safe_int_conversion(value, default=0):
        """Convierte un valor a int de manera segura"""
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
