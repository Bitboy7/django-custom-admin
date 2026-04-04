from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.contrib.admin.filters import SimpleListFilter
from django.contrib.admin.views.main import ChangeList
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.contrib.admin.utils import unquote
from .models import (
    Cliente, Agente, Ventas, Anticipo, TerminoCredito, MercadoDestino, PagoVenta,
    SaldoCliente, AntigüedadSaldo, EstadoCuentaCliente, ConfiguracionCuentasPorCobrar,
    ObligacionFiscal
)
from catalogo.models import Sucursal, Pais, Producto
from gastos.models import Cuenta
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.forms import ExportForm, ImportForm
from app.widgets import MoneyWidget
from django.utils.html import format_html
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.utils.safestring import mark_safe
from django.db import models
from django.db.models import Sum, Count, Avg, Q, F, Case, When, Value
from django.db.models.functions import Extract, TruncMonth, TruncDay, Coalesce
from django.utils import timezone
from datetime import datetime, timedelta, date
from decimal import Decimal
import json
from django.contrib import messages
from django.template.response import TemplateResponse
from .services.metrics_service import CuentasPorCobrarMetrics

# =============================================================================
# FILTROS PERSONALIZADOS AVANZADOS
# =============================================================================

class RangoCreditoFilter(SimpleListFilter):
    """Filtro por rango de crédito disponible"""
    title = 'Rango de Crédito Disponible'
    parameter_name = 'rango_credito'
    
    def lookups(self, request, model_admin):
        return [
            ('0-1000', '$0 - $1,000'),
            ('1000-5000', '$1,000 - $5,000'),
            ('5000-10000', '$5,000 - $10,000'),
            ('10000-50000', '$10,000 - $50,000'),
            ('50000+', '$50,000+'),
            ('sin_credito', 'Sin Crédito Disponible'),
        ]
    
    def queryset(self, request, queryset):
        if self.value() == 'sin_credito':
            return queryset.filter(
                Q(tipo_cliente='Contado') | Q(limite_credito__amount=0)
            )
        elif self.value() == '0-1000':
            return queryset.filter(
                tipo_cliente__in=['Credito', 'Mixto'],
                limite_credito__amount__range=[0, 1000]
            )
        elif self.value() == '1000-5000':
            return queryset.filter(
                tipo_cliente__in=['Credito', 'Mixto'],
                limite_credito__amount__range=[1000, 5000]
            )
        elif self.value() == '5000-10000':
            return queryset.filter(
                tipo_cliente__in=['Credito', 'Mixto'],
                limite_credito__amount__range=[5000, 10000]
            )
        elif self.value() == '10000-50000':
            return queryset.filter(
                tipo_cliente__in=['Credito', 'Mixto'],
                limite_credito__amount__range=[10000, 50000]
            )
        elif self.value() == '50000+':
            return queryset.filter(
                tipo_cliente__in=['Credito', 'Mixto'],
                limite_credito__amount__gte=50000
            )
        return queryset

class VencimientoFilter(SimpleListFilter):
    """Filtro por estado de vencimiento de ventas"""
    title = 'Estado de Vencimiento'
    parameter_name = 'vencimiento'
    
    def lookups(self, request, model_admin):
        return [
            ('vence_hoy', 'Vence Hoy'),
            ('vence_semana', 'Vence Esta Semana'),
            ('vence_mes', 'Vence Este Mes'),
            ('vencido', 'Vencido'),
            ('vencido_30', 'Vencido +30 días'),
            ('vencido_60', 'Vencido +60 días'),
            ('vencido_90', 'Vencido +90 días'),
        ]
    
    def queryset(self, request, queryset):
        hoy = timezone.now().date()
        
        if self.value() == 'vence_hoy':
            return queryset.filter(
                modalidad_pago='Credito',
                fecha_vencimiento=hoy
            )
        elif self.value() == 'vence_semana':
            fin_semana = hoy + timedelta(days=7)
            return queryset.filter(
                modalidad_pago='Credito',
                fecha_vencimiento__range=[hoy, fin_semana]
            )
        elif self.value() == 'vence_mes':
            fin_mes = hoy + timedelta(days=30)
            return queryset.filter(
                modalidad_pago='Credito',
                fecha_vencimiento__range=[hoy, fin_mes]
            )
        elif self.value() == 'vencido':
            return queryset.filter(
                modalidad_pago='Credito',
                fecha_vencimiento__lt=hoy,
                estado_cobranza__in=['Pendiente', 'Parcial']
            )
        elif self.value() == 'vencido_30':
            hace_30 = hoy - timedelta(days=30)
            return queryset.filter(
                modalidad_pago='Credito',
                fecha_vencimiento__lt=hace_30,
                estado_cobranza__in=['Pendiente', 'Parcial']
            )
        elif self.value() == 'vencido_60':
            hace_60 = hoy - timedelta(days=60)
            return queryset.filter(
                modalidad_pago='Credito',
                fecha_vencimiento__lt=hace_60,
                estado_cobranza__in=['Pendiente', 'Parcial']
            )
        elif self.value() == 'vencido_90':
            hace_90 = hoy - timedelta(days=90)
            return queryset.filter(
                modalidad_pago='Credito',
                fecha_vencimiento__lt=hace_90,
                estado_cobranza__in=['Pendiente', 'Parcial']
            )
        return queryset

class MontoVentaFilter(SimpleListFilter):
    """Filtro por rango de monto de venta"""
    title = 'Rango de Monto'
    parameter_name = 'rango_monto'
    
    def lookups(self, request, model_admin):
        return [
            ('0-1000', '$0 - $1,000'),
            ('1000-5000', '$1,000 - $5,000'),
            ('5000-10000', '$5,000 - $10,000'),
            ('10000-25000', '$10,000 - $25,000'),
            ('25000-50000', '$25,000 - $50,000'),
            ('50000+', '$50,000+'),
        ]
    
    def queryset(self, request, queryset):
        if self.value() == '0-1000':
            return queryset.filter(monto__amount__range=[0, 1000])
        elif self.value() == '1000-5000':
            return queryset.filter(monto__amount__range=[1000, 5000])
        elif self.value() == '5000-10000':
            return queryset.filter(monto__amount__range=[5000, 10000])
        elif self.value() == '10000-25000':
            return queryset.filter(monto__amount__range=[10000, 25000])
        elif self.value() == '25000-50000':
            return queryset.filter(monto__amount__range=[25000, 50000])
        elif self.value() == '50000+':
            return queryset.filter(monto__amount__gte=50000)
        return queryset


class ClienteResource(resources.ModelResource):
    pais = fields.Field(    
        column_name='pais',
        attribute='pais',
        widget=ForeignKeyWidget(Pais, field='nombre'))
    
    class Meta:
        model = Cliente
        fields = ('id', 'nombre', 'telefono', 'correo', 'direccion', 'pais', 'fecha_registro')
    
    def dehydrate_pais(self, cliente):
        return cliente.pais.nombre
    
    def before_import_row(self, row, **kwargs):
        # Asigna un ID específico basado en un rango disponible
        if not row['id']:
            last_cliente = Cliente.objects.order_by('-id').first()
            next_id = last_cliente.id + 1 if last_cliente else 1
            row['id'] = next_id
        

@admin.register(Cliente)
class ClienteAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = ClienteResource
    import_form_class = ImportForm
    export_form_class = ExportForm
    
    list_display = (
        'nombre', 'get_pais', 'tipo_cliente', 'limite_credito', 
        'calificacion_credito', 'get_credito_disponible', 'activo'
    )
    
    list_filter = ('tipo_cliente', 'calificacion_credito', 'mercado_destino', 'activo', 'pais', RangoCreditoFilter)
    search_fields = ('nombre', 'correo')
    list_per_page = 20
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'telefono', 'correo', 'direccion', 'imagen')
        }),
        ('Ubicación y Mercado', {
            'fields': ('pais', 'mercado_destino')
        }),
        ('Configuración de Crédito', {
            'fields': ('tipo_cliente', 'limite_credito', 'termino_credito_predeterminado', 
                      'calificacion_credito')
        }),
        ('Estado', {
            'fields': ('activo', 'fecha_registro'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('fecha_registro',)

    def get_pais(self, obj):
        return obj.pais.nombre
    get_pais.short_description = 'País'

    def get_bandera(self, obj):
        return obj.pais.mostrar_bandera()
    get_bandera.short_description = 'Bandera'
    
    def get_credito_disponible(self, obj):
        if obj.tipo_cliente == 'Contado':
            return 'N/A'
        disponible = obj.credito_disponible()
        color = 'green' if disponible > 0 else 'red'
        return format_html(
            '<span style="color: {}">${}</span>',
            color, f"{float(disponible):,.2f}"
        )
    get_credito_disponible.short_description = 'Crédito Disponible'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<client_id>/reporte-completo/',
                self.admin_site.admin_view(self.reporte_cliente_completo),
                name='%s_%s_reporte_completo' % (self.model._meta.app_label, self.model._meta.model_name),
            ),
        ]
        return custom_urls + urls
    
    def reporte_cliente_completo(self, request, client_id):
        """Genera un reporte completo del cliente con todas sus transacciones."""
        cliente = self.get_object(request, unquote(client_id))
        if cliente is None:
            messages.error(request, 'Cliente no encontrado')
            return redirect('admin:ventas_cliente_changelist')
            
        # Obtener métricas del cliente
        ventas_totales = cliente.ventas_set.aggregate(
            total=Sum('monto'),
            count=Count('id'),
            promedio=Avg('monto')
        )
        
        ventas_por_estado = cliente.ventas_set.values('estado_cobranza').annotate(
            total=Sum('monto'),
            count=Count('id')
        ).order_by('estado_cobranza')
        
        context = dict(
            self.admin_site.each_context(request),
            cliente=cliente,
            ventas_totales=ventas_totales,
            ventas_por_estado=ventas_por_estado,
            title=f'Reporte Completo - {cliente.nombre}'
        )
        
        return TemplateResponse(request, 'admin/ventas/cliente/reporte_completo.html', context)

# Inline para PagoVenta - debe definirse antes de VentasAdmin
class PagoVentaInline(admin.TabularInline):
    model = PagoVenta
    extra = 0
    readonly_fields = ('fecha_registro',)
    fields = ('fecha_pago', 'monto_pago', 'cuenta_destino', 'metodo_pago', 'referencia', 'notas')

@admin.register(Agente)
class AgenteAdmin(ModelAdmin):
    list_display = ('nombre', 'fecha_registro')
    list_per_page = 12
   
class VentasResource(resources.ModelResource):
    agente = fields.Field(
        column_name='agente',
        attribute='agente_id',
        widget=ForeignKeyWidget(Agente, field='nombre'))
    
    producto = fields.Field(    
        column_name='producto',
        attribute='producto',
        widget=ForeignKeyWidget(Producto, field='variedad'))
    
    cliente = fields.Field(
        column_name='cliente',
        attribute='cliente',
        widget=ForeignKeyWidget(Cliente, field='nombre'))
    
    sucursal = fields.Field(
        column_name='sucursal',
        attribute='sucursal_id',
        widget=ForeignKeyWidget(Sucursal, field='nombre'))
    
    cuenta = fields.Field(
        column_name='cuenta',
        attribute='cuenta',
        widget=ForeignKeyWidget(Cuenta, field='numero_cuenta'))
    
    monto = fields.Field(
        column_name='monto',
        attribute='monto',
        widget=MoneyWidget())

    class Meta:
        model = Ventas
        fields = ('id', 'fecha_salida_manifiesto', 'agente', 'fecha_deposito', 'carga', 'PO', 'producto', 'cantidad', 'monto', 'descripcion', 'cliente', 'fecha_registro', 'sucursal','cuenta')
        import_id_fields = ('id',)
        
    def dehydrate_agente(self, ventas):
        return ventas.agente_id.nombre
    
    def dehydrate_producto(self, ventas):
        return ventas.producto.variedad
    
    def dehydrate_cliente(self, ventas):
        return ventas.cliente.nombre
    
    def dehydrate_sucursal(self, ventas):
        return ventas.sucursal_id.nombre
    
    def dehydrate_cuenta(self, ventas):
        return ventas.cuenta.numero_cuenta if ventas.cuenta else ""

    def before_import_row(self, row, **kwargs):
        # Asigna un ID específico basado en un rango disponible
        if not row['id']:
            last_ventas = Ventas.objects.order_by('-id').first()
            next_id = last_ventas.id + 1 if last_ventas else 1
            row['id'] = next_id
       
@admin.register(Ventas)
class VentasAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = VentasResource
    import_form_class = ImportForm
    export_form_class = ExportForm
    
    list_display = (
        'fecha_salida_manifiesto', 'carga', 'get_cliente_info', 'get_monto_formateado', 
        'modalidad_pago', 'get_estado_cobranza', 'get_dias_vencimiento', 
        'tipo_venta', 'get_mercado_destino', 'get_saldo_pendiente'
    )
    
    list_filter = (
        VencimientoFilter, MontoVentaFilter, 'tipo_registro', 'modalidad_pago', 'estado_cobranza',
        'tipo_venta', 'fecha_salida_manifiesto', 'mercado_destino', 'termino_credito',
        'cliente__calificacion_credito', 'cliente__tipo_cliente'
    )
    
    search_fields = ('carga', 'cliente__nombre', 'producto__variedad', 'PO', 'pedimento')
    
    list_per_page = 30
    date_hierarchy = 'fecha_salida_manifiesto'
    
    inlines = [PagoVentaInline]
    
    actions = [
        'generar_reporte_cliente', 
        'marcar_como_pagado', 
        'generar_estado_cuenta',
        'enviar_notificacion_vencimiento',
        'exportar_cuentas_vencidas'
    ]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('fecha_salida_manifiesto', 'agente_id', 'fecha_deposito', 
                      'carga', 'PO', 'pedimento')
        }),
        ('Producto y Cliente', {
            'fields': ('producto', 'cantidad', 'monto', 'cliente', 
                      'sucursal_id', 'descripcion')
        }),
        ('Modalidad de Pago', {
            'fields': ('modalidad_pago', 'termino_credito', 'fecha_vencimiento',
                      'estado_cobranza', 'monto_pagado'),
            'classes': ('wide',)
        }),
        ('Mercado y Exportación', {
            'fields': ('tipo_venta', 'mercado_destino', 'incoterm', 
                      'moneda_venta', 'tipo_cambio'),
            'classes': ('collapse',)
        }),
        ('Contabilidad', {
            'fields': ('cuenta', 'anticipo'),
            'classes': ('collapse',)
        }),
        ('Tipo de Registro', {
            'fields': ('tipo_registro',),
            'description': 'Indica si este registro es una Venta normal o una Maquila.'
        }),
    )
    
    readonly_fields = ('fecha_registro', 'monto_pagado')
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'balances/',
                self.admin_site.admin_view(self.ventas_balances_admin_view),
                name='ventas_ventas_balances',
            ),
            path(
                'reporte-cobranza/',
                self.admin_site.admin_view(self.reporte_cobranza_admin_view),
                name='ventas_reporte_cobranza',
            ),
            path(
                'dashboard-ventas/',
                self.admin_site.admin_view(self.dashboard_ventas),
                name='ventas_dashboard',
            ),
            path(
                'reporte-cliente/<int:cliente_id>/',
                self.admin_site.admin_view(self.reporte_detallado_cliente),
                name='ventas_reporte_cliente',
            ),
            path(
                'exportar-excel/',
                self.admin_site.admin_view(self.exportar_excel_personalizado),
                name='ventas_exportar_excel',
            ),
        ]
        return custom_urls + urls
    
    def get_cliente_info(self, obj):
        """Información del cliente con indicador de riesgo"""
        cliente = obj.cliente
        color = {
            'A+': '#28a745',  # Verde
            'A': '#6c757d',   # Gris
            'B': '#fd7e14',   # Naranja
            'C': '#dc3545'    # Rojo
        }.get(cliente.calificacion_credito, '#6c757d')
        
        return format_html(
            '<strong>{}</strong><br>'
            '<small style="color: {};">📊 {}</small><br>'
            '<small>🌍 {}</small>',
            cliente.nombre,
            color,
            cliente.get_calificacion_credito_display(),
            cliente.pais.nombre
        )
    get_cliente_info.short_description = 'Cliente & Riesgo'
    
    def get_monto_formateado(self, obj):
        """Monto con formato mejorado"""
        color = '#28a745' if obj.modalidad_pago == 'Contado' else '#fd7e14'
        monto_str = f"{float(obj.monto.amount):,.2f}"
        return format_html(
            '<span style="color: {}; font-weight: bold;">${}</span><br>'
            '<small>{}</small>',
            color,
            monto_str,
            obj.moneda_venta
        )
    get_monto_formateado.short_description = 'Monto'
    
    def get_saldo_pendiente(self, obj):
        """Saldo pendiente con formato visual"""
        if obj.modalidad_pago == 'Contado':
            return format_html('<span style="color: green;">✓ Pagado</span>')
        
        saldo = obj.saldo_pendiente()
        if saldo <= 0:
            return format_html('<span style="color: green;">✓ $0.00</span>')
        
        color = '#dc3545' if obj.esta_vencida() else '#fd7e14'
        return format_html(
            '<span style="color: {}; font-weight: bold;">${}</span>',
            color, f"{float(saldo):,.2f}"
        )
    get_saldo_pendiente.short_description = 'Saldo Pendiente'
    
    # Métodos originales del admin
    def get_estado_cobranza(self, obj):
        colors = {
            'Pagado': 'green',
            'Pendiente': 'orange', 
            'Parcial': 'blue',
            'Vencido': 'red',
            'Incobrable': 'darkred'
        }
        color = colors.get(obj.estado_cobranza, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_estado_cobranza_display()
        )
    get_estado_cobranza.short_description = 'Estado Cobranza'
    
    def get_dias_vencimiento(self, obj):
        if obj.modalidad_pago == 'Contado':
            return '-'
        dias = obj.dias_vencido()
        if dias > 0:
            return format_html('<span style="color: red;">+{} días</span>', dias)
        elif dias < 0:
            return format_html('<span style="color: green;">{} días</span>', abs(dias))
        else:
            return 'Vence hoy'
    get_dias_vencimiento.short_description = 'Vencimiento'
    
    def get_mercado_destino(self, obj):
        return obj.mercado_destino.nombre if obj.mercado_destino else obj.tipo_venta
    get_mercado_destino.short_description = 'Mercado'
    
    # =============================================================================
    # ACCIONES PERSONALIZADAS
    # =============================================================================
    
    def generar_reporte_cliente(self, request, queryset):
        """Generar reporte consolidado por cliente"""
        clientes_ids = list(queryset.values_list('cliente_id', flat=True).distinct())
        
        if len(clientes_ids) > 10:
            messages.error(request, 'Selecciona máximo 10 clientes para el reporte.')
            return
            
        # Redirigir a vista de reporte personalizada
        return redirect('admin:ventas_reporte_consolidado') + '?clientes=' + ','.join(map(str, clientes_ids))
    
    generar_reporte_cliente.short_description = "📊 Generar reporte por cliente"
    
    def marcar_como_pagado(self, request, queryset):
        """Marcar ventas a crédito como pagadas"""
        ventas_credito = queryset.filter(modalidad_pago='Credito')
        count = 0
        
        for venta in ventas_credito:
            if venta.estado_cobranza != 'Pagado':
                venta.estado_cobranza = 'Pagado'
                venta.monto_pagado = venta.monto
                venta.save()
                count += 1
        
        if count > 0:
            messages.success(request, f'{count} ventas marcadas como pagadas.')
        else:
            messages.warning(request, 'No hay ventas a crédito pendientes para marcar como pagadas.')
    
    marcar_como_pagado.short_description = "💰 Marcar como pagado"
    
    def exportar_cuentas_vencidas(self, request, queryset):
        """Exportar solo cuentas vencidas a Excel"""
        from django.http import HttpResponse
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        
        hoy = timezone.now().date()
        vencidas = queryset.filter(
            modalidad_pago='Credito',
            fecha_vencimiento__lt=hoy,
            estado_cobranza__in=['Pendiente', 'Parcial']
        )
        
        if not vencidas.exists():
            messages.warning(request, 'No hay cuentas vencidas en la selección.')
            return
        
        # Crear workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Cuentas Vencidas'
        
        # Encabezados
        headers = [
            'Fecha Venta', 'Cliente', 'Carga', 'Monto Original', 
            'Saldo Pendiente', 'Fecha Vencimiento', 'Días Vencido', 
            'Calificación Cliente', 'Teléfono', 'Email'
        ]
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
            cell.font = Font(color='FFFFFF', bold=True)
        
        # Datos
        for row, venta in enumerate(vencidas, 2):
            ws.cell(row=row, column=1, value=venta.fecha_salida_manifiesto)
            ws.cell(row=row, column=2, value=venta.cliente.nombre)
            ws.cell(row=row, column=3, value=venta.carga)
            ws.cell(row=row, column=4, value=float(venta.monto.amount))
            ws.cell(row=row, column=5, value=venta.saldo_pendiente())
            ws.cell(row=row, column=6, value=venta.fecha_vencimiento)
            ws.cell(row=row, column=7, value=venta.dias_vencido())
            ws.cell(row=row, column=8, value=venta.cliente.calificacion_credito)
            ws.cell(row=row, column=9, value=venta.cliente.telefono)
            ws.cell(row=row, column=10, value=venta.cliente.correo)
        
        # Ajustar columnas
        for column in ws.columns:
            max_length = 0
            column = [cell for cell in column]
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            ws.column_dimensions[column[0].column_letter].width = adjusted_width
        
        # Respuesta HTTP
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename=cuentas_vencidas_{hoy.strftime("%Y%m%d")}.xlsx'
        
        wb.save(response)
        return response
    
    exportar_cuentas_vencidas.short_description = "📄 Exportar cuentas vencidas"
    
    # =============================================================================
    # VISTAS PERSONALIZADAS DE REPORTES
    # =============================================================================

    def ventas_balances_admin_view(self, request):
        """Vista de análisis de balances de ventas integrada en el admin de Django."""
        from ventas.views import build_ventas_balances_context
        from app.services.filter_utils import FilterOptionsProvider

        context = build_ventas_balances_context(request)
        context.update(self.admin_site.each_context(request))
        context.update({
            'title': 'Análisis de Ventas',
            'subtitle': None,
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
            'months': FilterOptionsProvider.get_months_list(),
        })
        return TemplateResponse(request, 'admin/ventas/ventas_balances.html', context)

    def reporte_cobranza_admin_view(self, request):
        """Vista del Reporte Global de Cobranza integrada en el admin de Django."""
        from ventas.views import reporte_cobranza_global
        from datetime import date
        from decimal import Decimal
        from ventas.services.reporte_cobranza_service import generar_reporte_cobranza

        hoy = date.today()
        default_inicio = date(hoy.year, 1, 1)
        default_fin = date(hoy.year, 12, 31)

        fecha_inicio_str = request.GET.get('fecha_inicio', default_inicio.isoformat())
        fecha_fin_str = request.GET.get('fecha_fin', default_fin.isoformat())
        tipo_cambio_str = request.GET.get('tipo_cambio', '')

        try:
            fecha_inicio = date.fromisoformat(fecha_inicio_str)
        except (ValueError, TypeError):
            fecha_inicio = default_inicio

        try:
            fecha_fin = date.fromisoformat(fecha_fin_str)
        except (ValueError, TypeError):
            fecha_fin = default_fin

        tipo_cambio_override = None
        if tipo_cambio_str:
            try:
                tipo_cambio_override = Decimal(tipo_cambio_str)
            except Exception:
                pass

        datos = generar_reporte_cobranza(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            tipo_cambio_override=tipo_cambio_override,
        )

        context = {**datos}
        context.update(self.admin_site.each_context(request))
        context.update({
            'title': 'Reporte Global de Cobranza',
            'subtitle': None,
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
            'fecha_inicio_str': fecha_inicio.isoformat(),
            'fecha_fin_str': fecha_fin.isoformat(),
            'tipo_cambio_input': tipo_cambio_str,
            'hoy': hoy,
        })
        return TemplateResponse(request, 'admin/ventas/reporte_cobranza.html', context)

    def dashboard_ventas(self, request):
        """Dashboard principal de ventas con métricas clave"""
        try:
            # Obtener métricas usando el servicio
            dso_metrics = CuentasPorCobrarMetrics.calcular_dso()
            
            # Métricas adicionales del período
            hoy = timezone.now().date()
            inicio_mes = hoy.replace(day=1)
            inicio_año = hoy.replace(month=1, day=1)
            
            # Ventas del mes actual
            ventas_mes = Ventas.objects.filter(
                fecha_salida_manifiesto__gte=inicio_mes
            ).aggregate(
                total=Sum('monto'),
                count=Count('id')
            )
            
            # Cuentas por cobrar vencidas
            vencidas = Ventas.objects.filter(
                modalidad_pago='Credito',
                fecha_vencimiento__lt=hoy,
                estado_cobranza__in=['Pendiente', 'Parcial']
            ).aggregate(
                total=Sum('monto'),
                count=Count('id')
            )
            
            # Top 5 clientes por volumen
            top_clientes = Ventas.objects.filter(
                fecha_salida_manifiesto__gte=inicio_año
            ).values('cliente__nombre').annotate(
                total_ventas=Sum('monto'),
                num_ventas=Count('id')
            ).order_by('-total_ventas')[:5]
            
            context = dict(
                self.admin_site.each_context(request),
                dso_metrics=dso_metrics,
                ventas_mes=ventas_mes,
                vencidas=vencidas,
                top_clientes=top_clientes,
                title='Dashboard de Ventas'
            )
            
            return TemplateResponse(request, 'admin/ventas/dashboard.html', context)
            
        except Exception as e:
            messages.error(request, f'Error al generar dashboard: {str(e)}')
            return redirect('admin:ventas_ventas_changelist')
    
    def reporte_detallado_cliente(self, request, cliente_id):
        """Vista de reporte detallado por cliente desde VentasAdmin"""
        from .models import Cliente as ClienteModel
        try:
            cliente = ClienteModel.objects.get(pk=cliente_id)
        except ClienteModel.DoesNotExist:
            messages.error(request, 'Cliente no encontrado')
            return redirect('admin:ventas_ventas_changelist')
        
        ventas_totales = cliente.ventas_set.aggregate(
            total=Sum('monto'),
            count=Count('id'),
            promedio=Avg('monto')
        )
        
        ventas_por_estado = cliente.ventas_set.values('estado_cobranza').annotate(
            total=Sum('monto'),
            count=Count('id')
        ).order_by('estado_cobranza')
        
        context = dict(
            self.admin_site.each_context(request),
            cliente=cliente,
            ventas_totales=ventas_totales,
            ventas_por_estado=ventas_por_estado,
            title=f'Reporte: {cliente.nombre}'
        )
        return TemplateResponse(request, 'admin/ventas/cliente/reporte_completo.html', context)
    
    def exportar_excel_personalizado(self, request):
        """Vista de exportación con opciones avanzadas"""
        return redirect('admin:ventas_ventas_changelist')
    
    def get_estado_cobranza(self, obj):
        colors = {
            'Pagado': 'green',
            'Pendiente': 'orange', 
            'Parcial': 'blue',
            'Vencido': 'red',
            'Incobrable': 'darkred'
        }
        color = colors.get(obj.estado_cobranza, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_estado_cobranza_display()
        )
    get_estado_cobranza.short_description = 'Estado Cobranza'
    
    def get_dias_vencimiento(self, obj):
        if obj.modalidad_pago == 'Contado':
            return '-'
        dias = obj.dias_vencido()
        if dias > 0:
            return format_html('<span style="color: red;">+{} días</span>', dias)
        elif dias < 0:
            return format_html('<span style="color: green;">{} días</span>', abs(dias))
        else:
            return 'Vence hoy'
    get_dias_vencimiento.short_description = 'Vencimiento'
    
    def get_mercado_destino(self, obj):
        return obj.mercado_destino.nombre if obj.mercado_destino else obj.tipo_venta
    get_mercado_destino.short_description = 'Mercado'

# Administración para PagoVenta
class PagoVentaResource(resources.ModelResource):
    venta = fields.Field(
        column_name='venta',
        attribute='venta',
        widget=ForeignKeyWidget(Ventas, field='carga'))
    
    cuenta_destino = fields.Field(
        column_name='cuenta_destino',
        attribute='cuenta_destino',
        widget=ForeignKeyWidget(Cuenta, field='numero_cuenta'))
    
    monto_pago = fields.Field(
        column_name='monto_pago',
        attribute='monto_pago',
        widget=MoneyWidget())

    class Meta:
        model = PagoVenta
        fields = ('id', 'fecha_pago', 'venta', 'monto_pago', 'cuenta_destino', 'metodo_pago', 'referencia')
        import_id_fields = ('id',)

@admin.register(PagoVenta)
class PagoVentaAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = PagoVentaResource
    list_display = ('fecha_pago', 'get_venta_info', 'monto_pago', 'metodo_pago', 'referencia', 'fecha_registro')
    list_filter = ('fecha_pago', 'metodo_pago', 'venta__cliente')
    search_fields = ('venta__carga', 'venta__cliente__nombre', 'referencia')
    date_hierarchy = 'fecha_pago'
    
    def get_venta_info(self, obj):
        return f"{obj.venta.carga} - {obj.venta.cliente.nombre}"
    get_venta_info.short_description = 'Venta - Cliente'
    
class AnticiposResource(resources.ModelResource):
    cliente = fields.Field(
        column_name='cliente',
        attribute='cliente',
        widget=ForeignKeyWidget(Cliente, field='nombre'))
    
    sucursal = fields.Field(
        column_name='sucursal',
        attribute='sucursal',
        widget=ForeignKeyWidget(Sucursal, field='nombre'))
    
    cuenta = fields.Field(
        column_name='cuenta',
        attribute='cuenta',
        widget=ForeignKeyWidget(Cuenta, field='numero_cuenta'))
    
    monto = fields.Field(
        column_name='monto',
        attribute='monto',
        widget=MoneyWidget())
    
    class Meta:
        model = Anticipo
        fields = ('id', 'fecha', 'cliente', 'sucursal', 'cuenta', 'monto', 'descripcion','estado_anticipo')
        import_id_fields = ('id',)
        
    def dehydrate_cliente(self, anticipo):
        return anticipo.cliente.nombre
    
    def dehydrate_sucursal(self, anticipo):
        return anticipo.sucursal.nombre
    
    def dehydrate_cuenta(self, anticipo):
        return anticipo.cuenta.numero_cuenta if anticipo.cuenta else ""

    def before_import_row(self, row, **kwargs):
        # Asigna un ID específico basado en un rango disponible
        if not row['id']:
            last_anticipo = Anticipo.objects.order_by('-id').first()
            next_id = last_anticipo.id + 1 if last_anticipo else 1
            row['id'] = next_id
     
@admin.register(Anticipo)
class AnticipoAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = AnticiposResource
    import_form_class = ImportForm
    export_form_class = ExportForm
    list_display = ('fecha', 'cliente', 'sucursal', 'cuenta', 'monto', 'descripcion','estado_anticipo')
    list_per_page = 20
    list_filter = ('fecha', 'cliente', 'sucursal', 'cuenta', 'monto', 'estado_anticipo')
    fields = ('fecha', 'cliente', 'sucursal', 'cuenta', 'monto', 'descripcion', 'estado_anticipo')        

# Administración para TerminoCredito
@admin.register(TerminoCredito)
class TerminoCreditoAdmin(ModelAdmin):
    list_display = ('nombre', 'dias_credito', 'tasa_interes_mensual', 'activo', 'fecha_creacion')
    list_filter = ('activo', 'dias_credito')
    search_fields = ('nombre',)
    list_editable = ('activo',)
    ordering = ['dias_credito']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'dias_credito', 'activo')
        }),
        ('Configuración Financiera', {
            'fields': ('tasa_interes_mensual', 'descripcion')
        }),
    )
    
    readonly_fields = ('fecha_creacion',)


# Administración para MercadoDestino  
# @admin.register(MercadoDestino)  # OCULTO DE LA SIDEBAR
class MercadoDestinoAdmin(ModelAdmin):
    list_display = (
        'nombre', 'get_num_paises', 'requiere_documentacion_especial', 
        'moneda_preferida', 'factor_riesgo', 'activo'
    )
    list_filter = ('activo', 'requiere_documentacion_especial', 'moneda_preferida')
    search_fields = ('nombre',)
    filter_horizontal = ('paises',)
    list_editable = ('activo', 'requiere_documentacion_especial')
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'activo')
        }),
        ('Países Asociados', {
            'fields': ('paises',)
        }),
        ('Configuración Comercial', {
            'fields': ('moneda_preferida', 'factor_riesgo', 'requiere_documentacion_especial')
        }),
    )
    
    readonly_fields = ('fecha_creacion',)
    
    def get_num_paises(self, obj):
        count = obj.paises.count()
        return format_html(
            '<span style="font-weight: bold;">{}</span> país{}',
            count, 'es' if count != 1 else ''
        )
    get_num_paises.short_description = 'Países'


# =========================================================================
# ADMINISTRACIÓN CUENTAS POR COBRAR
# =========================================================================

from .models import SaldoCliente, AntigüedadSaldo, EstadoCuentaCliente, ConfiguracionCuentasPorCobrar

# @admin.register(SaldoCliente)  # OCULTO DE LA SIDEBAR
class SaldoClienteAdmin(ModelAdmin):
    """
    Administración para Saldos de Clientes - RF1
    Permite visualizar y gestionar los saldos pendientes por cliente.
    """
    
    list_display = (
        'get_cliente_info', 'venta', 'fecha_creacion',
        'get_monto_original', 'get_saldo_pendiente', 'get_estado_visual',
        'get_dias_vencido', 'fecha_vencimiento'
    )
    
    list_filter = (
        'estado', 'fecha_vencimiento', 'fecha_creacion',
        'venta__modalidad_pago', 'venta__tipo_venta'
    )
    
    search_fields = (
        'cliente__nombre', 'venta__carga', 'venta__PO'
    )
    
    date_hierarchy = 'fecha_vencimiento'
    list_per_page = 25
    
    readonly_fields = (
        'venta', 'cliente', 'monto_original',
        'fecha_creacion', 'fecha_ultimo_pago',
        'get_monto_pagado', 'get_dias_vencido'
    )
    
    fieldsets = (
        ('Información de la Venta', {
            'fields': ('venta', 'cliente', 'monto_original')
        }),
        ('Estado del Saldo', {
            'fields': ('saldo_pendiente', 'estado', 'fecha_vencimiento', 'get_dias_vencido')
        }),
        ('Control de Pagos', {
            'fields': ('get_monto_pagado', 'fecha_ultimo_pago'),
            'classes': ('collapse',)
        }),
        ('Auditoria', {
            'fields': ('fecha_creacion',),
            'classes': ('collapse',)
        })
    )
    
    actions = ['marcar_como_incobrable', 'recalcular_saldos']
    
    def get_cliente_info(self, obj):
        return format_html(
            '<strong>{}</strong><br><small>{}</small>',
            obj.cliente.nombre,
            obj.cliente.pais.nombre if obj.cliente.pais else 'Sin país'
        )
    get_cliente_info.short_description = 'Cliente'
    
    def get_monto_original(self, obj):
        return format_html(
            '<span style="font-weight: bold;">${}</span>',
            f"{float(obj.monto_original.amount):,.2f}"
        )
    get_monto_original.short_description = 'Monto Original'
    
    def get_saldo_pendiente(self, obj):
        color = 'red' if obj.saldo_pendiente.amount > 0 else 'green'
        return format_html(
            '<span style="color: {}; font-weight: bold;">${}</span>',
            color, f"{float(obj.saldo_pendiente.amount):,.2f}"
        )
    get_saldo_pendiente.short_description = 'Saldo Pendiente'
    
    def get_estado_visual(self, obj):
        colors = {
            'P': 'orange',     # Pendiente
            'PP': 'blue',      # Pago Parcial  
            'PA': 'green',     # Pagado
            'V': 'red',        # Vencido
            'I': 'darkred',    # Incobrable
            'A': 'purple'      # Anulado
        }
        color = colors.get(obj.estado, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_estado_display()
        )
    get_estado_visual.short_description = 'Estado'
    
    def get_dias_vencido(self, obj):
        dias = obj.dias_vencido()
        if dias > 0:
            return format_html('<span style="color: red; font-weight: bold;">+{}</span>', dias)
        elif dias < 0:
            return format_html('<span style="color: green;">{}</span>', dias)
        else:
            return 'Vence hoy'
    get_dias_vencido.short_description = 'Días Vencido'
    
    def get_monto_pagado(self, obj):
        pagado = obj.monto_original - obj.saldo_pendiente 
        return f"${float(pagado.amount):,.2f}"
    get_monto_pagado.short_description = 'Monto Pagado'
    
    def marcar_como_incobrable(self, request, queryset):
        """Acción para marcar saldos como incobrables"""
        count = 0
        for saldo in queryset.filter(estado__in=['P', 'PP', 'V']):
            saldo.estado = SaldoCliente.EstadosSaldo.INCOBRABLE
            saldo.save()
            count += 1
        
        self.message_user(
            request, 
            f'{count} saldo(s) marcado(s) como incobrable(s).'
        )
    marcar_como_incobrable.short_description = "Marcar como incobrable"
    
    def recalcular_saldos(self, request, queryset):
        """Acción para recalcular saldos basado en pagos"""
        from .services.cuentas_por_cobrar_service import CuentasPorCobrarService
        
        count = 0
        for saldo in queryset:
            try:
                CuentasPorCobrarService.sincronizar_deuda_venta(saldo.venta.id)
                count += 1
            except Exception:
                pass
        
        self.message_user(
            request,
            f'{count} saldo(s) recalculado(s).'
        )
    recalcular_saldos.short_description = "Recalcular saldos"


# @admin.register(AntigüedadSaldo)  # OCULTO DE LA SIDEBAR
class AntigüedadSaldoAdmin(ModelAdmin):
    """
    Administración para Análisis de Antigüedad - RF3
    Permite visualizar el aging de cartera por cliente.
    """
    
    list_display = (
        'get_cliente_info', 'fecha_calculo', 'get_total_saldo',
        'get_corriente', 'get_vencido_1', 'get_vencido_2', 'get_vencido_3',
        'get_porcentaje_critico'
    )
    
    list_filter = ('fecha_calculo',)
    search_fields = ('cliente__nombre',)
    date_hierarchy = 'fecha_calculo'
    list_per_page = 50
    
    readonly_fields = (
        'fecha_calculo', 'cliente', 'total_saldo', 'corriente', 
        'vencido_1', 'vencido_2', 'vencido_3', 'calculado_por'
    )
    
    fieldsets = (
        ('Cliente y Fecha', {
            'fields': ('cliente', 'fecha_calculo')
        }),
        ('Distribución por Antigüedad', {
            'fields': ('total_saldo', 'corriente', 'vencido_1', 'vencido_2', 'vencido_3')
        }),
        ('Auditoria', {
            'fields': ('calculado_por',),
            'classes': ('collapse',)
        })
    )
    
    actions = ['exportar_aging_excel']
    
    def get_cliente_info(self, obj):
        return format_html(
            '<strong>{}</strong><br><small>ID: {}</small>',
            obj.cliente.nombre, obj.cliente.id
        )
    get_cliente_info.short_description = 'Cliente'
    
    def get_total_saldo(self, obj):
        return format_html(
            '<span style="font-weight: bold; color: navy;">${}</span>',
            f"{float(obj.total_saldo.amount):,.2f}"
        )
    get_total_saldo.short_description = 'Total Saldo'
    
    def get_corriente(self, obj):
        return format_html(
            '<span style="color: green;">${}</span>',
            f"{float(obj.corriente.amount):,.2f}"
        )
    get_corriente.short_description = 'Corriente'
    
    def get_vencido_1(self, obj):
        return format_html(
            '<span style="color: orange;">${}</span>',
            f"{float(obj.vencido_1.amount):,.2f}"
        )
    get_vencido_1.short_description = '1-30 días'
    
    def get_vencido_2(self, obj):
        return format_html(
            '<span style="color: red;">${}</span>',
            f"{float(obj.vencido_2.amount):,.2f}"
        )
    get_vencido_2.short_description = '31-60 días'
    
    def get_vencido_3(self, obj):
        return format_html(
            '<span style="color: darkred; font-weight: bold;">${}</span>',
            f"{float(obj.vencido_3.amount):,.2f}"
        )
    get_vencido_3.short_description = '+60 días'
    
    def get_porcentaje_critico(self, obj):
        """Muestra porcentaje de cartera crítica (>60 días)"""
        if obj.total_saldo.amount > 0:
            pct = (obj.vencido_3.amount / obj.total_saldo.amount) * 100
            color = 'red' if pct > 25 else 'orange' if pct > 10 else 'green'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
                color, pct
            )
        return '0%'
    get_porcentaje_critico.short_description = '% Crítico'
    
    def exportar_aging_excel(self, request, queryset):
        """Exporta análisis de aging a Excel"""
        # Esta funcionalidad se implementaría con openpyxl
        self.message_user(request, "Funcionalidad de exportación en desarrollo")
    exportar_aging_excel.short_description = "Exportar a Excel"


@admin.register(EstadoCuentaCliente)  
class EstadoCuentaClienteAdmin(ModelAdmin):
    """
    Administración para Estados de Cuenta - RF4
    Permite visualizar el historial completo por cliente.
    """
    
    list_display = (
        'get_cliente_info', 'fecha_generacion',
        'periodo_inicio', 'periodo_fin', 'get_total_ventas',
        'get_total_abonos', 'get_saldo_final', 'formato_generado'
    )
    
    list_filter = ('fecha_generacion', 'periodo_inicio', 'periodo_fin', 'formato_generado')
    search_fields = ('cliente__nombre', 'generado_por')
    date_hierarchy = 'fecha_generacion'
    list_per_page = 20
    
    readonly_fields = (
        'fecha_generacion', 'total_ventas', 'total_abonos',
        'saldo_final', 'numero_facturas'
    )
    
    fieldsets = (
        ('Información del Reporte', {
            'fields': ('cliente', 'fecha_generacion', 'generado_por')
        }),
        ('Período de Análisis', {
            'fields': ('periodo_inicio', 'periodo_fin')
        }),
        ('Resumen Financiero', {
            'fields': ('total_ventas', 'total_abonos', 'saldo_final', 'numero_facturas')
        }),
        ('Archivo', {
            'fields': ('formato_generado', 'archivo_generado', 'notas'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['regenerar_reporte', 'enviar_por_email']
    
    def get_cliente_info(self, obj):
        return format_html(
            '<strong>{}</strong><br><small>{}</small>',
            obj.cliente.nombre,
            obj.cliente.correo if obj.cliente.correo else 'Sin email'
        )
    get_cliente_info.short_description = 'Cliente'
    
    def get_total_ventas(self, obj):
        return format_html(
            '<span style="color: navy; font-weight: bold;">${}</span>',
            f"{float(obj.total_ventas.amount):,.2f}"
        )
    get_total_ventas.short_description = 'Total Ventas'

    def get_total_abonos(self, obj):
        return format_html(
            '<span style="color: green;">${}</span>',
            f"{float(obj.total_abonos.amount):,.2f}"
        )
    get_total_abonos.short_description = 'Total Abonos'
    
    def get_saldo_final(self, obj):
        color = 'red' if obj.saldo_final.amount > 0 else 'green'
        return format_html(
            '<span style="color: {}; font-weight: bold;">${}</span>',
            color, f"{float(obj.saldo_final.amount):,.2f}"
        )
    get_saldo_final.short_description = 'Saldo Final'
    
    def regenerar_reporte(self, request, queryset):
        """Regenera reportes de estado de cuenta"""
        from .services.cuentas_por_cobrar_service import CuentasPorCobrarService
        
        count = 0
        for estado in queryset:
            try:
                CuentasPorCobrarService.generar_estado_cuenta(
                    estado.cliente.id,
                    estado.periodo_inicio,
                    estado.periodo_fin
                )
                count += 1
            except Exception:
                pass
        
        self.message_user(request, f'{count} reporte(s) regenerado(s)')
    regenerar_reporte.short_description = "Regenerar reportes"
    
    def enviar_por_email(self, request, queryset):
        """Envía estados de cuenta por email"""
        # Funcionalidad para implementar con sistema de emails
        self.message_user(request, "Funcionalidad de envío por email en desarrollo")
    enviar_por_email.short_description = "Enviar por email"


# @admin.register(ConfiguracionCuentasPorCobrar)  # OCULTO DE LA SIDEBAR
class ConfiguracionCuentasPorCobrarAdmin(ModelAdmin):
    """
    Administración para Configuración del Sistema CxC
    Permite configurar parámetros globales del sistema.
    """
    
    list_display = (
        'get_config_str', 'dias_corriente', 'calculo_automatico_aging',
        'frecuencia_calculo', 'enviar_alertas_vencimiento', 'fecha_creacion'
    )
    
    list_filter = ('calculo_automatico_aging', 'frecuencia_calculo', 'enviar_alertas_vencimiento')
    search_fields = ('email_responsable_cobranza',)
    
    fieldsets = (
        ('Parámetros de Antigüedad (Aging)', {
            'fields': ('dias_corriente', 'dias_vencido_1', 'dias_vencido_2')
        }),
        ('Automatización', {
            'fields': ('calculo_automatico_aging', 'hora_calculo_aging', 'frecuencia_calculo')
        }),
        ('Alertas y Notificaciones', {
            'fields': ('enviar_alertas_vencimiento', 'dias_previos_alerta', 'email_responsable_cobranza')
        }),
        ('Límites de Crédito', {
            'fields': ('permitir_sobregiro_credito', 'porcentaje_sobregiro_permitido'),
            'classes': ('collapse',)
        }),
        ('Auditoria', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('fecha_creacion', 'fecha_modificacion')

    def get_config_str(self, obj):
        return str(obj)
    get_config_str.short_description = 'Configuración'

# Administración para MercadoDestino
class PaisInline(admin.TabularInline):
    model = MercadoDestino.paises.through
list_editable = ('activo',)
inlines = [PaisInline]
exclude = ('paises',)

# Inline para PagoVenta - debe definirse antes de VentasAdmin
class PagoVentaInline(admin.TabularInline):
    model = PagoVenta
    extra = 0
    readonly_fields = ('fecha_registro',)
    fields = ('fecha_pago', 'monto_pago', 'cuenta_destino', 'metodo_pago', 'referencia', 'notas')


# =============================================================================
# OBLIGACIONES FISCALES
# =============================================================================

@admin.register(ObligacionFiscal)
class ObligacionFiscalAdmin(ModelAdmin):
    list_display = ('periodo', 'isr_ingresos_propios', 'isr_resico',
                    'isr_retenciones_salarios', 'iva_retenciones_profesionales',
                    'get_total', 'fecha_registro')
    list_filter = ('fecha_registro',)
    search_fields = ('periodo',)
    readonly_fields = ('fecha_registro',)

    fieldsets = (
        ('Período', {
            'fields': ('periodo', 'fecha_registro')
        }),
        ('Impuestos', {
            'fields': (
                'isr_ingresos_propios',
                'isr_resico',
                'isr_retenciones_salarios',
                'iva_retenciones_profesionales',
            )
        }),
    )

    def get_total(self, obj):
        total = float(obj.total_impuestos())
        return format_html('<strong>${}</strong>', f'{total:,.2f}')
    get_total.short_description = 'Total Impuestos'