# Custom admin site for dashboard functionality
from django.contrib.admin import AdminSite
from django.template.response import TemplateResponse
from .views import dashboard_callback


class CustomAdminSite(AdminSite):
    site_header = "Agricola de la Costa San Luis"
    site_title = "Sistema administrativo"
    index_title = "Panel de Administración"
    
    def index(self, request, extra_context=None):
        """
        Displays the main admin index page, which lists all of the installed
        apps that have been registered in this site.
        """
        response = super().index(request, extra_context)
        
        # Solo agregar datos del dashboard si estamos en la página principal
        if hasattr(response, 'context_data'):
            context = response.context_data
            # Llamar al dashboard_callback para obtener los datos
            context = dashboard_callback(request, context)
            response.context_data = context
        
        return response


# Create custom admin site instance
admin_site = CustomAdminSite(name='custom_admin')
