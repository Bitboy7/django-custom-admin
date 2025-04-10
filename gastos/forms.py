from django import forms
from .models import Gastos, CatGastos, SaldoMensual, Compra

class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ['fecha_compra', 'productor', 'producto', 'cantidad', 'precio_unitario', 
                 'monto_total', 'cuenta', 'tipo_pago', 'observaciones']

        widgets = {
            'fecha_compra': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 
                'placeholder': 'YYYY-MM-DD',
                'required': True,
            }),
            'productor': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Seleccione el productor'}),
            'producto': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Seleccione el producto'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese la cantidad'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el precio unitario'}),
            'monto_total': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Monto total'}),
            'cuenta': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Seleccione la cuenta'}),
            'tipo_pago': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Seleccione el tipo de pago'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Ingrese observaciones'}),
        }

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
