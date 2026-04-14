from django import forms
from django.core.exceptions import ValidationError
from .models import Anticipo, Ventas, Cliente, PagoVenta


class VentasAdminForm(forms.ModelForm):
    """
    Form for Ventas admin with smart validation rules and auto-population.
    RF07: Implementa validaciones bancarias para anticipos.
    """

    class Meta:
        model = Ventas
        fields = '__all__'
        widgets = {
            'tipo_venta': forms.Select(attrs={'class': 'auto-tipo-venta'}),
            'mercado_destino': forms.Select(attrs={'class': 'auto-mercado-destino'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # RF07: Filtrar anticipos - solo mostrar PENDIENTES del mismo cliente
        if 'anticipo' in self.fields:
            cliente_id = None
            
            # Si estamos editando, obtener cliente actual
            if self.instance and self.instance.pk:
                cliente_id = self.instance.cliente_id
            # Si es nuevo pero hay data, obtener cliente seleccionado
            elif self.data.get('cliente'):
                try:
                    cliente_id = int(self.data.get('cliente'))
                except (ValueError, TypeError):
                    pass
            
            # Filtrar anticipos disponibles
            if cliente_id:
                self.fields['anticipo'].queryset = Anticipo.objects.filter(
                    cliente_id=cliente_id,
                    estado_anticipo=Anticipo.Estado_anticipo.Pendiente
                )
                self.fields['anticipo'].help_text = (
                    '<strong>Solo anticipos PENDIENTES del cliente seleccionado.</strong><br>'
                    'No se pueden asignar anticipos a ventas completadas.'
                )
            else:
                # Sin cliente, no mostrar anticipos
                self.fields['anticipo'].queryset = Anticipo.objects.none()
                self.fields['anticipo'].help_text = (
                    '<em>Seleccione un cliente primero para ver anticipos disponibles.</em>'
                )
        
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
        anticipo = cleaned_data.get('anticipo')

        # Validar término de crédito
        if modalidad == Ventas.ModalidadPago.CREDITO and not termino:
            self.add_error(
                'termino_credito',
                'El término de crédito es obligatorio para ventas a crédito.'
            )
        
        # RF07: Validar anticipo del mismo cliente
        if anticipo and cliente and anticipo.cliente_id != cliente.id:
            self.add_error(
                'anticipo',
                f'❌ El anticipo seleccionado pertenece a {anticipo.cliente.nombre} '
                f'pero la venta es de {cliente.nombre}. Deben ser del mismo cliente.'
            )
        
        # RF07: No permitir anticipo en venta completada
        if self.instance and self.instance.pk:
            if self.instance.estado_cobranza == Ventas.EstadoCobranza.PAGADO:
                venta_original = Ventas.objects.get(pk=self.instance.pk)
                anticipo_original_id = venta_original.anticipo_id if venta_original.anticipo else None
                anticipo_nuevo_id = anticipo.id if anticipo else None
                
                if anticipo_original_id != anticipo_nuevo_id:
                    self.add_error(
                        'anticipo',
                        '❌ No se puede cambiar el anticipo de una venta que ya está completamente pagada.'
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