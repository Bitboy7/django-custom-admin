from django import forms
from .models import Gastos

class GastoForm(forms.ModelForm):
    class Meta:
        model = Gastos
        fields = ['id_sucursal', 'id_cat_gastos', 'monto', 'descripcion', 'id_cuenta_banco', 'fecha']



