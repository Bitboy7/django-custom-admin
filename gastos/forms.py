from django import forms
from .models import Gastos, CatGastos, SaldoMensual, Compra, Cuenta
from catalogo.models import Productor, Sucursal

class CompraForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Hacer el campo monto_total de solo lectura y agregar ayuda
        self.fields['monto_total'].widget.attrs.update({
            'readonly': True,
            'title': 'Este campo se calcula automáticamente (Cantidad × Precio Unitario)',
            'style': 'background-color: #f8f9fa;',
            'class': 'calculated-field calc-tooltip'
        })
        
        # Agregar IDs específicos para el JavaScript
        self.fields['cantidad'].widget.attrs.update({
            'id': 'id_cantidad_compra',
            'min': '0',
            'step': '1'
        })
        
        self.fields['precio_unitario'].widget.attrs.update({
            'id': 'id_precio_unitario_compra',
            'min': '0'
        })
        
        self.fields['monto_total'].widget.attrs.update({
            'id': 'id_monto_total_compra'
        })

    def clean(self):
        cleaned_data = super().clean()
        cantidad = cleaned_data.get('cantidad')
        precio_unitario = cleaned_data.get('precio_unitario')
        
        # Calcular automáticamente el monto total
        if cantidad is not None and precio_unitario is not None:
            monto_total = cantidad * precio_unitario
            cleaned_data['monto_total'] = monto_total
            
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Asegurar que el monto total se calcule correctamente
        if instance.cantidad and instance.precio_unitario:
            instance.monto_total = instance.cantidad * instance.precio_unitario
            
        if commit:
            instance.save()
        return instance

    class Meta:
        model = Compra
        fields = ['fecha_compra', 'productor', 'producto', 'cantidad', 'precio_unitario', 
                  'monto_total', 'cuenta', 'tipo_pago']
        
        widgets = {
            'fecha_compra': forms.DateInput(attrs={
                'class': 'form-control', 
                'placeholder': 'YYYY-MM-DD',
                'type': 'date'
            }),
            'productor': forms.Select(attrs={'class': 'form-control'}),
            'producto': forms.Select(attrs={'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese la cantidad'
            }),
            'precio_unitario': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01',
                'placeholder': 'Ingrese el precio unitario'
            }),
            'monto_total': forms.NumberInput(attrs={
                'class': 'form-control calculated-field', 
                'step': '0.01',
                'placeholder': 'Se calculará automáticamente'
            }),
            'cuenta': forms.Select(attrs={'class': 'form-control'}),
            'tipo_pago': forms.Select(attrs={'class': 'form-control'}),
        }
    

class GastoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Configurar opciones para los campos select
        self.fields['id_sucursal'].queryset = Sucursal.objects.all()
        self.fields['id_cat_gastos'].queryset = CatGastos.objects.all().order_by('nombre')
        self.fields['id_cuenta_banco'].queryset = Cuenta.objects.all().order_by('id_banco__nombre', 'numero_cuenta')
        
        # Configurar labels más amigables
        self.fields['id_sucursal'].label = 'Sucursal'
        self.fields['id_cat_gastos'].label = 'Categoría de Gasto'
        self.fields['id_cuenta_banco'].label = 'Cuenta Bancaria'
        self.fields['monto'].label = 'Monto'
        self.fields['descripcion'].label = 'Descripción'
        self.fields['fecha'].label = 'Fecha'
        
        # Configurar placeholder para campo vacío
        self.fields['id_sucursal'].empty_label = "Seleccione una sucursal"
        self.fields['id_cat_gastos'].empty_label = "Seleccione una categoría"
        self.fields['id_cuenta_banco'].empty_label = "Seleccione una cuenta bancaria"
        
        # Agregar help text
        self.fields['id_sucursal'].help_text = "Selecciona la sucursal donde se realizó el gasto"
        self.fields['id_cat_gastos'].help_text = "Elige la categoría que mejor describa este gasto"
        self.fields['id_cuenta_banco'].help_text = "Cuenta bancaria desde la cual se pagó el gasto"

    class Meta:
        model = Gastos
        fields = ['id_sucursal', 'id_cat_gastos', 'monto', 'descripcion', 'id_cuenta_banco', 'fecha']

        widgets = {
            'id_sucursal': forms.Select(attrs={
                'class': 'w-full px-3 py-2 pr-10 border border-slate-300 rounded-lg shadow-sm focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-white transition-colors duration-200 appearance-none'
            }),
            'id_cat_gastos': forms.Select(attrs={
                'class': 'w-full px-3 py-2 pr-10 border border-slate-300 rounded-lg shadow-sm focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-white transition-colors duration-200 appearance-none'
            }),
            'monto': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg shadow-sm focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-colors duration-200',
                'step': '0.01',
                'placeholder': 'Ingrese el monto'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg shadow-sm focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-colors duration-200',
                'rows': 3,
                'placeholder': 'Descripción del gasto...'
            }),
            'id_cuenta_banco': forms.Select(attrs={
                'class': 'w-full px-3 py-2 pr-10 border border-slate-300 rounded-lg shadow-sm focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-white transition-colors duration-200 appearance-none'
            }),
            'fecha': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-slate-300 rounded-lg shadow-sm focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-colors duration-200',
                'type': 'date'
            }),
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

class FacturaUploadForm(forms.Form):
    documento_pdf = forms.FileField(
        label="Subir Documento PDF",
        help_text="Sube una factura o estado de cuenta en formato PDF",
        widget=forms.FileInput(attrs={
            'accept': '.pdf',
            'class': 'form-control'
        })
    )
    tipo_documento = forms.ChoiceField(
        label="Tipo de Documento",
        choices=[
            ('auto', 'Detectar automáticamente'),
            ('factura', 'Factura'),
            ('estado_cuenta', 'Estado de Cuenta'),
        ],
        initial='auto',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    asignar_categorias = forms.BooleanField(
        label="Asignar categorías automáticamente",
        help_text="⚠️ ATENCIÓN: Esta opción utiliza IA para sugerir categorías. Puede ser lenta y exceder límites de API para estados de cuenta con muchos movimientos.",
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
