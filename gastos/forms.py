from django import forms
from .models import Gastos, CatGastos, Compra

class GastoForm(forms.ModelForm):
    class Meta:
        model = Gastos
        fields = ['id', 'id_sucursal', 'id_cat_gastos', 'monto', 'descripcion', 'id_cuenta_banco', 'fecha']

        widgets = {
            'id_sucursal': forms.Select(attrs={'class': 'form-control'}, choices=Gastos.objects.all()),
            'id_cat_gastos': forms.Select(attrs={'class': 'form-control'}, choices=Gastos.objects.all()),
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

class ComprasForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ['fecha_compra', 'productor', 'producto', 'cantidad', 'precio_unitario', 'monto_total', 'fecha_registro']

        widgets = {
                    'fecha_compra': forms.DateInput(attrs={'class': 'form-control'}, format='%Y-%m-%d'),
                    'productor': forms.Select(attrs={'class': 'form-control'}, choices=Compra.objects.all()),
                    'producto': forms.Select(attrs={'class': 'form-control'}, choices=Compra.objects.all()),
                    'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
                    'precio_unitario': forms.NumberInput(attrs={'class': 'form-control'}),
                    'monto_total': forms.NumberInput(attrs={'class': 'form-control'}),
                    'fecha_registro': forms.DateTimeInput(attrs={'class': 'form-control'}),
                }