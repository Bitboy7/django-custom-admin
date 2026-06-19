from django import forms
from .models import Inversion, CatInversion, RendimientoInversion
from catalogo.models import Sucursal
from gastos.models import Cuenta


class InversionForm(forms.ModelForm):
    """Formulario para crear/editar inversiones"""
    
    class Meta:
        model = Inversion
        fields = [
            'id_sucursal',
            'id_cat_inversion',
            'id_cuenta_banco',
            'tipo_movimiento',
            'monto',
            'fecha',
            'descripcion',
            'notas',
            'documento_soporte'
        ]
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'notas': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tipo_movimiento': forms.Select(attrs={'class': 'form-control'}),
            'id_sucursal': forms.Select(attrs={'class': 'form-control'}),
            'id_cat_inversion': forms.Select(attrs={'class': 'form-control'}),
            'id_cuenta_banco': forms.Select(attrs={'class': 'form-control'}),
        }


class RendimientoInversionForm(forms.ModelForm):
    """Formulario para registrar rendimientos"""
    
    class Meta:
        model = RendimientoInversion
        fields = [
            'inversion',
            'fecha_rendimiento',
            'monto_rendimiento',
            'tipo_rendimiento',
            'descripcion'
        ]
        widgets = {
            'fecha_rendimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'monto_rendimiento': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tipo_rendimiento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Dividendo, Interés, etc.'}),
            'descripcion': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'inversion': forms.Select(attrs={'class': 'form-control'}),
        }


class FiltroReporteForm(forms.Form):
    """Formulario para filtrar reportes"""
    
    PERIODO_CHOICES = [
        ('diario', 'Diario'),
        ('semanal', 'Semanal'),
        ('mensual', 'Mensual'),
        ('anual', 'Anual'),
    ]
    
    fecha_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    fecha_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    sucursal = forms.ModelChoiceField(
        queryset=Sucursal.objects.all(),
        required=False,
        empty_label="Todas las sucursales",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    categoria = forms.ModelChoiceField(
        queryset=CatInversion.objects.filter(activa=True),
        required=False,
        empty_label="Todas las categorías",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    periodo = forms.ChoiceField(
        choices=PERIODO_CHOICES,
        initial='mensual',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
