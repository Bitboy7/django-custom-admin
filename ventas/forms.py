from django import forms
from django.core.exceptions import ValidationError
from .models import Anticipo, Ventas, Cliente, PagoVenta, Agente, TerminoCredito
from catalogo.models import Producto, Sucursal
from gastos.models import Cuenta


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


# =============================================================================
# CFDI IMPORT FORMS
# =============================================================================

class CFDIUploadForm(forms.Form):
    """Step 1 – just the file upload."""
    xml_file = forms.FileField(
        label='Archivo XML (CFDI)',
        help_text='Sube el archivo .xml generado por tu PAC (máx. 1 MB).',
        widget=forms.ClearableFileInput(attrs={'accept': '.xml', 'class': 'form-control'}),
    )

    def clean_xml_file(self):
        f = self.cleaned_data['xml_file']
        if not f.name.lower().endswith('.xml'):
            raise ValidationError('El archivo debe tener extensión .xml')
        if f.size > 1 * 1024 * 1024:
            raise ValidationError('El archivo no puede superar 1 MB.')
        return f


class CFDIConfirmForm(forms.Form):
    """
    Step 2 – confirmation form pre-filled with XML data.
    User completes the manual-only fields and confirms before saving.
    """
    # ── Fields extracted from XML (pre-filled, editable) ──────────────────
    folio_factura = forms.CharField(
        max_length=50, required=False, label='Folio factura / UUID',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    fecha_emision_cfdi = forms.DateField(
        required=False, label='Fecha emisión CFDI',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
    )
    monto = forms.DecimalField(
        max_digits=12, decimal_places=2, label='Monto total (MXN)',
        widget=forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
    )
    moneda_venta = forms.CharField(
        max_length=3, initial='MXN', label='Moneda',
        widget=forms.TextInput(attrs={'class': 'form-control', 'maxlength': '3'}),
    )
    tipo_cambio = forms.DecimalField(
        max_digits=10, decimal_places=4, initial='1.0000', label='Tipo de cambio USD',
        widget=forms.NumberInput(attrs={'step': '0.0001', 'class': 'form-control'}),
    )
    incoterm = forms.CharField(
        max_length=10, required=False, label='Incoterm',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    tipo_venta = forms.ChoiceField(
        choices=Ventas.TipoVenta.choices, label='Tipo de venta',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    modalidad_pago = forms.ChoiceField(
        choices=Ventas.ModalidadPago.choices, label='Modalidad de pago',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    termino_credito = forms.ModelChoiceField(
        queryset=TerminoCredito.objects.filter(activo=True).order_by('dias_credito'),
        required=False, label='Término de crédito',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    cantidad = forms.DecimalField(
        max_digits=12, decimal_places=3, label='Cantidad (cajas)',
        widget=forms.NumberInput(attrs={'step': '0.001', 'class': 'form-control'}),
    )
    descripcion = forms.CharField(
        max_length=100, required=False, label='Descripción',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    PO = forms.CharField(
        max_length=50, required=False, label='P.O. (Purchase Order)',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )

    # ── Client & product (pre-selected from match, editable) ──────────────
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.filter(activo=True).order_by('nombre'),
        label='Cliente',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(disponible=True).order_by('variedad'),
        label='Producto',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    # ── Manual-only fields ─────────────────────────────────────────────────
    fecha_salida_manifiesto = forms.DateField(
        label='Fecha salida manifiesto',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    fecha_deposito = forms.DateField(
        label='Fecha depósito',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    agente_id = forms.ModelChoiceField(
        queryset=Agente.objects.all().order_by('nombre'),
        label='Agente aduanal',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    pedimento = forms.CharField(
        max_length=50, required=False, label='Pedimento',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    carga = forms.CharField(
        max_length=50, required=False, label='Carga',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    sucursal_id = forms.ModelChoiceField(
        queryset=Sucursal.objects.all().order_by('nombre'),
        label='Sucursal',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    cuenta = forms.ModelChoiceField(
        queryset=Cuenta.objects.all().order_by('numero_cuenta'),
        required=False, label='Cuenta',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    tipo_registro = forms.ChoiceField(
        choices=Ventas.TipoRegistro.choices,
        initial=Ventas.TipoRegistro.VENTA,
        label='Tipo de registro',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )


class AnticipoForm(forms.ModelForm):
    class Meta:
        model = Anticipo
        fields = ['cliente', 'cuenta', 'monto', 'fecha', 'descripcion', 'estado_anticipo']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-control'}),
            'cuenta': forms.Select(attrs={'class': 'form-control'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control'}),
            'estado_anticipo': forms.Select(attrs={'class': 'form-control'}),
        }