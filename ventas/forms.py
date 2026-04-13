from django import forms
from .models import Anticipo, Ventas, Cliente


class VentasAdminForm(forms.ModelForm):
    """Form for Ventas admin with smart validation rules and auto-population."""

    class Meta:
        model = Ventas
        fields = '__all__'
        widgets = {
            'tipo_venta': forms.Select(attrs={'class': 'auto-tipo-venta'}),
            'mercado_destino': forms.Select(attrs={'class': 'auto-mercado-destino'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Si estamos editando una venta existente, pre-poblar basado en cliente
        if self.instance and self.instance.pk and self.instance.cliente:
            cliente = self.instance.cliente
            # Auto-establecer tipo de venta basado en país
            if cliente.pais.nombre != 'México':
                self.initial['tipo_venta'] = Ventas.TipoVenta.EXPORTACION
            else:
                self.initial['tipo_venta'] = Ventas.TipoVenta.NACIONAL
            
            # Auto-establecer mercado destino si el cliente lo tiene
            if cliente.mercado_destino:
                self.initial['mercado_destino'] = cliente.mercado_destino

    def clean(self):
        cleaned_data = super().clean()
        modalidad = cleaned_data.get('modalidad_pago')
        termino = cleaned_data.get('termino_credito')
        cliente = cleaned_data.get('cliente')
        tipo_venta = cleaned_data.get('tipo_venta')

        # Validar término de crédito
        if modalidad == Ventas.ModalidadPago.CREDITO and not termino:
            self.add_error(
                'termino_credito',
                'El término de crédito es obligatorio para ventas a crédito.'
            )
        
        # Auto-establecer tipo de venta basado en país del cliente
        if cliente:
            if cliente.pais.nombre != 'México':
                cleaned_data['tipo_venta'] = Ventas.TipoVenta.EXPORTACION
            else:
                cleaned_data['tipo_venta'] = Ventas.TipoVenta.NACIONAL
            
            # Auto-establecer mercado destino si el cliente lo tiene
            if cliente.mercado_destino:
                cleaned_data['mercado_destino'] = cliente.mercado_destino

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