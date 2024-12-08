from django import forms
from .models import Gastos, CatGastos, Compra

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

class ComprasForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ['fecha_compra', 'productor', 'producto', 'cantidad', 'precio_unitario', 'monto_total', 'fecha_registro']

        widgets = {
            'fecha_compra': forms.DateInput(attrs={'class': 'form-control', 'placeholder': 'YYYY-MM-DD'}, format='%Y-%m-%d'),
            'productor': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Seleccione el productor'}, choices=Compra.objects.all()),
            'producto': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Seleccione el producto'}, choices=Compra.objects.all()),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese la cantidad'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el precio unitario'}),
            'monto_total': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el monto total'}),
            'fecha_registro': forms.DateTimeInput(attrs={'class': 'form-control', 'placeholder': 'YYYY-MM-DD HH:MM:SS'}),
        }