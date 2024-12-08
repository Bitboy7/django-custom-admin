from django import forms
from .models import Productor

class ProductorForm(forms.ModelForm):
    class Meta:
        model = Productor
        fields = '__all__'

        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su nombre'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su teléfono'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su dirección'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su email'}),
            'fecha_registro': forms.DateInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese la fecha de registro'}),
        }
