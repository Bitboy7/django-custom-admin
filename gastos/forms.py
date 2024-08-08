from django import forms
from .models import Gastos , CatGastos

class GastoForm(forms.ModelForm):
    class Meta:
        model = Gastos
        fields = ['id', 'id_sucursal', 'id_cat_gastos', 'monto', 'descripcion', 'id_cuenta_banco', 'fecha']

        widgets = {
            'id_sucursal': forms.Select(attrs={'class': 'form-control'}),
            'id_cat_gastos': forms.Select(attrs={'class': 'form-control'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control'}),
            'id_cuenta_banco': forms.Select(attrs={'class': 'form-control'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control'}),
        }

class CatGastoForm(forms.ModelForm):
    class Meta:
        model = CatGastos
        fields = ['id', 'nombre', 'fecha_registro']

        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_registro': forms.DateInput(attrs={'class': 'form-control'}),
        }

