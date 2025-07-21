# Widgets personalizados para Django Money con Unfold
from django import forms
from unfold.widgets import UnfoldAdminMoneyWidget

class CustomMoneyWidget(UnfoldAdminMoneyWidget):
    """
    Widget personalizado para campos de dinero que integra perfectamente
    con Django Unfold y proporciona una mejor experiencia de usuario
    """
    class Media:
        css = {
            'all': ('css/money_widget.css',)
        }
        js = ('js/money_widget.js',)

    def __init__(self, attrs=None, **kwargs):
        default_attrs = {
            'class': 'money-field',
            'style': 'border-radius: 6px; border: 1px solid #d1d5db; padding: 8px 12px;'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs, **kwargs)

    def format_value(self, value):
        """Formatear el valor del dinero para mostrar"""
        if value is None:
            return None
        # Aplicar formato personalizado si es necesario
        return super().format_value(value)
