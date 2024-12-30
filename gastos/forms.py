from django import forms
from .models import Gastos, CatGastos, SaldoMensual

class GastoForm(forms.ModelForm):
    class Meta:
        model = Gastos
        fields = ['id', 'id_sucursal', 'id_cat_gastos', 'monto', 'descripcion', 'id_cuenta_banco', 'fecha']

        widgets = {
            'id_sucursal': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Seleccione la sucursal'}, choices=Gastos.objects.all()),
            'id_cat_gastos': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Seleccione la categoría de gastos'}, choices=Gastos.objects.all()),
            'monto': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el monto'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Ingrese una descripción'}),
            'id_cuenta_banco': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Seleccione la cuenta bancaria'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'placeholder': 'YYYY-MM-DD'}),
        }

class CatGastoForm(forms.ModelForm):
    class Meta:
        model = CatGastos
        fields = ['id', 'nombre', 'fecha_registro']

        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el nombre'}),
            'fecha_registro': forms.DateInput(attrs={'class': 'form-control', 'placeholder': 'YYYY-MM-DD'}),
        }


class SaldoMensualForm(forms.ModelForm):
    class Meta:
        model = SaldoMensual
        fields = ['cuenta', 'año', 'mes', 'saldo_inicial']
        widgets = {
            'cuenta': forms.Select(attrs={'class': 'form-control'}),
            'año': forms.NumberInput(attrs={'class': 'form-control'}),
            'mes': forms.NumberInput(attrs={'class': 'form-control'}),
            'saldo_inicial': forms.NumberInput(attrs={'class': 'form-control'}),
        }
