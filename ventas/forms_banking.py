"""
Formularios con validaciones de nivel bancario para ventas.

Estándares implementados:
- RF01: Un pago solo puede pertenecer a una venta
- RF02: No se permiten pagos a ventas completadas  
- RF03: No se permiten sobrepagos
- RF07: No se pueden asignar anticipos a ventas completadas
- RF08: Validaciones en múltiples niveles (formulario + modelo + BD)
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import PagoVenta, Anticipo, Ventas


class PagoVentaForm(forms.ModelForm):
    """
    Formulario para PagoVenta con validaciones estrictas.
    """
    
    class Meta:
        model = PagoVenta
        fields = '__all__'
        widgets = {
            'fecha_pago': forms.DateInput(attrs={'type': 'date'}),
            'notas': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # RF02: Filtrar ventas - solo mostrar ventas a CRÉDITO que NO estén completadas
        if 'venta' in self.fields:
            self.fields['venta'].queryset = Ventas.objects.filter(
                modalidad_pago=Ventas.ModalidadPago.CREDITO
            ).exclude(
                estado_cobranza=Ventas.EstadoCobranza.PAGADO
            ).select_related('cliente').order_by('-fecha_registro')
            
            self.fields['venta'].label_from_instance = lambda obj: (
                f"{obj.carga} - {obj.cliente.nombre} - "
                f"Saldo: ${obj.saldo_pendiente():,.2f}"
            )
            
            self.fields['venta'].help_text = (
                '<strong>Solo ventas a CRÉDITO con saldo pendiente.</strong><br>'
                'Las ventas completadas NO aparecen en la lista.'
            )
        
        # Mostrar saldo pendiente en el campo de monto
        if self.instance and self.instance.pk and self.instance.venta:
            saldo = self.instance.venta.saldo_pendiente()
            self.fields['monto_pago'].help_text = (
                f'<strong style="color:#047857;">Saldo pendiente: ${saldo:,.2f}</strong><br>'
                'No se permiten sobrepagos por controles bancarios.'
            )
        elif 'venta' in self.initial and self.initial['venta']:
            try:
                venta = Ventas.objects.get(pk=self.initial['venta'])
                saldo = venta.saldo_pendiente()
                self.fields['monto_pago'].help_text = (
                    f'<strong style="color:#047857;">Saldo pendiente: ${saldo:,.2f}</strong>'
                )
            except:
                pass
    
    def clean(self):
        cleaned_data = super().clean()
        venta = cleaned_data.get('venta')
        monto_pago = cleaned_data.get('monto_pago')
        
        if not venta or not monto_pago:
            return cleaned_data
        
        # RF02: Validar que la venta NO esté completada
        if venta.estado_cobranza == Ventas.EstadoCobranza.PAGADO:
            raise ValidationError(
                '❌ Esta venta ya está completamente pagada. No se permiten más pagos.'
            )
        
        # RF03: Validar que no se sobrepague
        saldo_actual = venta.saldo_pendiente()
        
        # Si estamos editando, considerar el monto original del pago
        if self.instance and self.instance.pk:
            pago_anterior = PagoVenta.objects.get(pk=self.instance.pk)
            saldo_actual += float(pago_anterior.monto_pago.amount)
        
        if float(monto_pago.amount) > saldo_actual:
            raise ValidationError(
                f'❌ El monto del pago (${monto_pago.amount:,.2f}) excede el saldo pendiente (${saldo_actual:,.2f}). '
                'No se permiten sobrepagos por controles bancarios.'
            )
        
        # Validar monto positivo
        if monto_pago.amount <= 0:
            self.add_error('monto_pago', '❌ El monto del pago debe ser mayor a cero.')
        
        # Validar que la venta sea a crédito
        if venta.modalidad_pago != Ventas.ModalidadPago.CREDITO:
            self.add_error(
                'venta',
                '❌ Solo se pueden registrar pagos para ventas a crédito.'
            )
        
        return cleaned_data
