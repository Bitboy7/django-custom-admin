# ventas/services/cache_service.py

"""
Servicio de cache para cuentas por cobrar.
Gestiona el cache de métricas y datos calculados para mejorar performance.
"""

from django.core.cache import cache
from django.db.models import Sum, Count, Avg, Max
from django.utils import timezone
from datetime import timedelta
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class CuentasPorCobrarCache:
    """
    Gestión de cache para métricas de cuentas por cobrar.
    Usa Redis existente con fallback a cache local.
    """
    
    # Configuración de timeouts
    CACHE_TIMEOUT_SHORT = 300    # 5 minutos
    CACHE_TIMEOUT_MEDIUM = 900   # 15 minutos  
    CACHE_TIMEOUT_LONG = 3600    # 1 hora
    
    # Prefijos para organizar las keys
    PREFIX_CLIENTE = 'cxc_cliente'
    PREFIX_DASHBOARD = 'cxc_dashboard'
    PREFIX_AGING = 'cxc_aging'
    PREFIX_METRICAS = 'cxc_metricas'
    
    @classmethod
    def get_metricas_cliente(cls, cliente_id: int) -> Optional[Dict]:
        """
        Obtiene métricas de cuentas por cobrar para un cliente específico.
        Cache de 15 minutos para balance entre performance y frescura.
        """
        cache_key = f'{cls.PREFIX_CLIENTE}_{cliente_id}'
        
        metricas = cache.get(cache_key)
        if metricas is None:
            try:
                metricas = cls._calcular_metricas_cliente(cliente_id)
                cache.set(cache_key, metricas, cls.CACHE_TIMEOUT_MEDIUM)
                logger.debug(f"Métricas cliente {cliente_id} calculadas y cacheadas")
            except Exception as e:
                logger.error(f"Error calculando métricas cliente {cliente_id}: {e}")
                return None
                
        return metricas
    
    @classmethod
    def get_dashboard_global(cls) -> Optional[Dict]:
        """
        Obtiene métricas del dashboard global de cuentas por cobrar.
        Cache de 5 minutos para datos más actualizados en vista principal.
        """
        cache_key = f'{cls.PREFIX_DASHBOARD}_global'
        
        dashboard = cache.get(cache_key)
        if dashboard is None:
            try:
                dashboard = cls._calcular_dashboard_global()
                cache.set(cache_key, dashboard, cls.CACHE_TIMEOUT_SHORT)
                logger.debug("Dashboard global calculado y cacheado")
            except Exception as e:
                logger.error(f"Error calculando dashboard global: {e}")
                return None
                
        return dashboard
    
    @classmethod
    def get_aging_consolidado(cls, fecha_corte: str = None) -> Optional[Dict]:
        """
        Obtiene aging consolidado de todos los clientes.
        Cache de 1 hora ya que aging no cambia frecuentemente.
        """
        fecha_key = fecha_corte or timezone.now().date().isoformat()
        cache_key = f'{cls.PREFIX_AGING}_consolidado_{fecha_key}'
        
        aging = cache.get(cache_key)
        if aging is None:
            try:
                aging = cls._calcular_aging_consolidado(fecha_corte)
                cache.set(cache_key, aging, cls.CACHE_TIMEOUT_LONG)
                logger.debug(f"Aging consolidado calculado para {fecha_key}")
            except Exception as e:
                logger.error(f"Error calculando aging consolidado: {e}")
                return None
                
        return aging
    
    @classmethod
    def get_top_deudores(cls, limite: int = 10) -> Optional[Dict]:
        """
        Obtiene top N clientes con mayor saldo pendiente.
        Cache de 15 minutos para reportes frecuentes.
        """
        cache_key = f'{cls.PREFIX_METRICAS}_top_deudores_{limite}'
        
        top_deudores = cache.get(cache_key)
        if top_deudores is None:
            try:
                top_deudores = cls._calcular_top_deudores(limite)
                cache.set(cache_key, top_deudores, cls.CACHE_TIMEOUT_MEDIUM)
                logger.debug(f"Top {limite} deudores calculado y cacheado")
            except Exception as e:
                logger.error(f"Error calculando top deudores: {e}")
                return None
                
        return top_deudores
    
    @classmethod
    def invalidar_cliente(cls, cliente_id: int):
        """
        Invalida todos los caches relacionados con un cliente específico.
        Se llama cuando hay cambios en saldos, pagos, etc.
        """
        cache_keys = [
            f'{cls.PREFIX_CLIENTE}_{cliente_id}',
            f'{cls.PREFIX_DASHBOARD}_global',
            f'{cls.PREFIX_METRICAS}_top_deudores_10',
            f'{cls.PREFIX_METRICAS}_top_deudores_20'
        ]
        
        # También invalidar aging si tienen fecha de hoy
        fecha_hoy = timezone.now().date().isoformat()
        cache_keys.append(f'{cls.PREFIX_AGING}_consolidado_{fecha_hoy}')
        
        deleted = cache.delete_many(cache_keys)
        logger.debug(f"Cache invalidado para cliente {cliente_id}: {deleted} keys eliminadas")
    
    @classmethod
    def invalidar_global(cls):
        """
        Invalida todos los caches globales.
        Se usa para operaciones masivas o mantenimiento.
        """
        # Obtener todas las keys que empiecen con nuestros prefijos
        # Nota: Esto depende del backend de cache
        try:
            if hasattr(cache, 'delete_pattern'):
                # Redis backend
                patterns = [
                    f'{cls.PREFIX_CLIENTE}_*',
                    f'{cls.PREFIX_DASHBOARD}_*',
                    f'{cls.PREFIX_AGING}_*',
                    f'{cls.PREFIX_METRICAS}_*'
                ]
                for pattern in patterns:
                    cache.delete_pattern(pattern)
            else:
                # Fallback: invalidar keys conocidas
                cache.clear()
                
            logger.info("Cache global de CuentasPorCobrar invalidado")
        except Exception as e:
            logger.warning(f"No se pudo invalidar cache completamente: {e}")
    
    @classmethod  
    def warm_up_cache(cls, cliente_ids: list = None):
        """
        Pre-carga cache para clientes especificados o principales.
        Útil para mejorar performance en horarios pico.
        """
        if cliente_ids is None:
            # Obtener top 20 clientes por saldo
            from ..models import SaldoCliente
            cliente_ids = list(SaldoCliente.objects.values('cliente_id').annotate(
                total=Sum('saldo_pendiente')
            ).order_by('-total')[:20].values_list('cliente_id', flat=True))
        
        cacheados = 0
        for cliente_id in cliente_ids:
            try:
                cls.get_metricas_cliente(cliente_id)
                cacheados += 1
            except Exception as e:
                logger.warning(f"Error pre-cargando cache para cliente {cliente_id}: {e}")
        
        # Pre-cargar dashboard global
        try:
            cls.get_dashboard_global()
            cls.get_top_deudores()
            cls.get_aging_consolidado()
        except Exception as e:
            logger.warning(f"Error pre-cargando caches globales: {e}")
        
        logger.info(f"Cache pre-cargado para {cacheados} clientes")
        return cacheados
    
    # =========================================================================
    # MÉTODOS PRIVADOS DE CÁLCULO
    # =========================================================================
    
    @staticmethod
    def _calcular_metricas_cliente(cliente_id: int) -> Dict:
        """Calcula métricas frescas por cliente"""
        from ..models import SaldoCliente, PagoVenta, Cliente
        
        try:
            cliente = Cliente.objects.get(id=cliente_id)
        except Cliente.DoesNotExist:
            return {}
        
        # Saldos actuales
        saldos = SaldoCliente.objects.filter(cliente_id=cliente_id)
        saldos_activos = saldos.exclude(estado=SaldoCliente.EstadosSaldo.PAGADO)
        
        metricas_saldos = saldos_activos.aggregate(
            total_saldo=Sum('saldo_pendiente'),
            numero_facturas=Count('id'),
            saldo_vencido=Sum('saldo_pendiente', 
                filter=models.Q(fecha_vencimiento__lt=timezone.now().date())),
            ultimo_saldo_creado=Max('fecha_creacion')
        )
        
        # Historial de pagos
        metricas_pagos = PagoVenta.objects.filter(venta__cliente_id=cliente_id).aggregate(
            total_pagos=Sum('monto_pago'),
            numero_pagos=Count('id'),
            ultimo_pago=Max('fecha_pago'),
            promedio_pago=Avg('monto_pago')
        )
        
        # Información de crédito
        limite_credito = float(cliente.limite_credito.amount) if cliente.limite_credito else 0
        saldo_total = float(metricas_saldos['total_saldo'] or 0)
        credito_disponible = cliente.credito_disponible()
        
        return {
            'cliente_id': cliente_id,
            'cliente_nombre': cliente.nombre,
            'fecha_calculo': timezone.now().isoformat(),
            
            # Saldos
            'total_saldo': saldo_total,
            'numero_facturas': metricas_saldos['numero_facturas'] or 0,
            'saldo_vencido': float(metricas_saldos['saldo_vencido'] or 0),
            'ultimo_saldo_creado': metricas_saldos['ultimo_saldo_creado'],
            
            # Pagos
            'total_pagos_historico': float(metricas_pagos['total_pagos'] or 0),
            'numero_pagos': metricas_pagos['numero_pagos'] or 0,
            'ultimo_pago': metricas_pagos['ultimo_pago'],
            'promedio_pago': float(metricas_pagos['promedio_pago'] or 0),
            
            # Crédito
            'limite_credito': limite_credito,
            'credito_disponible': credito_disponible,
            'utilizacion_credito': round((saldo_total / limite_credito * 100) if limite_credito > 0 else 0, 2),
            
            # Flags de estado
            'tiene_saldos_vencidos': metricas_saldos['saldo_vencido'] and metricas_saldos['saldo_vencido'] > 0,
            'excede_limite': saldo_total > limite_credito,
            'cliente_activo': saldos_activos.exists()
        }
    
    @staticmethod
    def _calcular_dashboard_global() -> Dict:
        """Calcula métricas globales del dashboard"""
        from ..models import SaldoCliente, PagoVenta, Cliente, AntigüedadSaldo
        
        # Saldos globales
        saldos_globales = SaldoCliente.objects.exclude(
            estado=SaldoCliente.EstadosSaldo.PAGADO
        ).aggregate(
            total_cartera=Sum('saldo_pendiente'),
            numero_facturas=Count('id'),
            cartera_vencida=Sum('saldo_pendiente', 
                filter=models.Q(fecha_vencimiento__lt=timezone.now().date())),
            clientes_con_saldo=Count('cliente', distinct=True)
        )
        
        # Pagos de hoy
        hoy = timezone.now().date()
        pagos_hoy = PagoVenta.objects.filter(fecha_pago=hoy).aggregate(
            total_cobrado_hoy=Sum('monto_pago'),
            numero_pagos_hoy=Count('id')
        )
        
        # Aging más reciente
        aging_reciente = AntigüedadSaldo.objects.filter(
            fecha_calculo=hoy
        ).aggregate(
            total_corriente=Sum('corriente'),
            total_vencido_1=Sum('vencido_1'),
            total_vencido_2=Sum('vencido_2'),
            total_vencido_3=Sum('vencido_3')
        )
        
        # Alertas y casos críticos
        facturas_vencen_hoy = SaldoCliente.objects.filter(
            fecha_vencimiento=hoy,
            estado__in=[SaldoCliente.EstadosSaldo.PENDIENTE, SaldoCliente.EstadosSaldo.PARCIAL]
        ).count()
        
        clientes_limite_excedido = Cliente.objects.filter(
            saldos_cxc__saldo_pendiente__gt=models.F('limite_credito')
        ).distinct().count()
        
        return {
            'fecha_calculo': timezone.now().isoformat(),
            
            # Cartera total
            'total_cartera': float(saldos_globales['total_cartera'] or 0),
            'numero_facturas_pendientes': saldos_globales['numero_facturas'] or 0,
            'cartera_vencida': float(saldos_globales['cartera_vencida'] or 0),
            'clientes_con_saldo': saldos_globales['clientes_con_saldo'] or 0,
            
            # Actividad del día
            'cobrado_hoy': float(pagos_hoy['total_cobrado_hoy'] or 0),
            'pagos_hoy': pagos_hoy['numero_pagos_hoy'] or 0,
            
            # Distribución aging
            'aging_corriente': float(aging_reciente['total_corriente'] or 0),
            'aging_vencido_1': float(aging_reciente['total_vencido_1'] or 0),
            'aging_vencido_2': float(aging_reciente['total_vencido_2'] or 0),
            'aging_vencido_3': float(aging_reciente['total_vencido_3'] or 0),
            
            # Alertas
            'facturas_vencen_hoy': facturas_vencen_hoy,
            'clientes_limite_excedido': clientes_limite_excedido,
            
            # KPIs calculados
            'porcentaje_cartera_vencida': round(
                (float(saldos_globales['cartera_vencida'] or 0) / 
                 float(saldos_globales['total_cartera'] or 1) * 100), 2
            ),
            'promedio_saldo_por_cliente': round(
                (float(saldos_globales['total_cartera'] or 0) / 
                 max(saldos_globales['clientes_con_saldo'] or 1, 1)), 2
            )
        }
    
    @staticmethod
    def _calcular_aging_consolidado(fecha_corte: str = None) -> Dict:
        """Calcula aging consolidado de todos los clientes"""
        from ..models import AntigüedadSaldo
        
        if fecha_corte:
            try:
                fecha_obj = timezone.datetime.fromisoformat(fecha_corte).date()
            except:
                fecha_obj = timezone.now().date()
        else:
            fecha_obj = timezone.now().date()
        
        aging_datos = AntigüedadSaldo.objects.filter(
            fecha_calculo=fecha_obj
        ).aggregate(
            total_corriente=Sum('corriente'),
            total_vencido_1=Sum('vencido_1'),
            total_vencido_2=Sum('vencido_2'),
            total_vencido_3=Sum('vencido_3'),
            total_clientes=Count('cliente'),
            total_facturas=Sum('numero_facturas')
        )
        
        total_cartera = sum([
            float(aging_datos['total_corriente'] or 0),
            float(aging_datos['total_vencido_1'] or 0),
            float(aging_datos['total_vencido_2'] or 0),
            float(aging_datos['total_vencido_3'] or 0)
        ])
        
        # Calcular distribución porcentual
        distribucion = {}
        if total_cartera > 0:
            distribucion = {
                'corriente_pct': round((float(aging_datos['total_corriente'] or 0) / total_cartera) * 100, 2),
                'vencido_1_pct': round((float(aging_datos['total_vencido_1'] or 0) / total_cartera) * 100, 2),
                'vencido_2_pct': round((float(aging_datos['total_vencido_2'] or 0) / total_cartera) * 100, 2),
                'vencido_3_pct': round((float(aging_datos['total_vencido_3'] or 0) / total_cartera) * 100, 2)
            }
        
        return {
            'fecha_corte': fecha_obj.isoformat(),
            'total_cartera': total_cartera,
            'clientes_analizados': aging_datos['total_clientes'] or 0,
            'facturas_analizadas': aging_datos['total_facturas'] or 0,
            
            # Montos por bucket
            'corriente': float(aging_datos['total_corriente'] or 0),
            'vencido_1': float(aging_datos['total_vencido_1'] or 0), 
            'vencido_2': float(aging_datos['total_vencido_2'] or 0),
            'vencido_3': float(aging_datos['total_vencido_3'] or 0),
            
            # Distribución porcentual
            'distribucion': distribucion,
            
            # Métricas derivadas
            'cartera_critica': float(aging_datos['total_vencido_2'] or 0) + float(aging_datos['total_vencido_3'] or 0),
            'cartera_sana': float(aging_datos['total_corriente'] or 0) + float(aging_datos['total_vencido_1'] or 0)
        }
    
    @staticmethod
    def _calcular_top_deudores(limite: int = 10) -> Dict:
        """Calcula top N clientes con mayor saldo"""
        from ..models import SaldoCliente
        
        top_saldos = SaldoCliente.objects.values(
            'cliente__nombre', 'cliente__id'
        ).annotate(
            total_saldo=Sum('saldo_pendiente'),
            numero_facturas=Count('id'),
            saldo_vencido=Sum('saldo_pendiente', 
                filter=models.Q(fecha_vencimiento__lt=timezone.now().date())),
            dias_promedio_vencido=Avg(
                timezone.now().date() - models.F('fecha_vencimiento'),
                filter=models.Q(fecha_vencimiento__lt=timezone.now().date())
            )
        ).filter(
            total_saldo__gt=0
        ).order_by('-total_saldo')[:limite]
        
        deudores = []
        total_top = 0
        
        for saldo in top_saldos:
            total_saldo = float(saldo['total_saldo'])
            saldo_vencido = float(saldo['saldo_vencido'] or 0)
            total_top += total_saldo
            
            deudores.append({
                'cliente_id': saldo['cliente__id'],
                'cliente_nombre': saldo['cliente__nombre'],
                'total_saldo': total_saldo,
                'numero_facturas': saldo['numero_facturas'],
                'saldo_vencido': saldo_vencido,
                'porcentaje_vencido': round((saldo_vencido / total_saldo * 100) if total_saldo > 0 else 0, 2),
                'dias_promedio_vencido': saldo['dias_promedio_vencido'] or 0
            })
        
        return {
            'fecha_calculo': timezone.now().isoformat(),
            'limite': limite,
            'deudores': deudores,
            'total_top_deudores': total_top,
            'numero_deudores': len(deudores)
        }