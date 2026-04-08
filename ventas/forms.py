from django import forms
from .models import Anticipo, Ventas


class VentasAdminForm(forms.ModelForm):
    """Form for Ventas admin with smart validation rules."""

    class Meta:
        model = Ventas
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        modalidad = cleaned_data.get('modalidad_pago')
        termino = cleaned_data.get('termino_credito')

        if modalidad == Ventas.ModalidadPago.CREDITO and not termino:
            self.add_error(
                'termino_credito',
                'El término de crédito es obligatorio para ventas a crédito.'
            )

        return cleaned_data


class AnticipoForm(forms.ModelForm):
    class Meta:
        model = Anticipo
        fields = ['cliente', 'sucursal', 'cuenta', 'monto', 'fecha', 'descripcion', 'estado_anticipo']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-control'}),
            'sucursal': forms.Select(attrs={'class': 'form-control'}),
            'cuenta': forms.Select(attrs={'class': 'form-control'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control'}),
            'estado_anticipo': forms.Select(attrs={'class': 'form-control'}),
        }