from django.contrib import admin
from django.contrib.admin import ModelAdmin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin
from import_export.forms import ExportForm, ImportForm
from .models import CatInversion, Inversion, RendimientoInversion
from catalogo.models import Sucursal
from gastos.models import Cuenta
from app.widgets import MoneyWidget
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe


# ==================== CATEGORÍAS DE INVERSIÓN ====================

class CatInversionResource(resources.ModelResource):
    """Resource para importar/exportar categorías de inversión"""
    
    class Meta:
        model = CatInversion
        fields = ('id', 'nombre', 'descripcion', 'activa', 'fecha_registro')
        export_order = fields


@admin.register(CatInversion)
class CatInversionAdmin(ImportExportModelAdmin, ModelAdmin):
    """Administración de Categorías de Inversión"""
    
    resource_class = CatInversionResource
    import_form_class = ImportForm
    export_form_class = ExportForm
    
    list_display = ('id', 'nombre', 'activa', 'descripcion_corta', 'fecha_registro')
    list_filter = ('activa', 'fecha_registro')
    search_fields = ('nombre', 'descripcion')
    list_per_page = 20
    
    fieldsets = (
        ('Información de la Categoría', {
            'fields': ('nombre', 'descripcion', 'activa')
        }),
        ('Metadatos', {
            'fields': ('fecha_registro',),
            'classes': ('collapse',)
        })
    )
    
    def descripcion_corta(self, obj):
        """Muestra descripción truncada"""
        if obj.descripcion:
            return obj.descripcion[:50] + '...' if len(obj.descripcion) > 50 else obj.descripcion
        return '-'
    descripcion_corta.short_description = 'Descripción'


# ==================== INVERSIONES ====================

class InversionResource(resources.ModelResource):
    """Resource para importar/exportar inversiones"""
    
    sucursal = fields.Field(
        column_name='sucursal',
        attribute='id_sucursal',
        widget=ForeignKeyWidget(Sucursal, field='nombre')
    )
    
    categoria = fields.Field(
        column_name='categoria',
        attribute='id_cat_inversion',
        widget=ForeignKeyWidget(CatInversion, field='nombre')
    )
    
    cuenta = fields.Field(
        column_name='cuenta',
        attribute='id_cuenta_banco',
        widget=ForeignKeyWidget(Cuenta, field='numero_cuenta')
    )
    
    monto = fields.Field(
        column_name='monto',
        attribute='monto',
        widget=MoneyWidget()
    )
    
    class Meta:
        model = Inversion
        fields = (
            'id', 
            'sucursal', 
            'categoria', 
            'cuenta', 
            'tipo_movimiento',
            'monto', 
            'fecha', 
            'descripcion',
            'notas',
            'fecha_registro'
        )
        export_order = fields
        import_id_fields = ('id',)
    
    def dehydrate_sucursal(self, inversion):
        return inversion.id_sucursal.nombre
    
    def dehydrate_categoria(self, inversion):
        return inversion.id_cat_inversion.nombre
    
    def dehydrate_cuenta(self, inversion):
        return inversion.id_cuenta_banco.numero_cuenta


@admin.register(Inversion)
class InversionAdmin(ImportExportModelAdmin, ModelAdmin):
    """Administración de Inversiones y Capital"""
    
    resource_class = InversionResource
    import_form_class = ImportForm
    export_form_class = ExportForm
    
    list_display = (
        'id',
        'tipo_movimiento_badge',
        'fecha',
        'id_sucursal',
        'id_cat_inversion',
        'monto',
        'id_cuenta_banco',
        'tiene_documento',
        'rendimientos_count'
    )
    
    list_filter = (
        'tipo_movimiento',
        'id_sucursal',
        'id_cat_inversion',
        'fecha',
        'id_cuenta_banco'
    )
    
    search_fields = (
        'id',
        'descripcion',
        'notas',
        'id_sucursal__nombre',
        'id_cat_inversion__nombre',
        'id_cuenta_banco__numero_cuenta'
    )
    
    date_hierarchy = 'fecha'
    list_per_page = 25
    
    fieldsets = (
        ('Datos Principales', {
            'fields': (
                'id_sucursal',
                'id_cat_inversion',
                'tipo_movimiento',
                'monto',
                'fecha'
            )
        }),
        ('Cuenta Bancaria', {
            'fields': ('id_cuenta_banco',)
        }),
        ('Descripción', {
            'fields': ('descripcion', 'notas')
        }),
        ('Documentación', {
            'fields': ('documento_soporte',),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('fecha_registro', 'ultima_modificacion'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('fecha_registro', 'ultima_modificacion')
    
    def tipo_movimiento_badge(self, obj):
        """Muestra el tipo de movimiento con color"""
        if obj.tipo_movimiento == 'ENTRADA':
            color = '#28a745'  # verde
            icon = '↓'
        else:
            color = '#dc3545'  # rojo
            icon = '↑'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">'
            '{} {}</span>',
            color, icon, obj.get_tipo_movimiento_display()
        )
    tipo_movimiento_badge.short_description = 'Tipo'
    tipo_movimiento_badge.admin_order_field = 'tipo_movimiento'
    
    def tiene_documento(self, obj):
        """Indica si tiene documento adjunto"""
        if obj.documento_soporte:
            return format_html(
                '<span style="color: green;">✓ Sí</span>'
            )
        return format_html('<span style="color: gray;">✗ No</span>')
    tiene_documento.short_description = 'Documento'
    
    def rendimientos_count(self, obj):
        """Muestra cantidad de rendimientos registrados"""
        count = obj.rendimientos.count()
        if count > 0:
            return format_html(
                '<span style="background-color: #007bff; color: white; padding: 2px 6px; border-radius: 10px;">{}</span>',
                count
            )
        return '-'
    rendimientos_count.short_description = 'Rendimientos'
    
    actions = ['marcar_como_entrada', 'marcar_como_salida']
    
    def marcar_como_entrada(self, request, queryset):
        """Marca inversiones seleccionadas como entrada de capital"""
        updated = queryset.update(tipo_movimiento='ENTRADA')
        self.message_user(request, f'{updated} inversión(es) marcada(s) como ENTRADA de capital.')
    marcar_como_entrada.short_description = "Marcar como Entrada de Capital"
    
    def marcar_como_salida(self, request, queryset):
        """Marca inversiones seleccionadas como salida de capital (inversión)"""
        updated = queryset.update(tipo_movimiento='SALIDA')
        self.message_user(request, f'{updated} inversión(es) marcada(s) como SALIDA de capital.')
    marcar_como_salida.short_description = "Marcar como Salida de Capital"


# ==================== RENDIMIENTOS ====================

class RendimientoInversionResource(resources.ModelResource):
    """Resource para importar/exportar rendimientos"""
    
    inversion_id = fields.Field(
        column_name='inversion_id',
        attribute='inversion',
        widget=ForeignKeyWidget(Inversion, field='id')
    )
    
    monto_rendimiento = fields.Field(
        column_name='monto_rendimiento',
        attribute='monto_rendimiento',
        widget=MoneyWidget()
    )
    
    class Meta:
        model = RendimientoInversion
        fields = (
            'id',
            'inversion_id',
            'fecha_rendimiento',
            'monto_rendimiento',
            'porcentaje_rendimiento',
            'tipo_rendimiento',
            'descripcion',
            'fecha_registro'
        )
        export_order = fields
        import_id_fields = ('id',)


class RendimientoInline(admin.TabularInline):
    """Inline para mostrar rendimientos en el detalle de inversión"""
    model = RendimientoInversion
    extra = 1
    fields = ('fecha_rendimiento', 'monto_rendimiento', 'porcentaje_rendimiento', 'tipo_rendimiento', 'descripcion')
    readonly_fields = ('porcentaje_rendimiento',)


@admin.register(RendimientoInversion)
class RendimientoInversionAdmin(ImportExportModelAdmin, ModelAdmin):
    """Administración de Rendimientos de Inversiones"""
    
    resource_class = RendimientoInversionResource
    import_form_class = ImportForm
    export_form_class = ExportForm
    
    list_display = (
        'id',
        'inversion_link',
        'fecha_rendimiento',
        'monto_rendimiento',
        'porcentaje_rendimiento_formatted',
        'tipo_rendimiento'
    )
    
    list_filter = (
        'tipo_rendimiento',
        'fecha_rendimiento',
        'inversion__id_sucursal',
        'inversion__id_cat_inversion'
    )
    
    search_fields = (
        'inversion__id',
        'inversion__descripcion',
        'descripcion',
        'tipo_rendimiento'
    )
    
    date_hierarchy = 'fecha_rendimiento'
    list_per_page = 20
    
    fieldsets = (
        ('Inversión Relacionada', {
            'fields': ('inversion',)
        }),
        ('Datos del Rendimiento', {
            'fields': (
                'fecha_rendimiento',
                'monto_rendimiento',
                'porcentaje_rendimiento',
                'tipo_rendimiento'
            )
        }),
        ('Descripción', {
            'fields': ('descripcion',)
        }),
        ('Metadatos', {
            'fields': ('fecha_registro',),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('porcentaje_rendimiento', 'fecha_registro')
    
    def inversion_link(self, obj):
        """Crea un link a la inversión relacionada"""
        url = reverse('admin:capital_inversiones_inversion_change', args=[obj.inversion.id])
        return format_html(
            '<a href="{}">Inv #{} - {}</a>',
            url,
            obj.inversion.id,
            obj.inversion.id_cat_inversion.nombre
        )
    inversion_link.short_description = 'Inversión'
    
    def porcentaje_rendimiento_formatted(self, obj):
        """Formatea el porcentaje de rendimiento"""
        if obj.porcentaje_rendimiento:
            return format_html(
                '<span style="font-weight: bold; color: #28a745;">{}%</span>',
                round(obj.porcentaje_rendimiento, 2)
            )
        return '-'
    porcentaje_rendimiento_formatted.short_description = '% Rendimiento'
    porcentaje_rendimiento_formatted.admin_order_field = 'porcentaje_rendimiento'


# Agregar el inline de rendimientos al admin de Inversion
InversionAdmin.inlines = [RendimientoInline]
