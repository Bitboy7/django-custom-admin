# ventas/services/metrics_service.py

"""
Servicio de métricas y KPIs para cuentas por cobrar.
Calcula indicadores clave de performance y análisis financiero.
"""

from django.db.models import Sum, Count, Avg, Max, Min, Q, F, Case, When, Value
from django.db.models.functions import Extract, Coalesce
from django.utils import timezone
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import calendar
import logging

logger = logging.getLogger(__name__)


class CuentasPorCobrarMetrics:
    """
    Clase para calcular métricas y KPIs del sistema de cuentas por cobrar.
    Se integra con el sistema de reportes existente.
    """
    
    # =========================================================================
    # MÉTRICAS DE PERFORMANCE PRINCIPAL
    # =========================================================================
    
    @staticmethod
    def calcular_dso(periodo_dias: int = 30) -> Dict:
        """
        Days Sales Outstanding - Métrica clave de eficiencia de cobranza
        DSO = (Cuentas por Cobrar Promedio / Ventas a Crédito del Período) * Número de Días
        
        Args:
            periodo_dias: Número de días a considerar para el cálculo
            
        Returns:
            Dict con DSO y componentes del cálculo
        """
        from ..models import SaldoCliente, Ventas
        
        fecha_fin = timezone.now().date()
        fecha_inicio = fecha_fin - timedelta(days=periodo_dias)
        
        try:
            # Total de cuentas por cobrar actuales
            total_cxc = SaldoCliente.objects.exclude(
                estado=SaldoCliente.EstadosSaldo.PAGADO
            ).aggregate(
                total=Sum('saldo_pendiente')
            )['total'] or 0
            
            # Ventas a crédito del período
            ventas_credito = Ventas.objects.filter(
                fecha_deposito__range=[fecha_inicio, fecha_fin],
                modalidad_pago=Ventas.ModalidadPago.CREDITO
            ).aggregate(
                total=Sum('monto')
            )['total'] or 0
            
            # Calcular DSO
            if float(ventas_credito) > 0:
                dso_dias = (float(total_cxc) / float(ventas_credito)) * periodo_dias
            else:
                dso_dias = 0
            
            # Benchmarking básico
            benchmark = "Excelente"
            if dso_dias > 60:
                benchmark = "Deficiente"
            elif dso_dias > 45:
                benchmark = "Regular"  
            elif dso_dias > 30:
                benchmark = "Bueno"
            
            return {
                'dso_dias': round(dso_dias, 2),
                'total_cxc': float(total_cxc),
                'ventas_credito_periodo': float(ventas_credito),
                'periodo_dias': periodo_dias,
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
                'benchmark': benchmark,
                'fecha_calculo': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculando DSO: {str(e)}")
            raise
    
    @staticmethod
    def calcular_dso_tendencia(meses: int = 6) -> List[Dict]:
        """
        Calcula DSO mensual para análisis de tendencias.
        
        Args:
            meses: Número de meses hacia atrás a analizar
            
        Returns:
            Lista de DSO por mes
        """
        resultados = []
        fecha_base = timezone.now().date().replace(day=1)  # Primer día del mes actual
        
        for i in range(meses):
            # Calcular fecha del mes
            if i == 0:
                fecha_mes = fecha_base
            else:
                # Retroceder meses
                mes_actual = fecha_base.month
                año_actual = fecha_base.year
                
                mes_calc = mes_actual - i
                año_calc = año_actual
                
                if mes_calc <= 0:
                    mes_calc += 12
                    año_calc -= 1
                    
                fecha_mes = date(año_calc, mes_calc, 1)
            
            # Último día del mes
            ultimo_dia = calendar.monthrange(fecha_mes.year, fecha_mes.month)[1]
            fecha_fin_mes = date(fecha_mes.year, fecha_mes.month, ultimo_dia)
            
            try:
                dso_mes = CuentasPorCobrarMetrics.calcular_dso_historico(
                    fecha_corte=fecha_fin_mes
                )
                
                resultados.append({
                    'año': fecha_mes.year,
                    'mes': fecha_mes.month,
                    'nombre_mes': calendar.month_name[fecha_mes.month],
                    'fecha_corte': fecha_fin_mes,
                    'dso': dso_mes['dso_dias'],
                    'ventas_credito': dso_mes['ventas_credito_periodo'],
                    'cxc_promedio': dso_mes['total_cxc']
                })
                
            except Exception as e:
                logger.warning(f"Error calculando DSO para {fecha_mes}: {str(e)}")
                resultados.append({
                    'año': fecha_mes.year,
                    'mes': fecha_mes.month,
                    'nombre_mes': calendar.month_name[fecha_mes.month],
                    'fecha_corte': fecha_fin_mes,
                    'dso': 0,
                    'ventas_credito': 0,
                    'cxc_promedio': 0,
                    'error': True
                })
        
        # Ordenar cronológicamente (más antiguo primero)
        resultados.reverse()
        return resultados
    
    @staticmethod
    def calcular_dso_historico(fecha_corte: date) -> Dict:
        """
        Calcula DSO para una fecha específica (análisis histórico).
        """
        from ..models import SaldoCliente, Ventas
        
        # Período de 30 días antes de la fecha de corte
        fecha_inicio = fecha_corte - timedelta(days=30)
        
        # CxC al corte
        total_cxc = SaldoCliente.objects.filter(
            fecha_creacion__date__lte=fecha_corte
        ).exclude(
            estado=SaldoCliente.EstadosSaldo.PAGADO
        ).aggregate(
            total=Sum('saldo_pendiente')
        )['total'] or 0
        
        # Ventas a crédito en los 30 días previos
        ventas_credito = Ventas.objects.filter(
            fecha_deposito__range=[fecha_inicio, fecha_corte],
            modalidad_pago=Ventas.ModalidadPago.CREDITO
        ).aggregate(
            total=Sum('monto')
        )['total'] or 0
        
        dso_dias = 0
        if float(ventas_credito) > 0:
            dso_dias = (float(total_cxc) / float(ventas_credito)) * 30
        
        return {
            'dso_dias': round(dso_dias, 2),
            'total_cxc': float(total_cxc),
            'ventas_credito_periodo': float(ventas_credito),
            'periodo_dias': 30,
            'fecha_corte': fecha_corte
        }
    
    # =========================================================================
    # ANÁLISIS DE CARTERA
    # =========================================================================
    
    @staticmethod
    def distribucion_aging_global(fecha_corte: Optional[date] = None) -> Dict:
        """
        Distribución porcentual de cartera por antigüedad a nivel global.
        """
        from ..models import AntigüedadSaldo
        
        if fecha_corte is None:
            fecha_corte = timezone.now().date()
        
        try:
            totales = AntigüedadSaldo.objects.filter(
                fecha_calculo=fecha_corte
            ).aggregate(
                corriente=Sum('corriente'),
                vencido_1=Sum('vencido_1'),
                vencido_2=Sum('vencido_2'),
                vencido_3=Sum('vencido_3'),
                total=Sum('total_saldo'),
                clientes=Count('cliente')
            )
            
            total_cartera = float(totales['total'] or 0)
            
            if total_cartera > 0:
                distribucion = {
                    'corriente': {
                        'monto': float(totales['corriente'] or 0),
                        'porcentaje': round((float(totales['corriente'] or 0) / total_cartera) * 100, 2)
                    },
                    'vencido_1': {
                        'monto': float(totales['vencido_1'] or 0),
                        'porcentaje': round((float(totales['vencido_1'] or 0) / total_cartera) * 100, 2)
                    },
                    'vencido_2': {
                        'monto': float(totales['vencido_2'] or 0),
                        'porcentaje': round((float(totales['vencido_2'] or 0) / total_cartera) * 100, 2)
                    },
                    'vencido_3': {
                        'monto': float(totales['vencido_3'] or 0),
                        'porcentaje': round((float(totales['vencido_3'] or 0) / total_cartera) * 100, 2)
                    }
                }
            else:
                distribucion = {
                    'corriente': {'monto': 0, 'porcentaje': 0},
                    'vencido_1': {'monto': 0, 'porcentaje': 0},
                    'vencido_2': {'monto': 0, 'porcentaje': 0},
                    'vencido_3': {'monto': 0, 'porcentaje': 0}
                }
            
            # KPIs derivados
            cartera_sana = distribucion['corriente']['porcentaje'] + distribucion['vencido_1']['porcentaje']
            cartera_critica = distribucion['vencido_2']['porcentaje'] + distribucion['vencido_3']['porcentaje']
            
            return {
                'fecha_corte': fecha_corte,
                'total_cartera': total_cartera,
                'clientes_analizados': totales['clientes'] or 0,
                'distribucion': distribucion,
                'kpis': {
                    'cartera_sana_pct': round(cartera_sana, 2),
                    'cartera_critica_pct': round(cartera_critica, 2),
                    'indice_deterioro': round(cartera_critica / 100, 4) if cartera_critica > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculando distribución aging: {str(e)}")
            raise
    
    @staticmethod
    def evolucion_cartera_mensual(meses: int = 12) -> List[Dict]:
        """
        Evolución de la cartera total en los últimos N meses.
        """
        from ..models import SaldoCliente
        
        resultados = []
        fecha_actual = timezone.now().date()
        
        for i in range(meses):
            # Calcular primer día de cada mes hacia atrás
            año = fecha_actual.year
            mes = fecha_actual.month - i
            
            if mes <= 0:
                mes += 12
                año -= 1
            
            primer_dia = date(año, mes, 1)
            ultimo_dia = date(año, mes, calendar.monthrange(año, mes)[1])
            
            try:
                # Saldos creados hasta ese mes
                saldos_mes = SaldoCliente.objects.filter(
                    fecha_creacion__date__lte=ultimo_dia
                ).exclude(
                    estado=SaldoCliente.EstadosSaldo.PAGADO,
                    fecha_ultimo_pago__date__lte=ultimo_dia  # Que no hayan sido pagados antes del corte
                ).aggregate(
                    total_cartera=Sum('saldo_pendiente'),
                    numero_facturas=Count('id'),
                    clientes_activos=Count('cliente', distinct=True)
                )
                
                resultados.append({
                    'año': año,
                    'mes': mes,
                    'nombre_mes': calendar.month_name[mes],
                    'fecha_corte': ultimo_dia,
                    'total_cartera': float(saldos_mes['total_cartera'] or 0),
                    'numero_facturas': saldos_mes['numero_facturas'] or 0,
                    'clientes_activos': saldos_mes['clientes_activos'] or 0
                })
                
            except Exception as e:
                logger.warning(f"Error calculando cartera para {año}-{mes}: {str(e)}")
        
        # Ordenar cronológicamente y calcular variaciones
        resultados.reverse()
        
        for i in range(1, len(resultados)):
            actual = resultados[i]
            anterior = resultados[i-1]
            
            if anterior['total_cartera'] > 0:
                variacion_pct = ((actual['total_cartera'] - anterior['total_cartera']) / 
                               anterior['total_cartera']) * 100
                actual['variacion_pct'] = round(variacion_pct, 2)
                actual['variacion_absoluta'] = actual['total_cartera'] - anterior['total_cartera']
            else:
                actual['variacion_pct'] = 0
                actual['variacion_absoluta'] = actual['total_cartera']
        
        return resultados
    
    # =========================================================================
    # MÉTRICAS DE EFICIENCIA DE COBRANZA
    # =========================================================================
    
    @staticmethod
    def eficiencia_cobranza_mensual(meses: int = 12) -> List[Dict]:
        """
        Análisis de eficiencia de cobranza por mes.
        Mide qué tanto se cobra vs lo que se vende.
        """
        from ..models import PagoVenta, Ventas
        
        resultados = []
        fecha_actual = timezone.now().date()
        
        for i in range(meses):
            # Calcular mes
            año = fecha_actual.year
            mes = fecha_actual.month - i
            
            if mes <= 0:
                mes += 12
                año -= 1
            
            primer_dia = date(año, mes, 1)
            ultimo_dia = date(año, mes, calendar.monthrange(año, mes)[1])
            
            try:
                # Ventas a crédito del mes
                ventas_mes = Ventas.objects.filter(
                    fecha_deposito__range=[primer_dia, ultimo_dia],
                    modalidad_pago=Ventas.ModalidadPago.CREDITO
                ).aggregate(
                    total_vendido=Sum('monto'),
                    numero_ventas=Count('id')
                )
                
                # Pagos recibidos en el mes
                pagos_mes = PagoVenta.objects.filter(
                    fecha_pago__range=[primer_dia, ultimo_dia]
                ).aggregate(
                    total_cobrado=Sum('monto_pago'),
                    numero_pagos=Count('id')
                )
                
                # Calcular eficiencia
                total_vendido = float(ventas_mes['total_vendido'] or 0)
                total_cobrado = float(pagos_mes['total_cobrado'] or 0)
                
                if total_vendido > 0:
                    eficiencia_pct = (total_cobrado / total_vendido) * 100
                else:
                    eficiencia_pct = 0 if total_cobrado == 0 else float('inf')
                
                resultados.append({
                    'año': año,
                    'mes': mes,
                    'nombre_mes': calendar.month_name[mes],
                    'total_vendido': total_vendido,
                    'total_cobrado': total_cobrado,
                    'numero_ventas': ventas_mes['numero_ventas'] or 0,
                    'numero_pagos': pagos_mes['numero_pagos'] or 0,
                    'eficiencia_pct': round(eficiencia_pct, 2),
                    'gap_cobranza': total_vendido - total_cobrado
                })
                
            except Exception as e:
                logger.warning(f"Error calculando eficiencia para {año}-{mes}: {str(e)}")
        
        resultados.reverse()
        return resultados
    
    @staticmethod
    def tasa_recuperacion_cartera(periodo_dias: int = 30) -> Dict:
        """
        Calcula la tasa de recuperación de cartera en un período específico.
        Mide qué porcentaje de la cartera inicial se logró cobrar.
        """
        from ..models import SaldoCliente, PagoVenta
        
        fecha_fin = timezone.now().date()
        fecha_inicio = fecha_fin - timedelta(days=periodo_dias)
        
        try:
            # Cartera inicial al inicio del período
            cartera_inicial = SaldoCliente.objects.filter(
                fecha_creacion__date__lt=fecha_inicio
            ).exclude(
                estado=SaldoCliente.EstadosSaldo.PAGADO
            ).aggregate(
                total=Sum('saldo_pendiente')
            )['total'] or 0
            
            # Pagos recibidos durante el período de cartera preexistente
            pagos_periodo = PagoVenta.objects.filter(
                fecha_pago__range=[fecha_inicio, fecha_fin],
                venta__fecha_deposito__lt=fecha_inicio  # Solo cartera previa
            ).aggregate(
                total_cobrado=Sum('monto_pago'),
                numero_pagos=Count('id')
            )
            
            total_cobrado = float(pagos_periodo['total_cobrado'] or 0)
            cartera_inicial_float = float(cartera_inicial)
            
            if cartera_inicial_float > 0:
                tasa_recuperacion = (total_cobrado / cartera_inicial_float) * 100
            else:
                tasa_recuperacion = 0
            
            return {
                'periodo_dias': periodo_dias,
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
                'cartera_inicial': cartera_inicial_float,
                'total_cobrado': total_cobrado,
                'numero_pagos': pagos_periodo['numero_pagos'] or 0,
                'tasa_recuperacion_pct': round(tasa_recuperacion, 2),
                'cartera_pendiente': cartera_inicial_float - total_cobrado
            }
            
        except Exception as e:
            logger.error(f"Error calculando tasa de recuperación: {str(e)}")
            raise
    
    # =========================================================================
    # ANÁLISIS DE CLIENTES Y SEGMENTACIÓN
    # =========================================================================
    
    @staticmethod
    def segmentacion_clientes_por_riesgo() -> Dict:
        """
        Segmenta clientes por nivel de riesgo basado en su aging.
        """
        from ..models import AntigüedadSaldo, Cliente
        
        try:
            fecha_reciente = AntigüedadSaldo.objects.aggregate(
                fecha_max=Max('fecha_calculo')
            )['fecha_max']
            
            if not fecha_reciente:
                return {'error': 'No hay datos de aging disponibles'}
            
            clientes_aging = AntigüedadSaldo.objects.filter(
                fecha_calculo=fecha_reciente,
                total_saldo__gt=0
            )
            
            segmentos = {
                'excelente': {'clientes': [], 'total_saldo': 0, 'criterio': '100% corriente'},
                'bueno': {'clientes': [], 'total_saldo': 0, 'criterio': 'Máx 10% vencido crítico'},
                'regular': {'clientes': [], 'total_saldo': 0, 'criterio': '10-25% vencido crítico'}, 
                'riesgo': {'clientes': [], 'total_saldo': 0, 'criterio': '25-50% vencido crítico'},
                'critico': {'clientes': [], 'total_saldo': 0, 'criterio': '+50% vencido crítico'}
            }
            
            for aging in clientes_aging:
                pct_critico = aging.porcentaje_vencido_critico
                total_saldo = float(aging.total_saldo.amount)
                
                cliente_info = {
                    'id': aging.cliente.id,
                    'nombre': aging.cliente.nombre,
                    'total_saldo': total_saldo,
                    'pct_vencido_critico': pct_critico
                }
                
                if pct_critico == 0:
                    segmentos['excelente']['clientes'].append(cliente_info)
                    segmentos['excelente']['total_saldo'] += total_saldo
                elif pct_critico <= 10:
                    segmentos['bueno']['clientes'].append(cliente_info)
                    segmentos['bueno']['total_saldo'] += total_saldo
                elif pct_critico <= 25:
                    segmentos['regular']['clientes'].append(cliente_info)
                    segmentos['regular']['total_saldo'] += total_saldo
                elif pct_critico <= 50:
                    segmentos['riesgo']['clientes'].append(cliente_info)
                    segmentos['riesgo']['total_saldo'] += total_saldo
                else:
                    segmentos['critico']['clientes'].append(cliente_info)
                    segmentos['critico']['total_saldo'] += total_saldo
            
            # Agregar estadísticas por segmento
            total_clientes = sum(len(seg['clientes']) for seg in segmentos.values())
            total_cartera = sum(seg['total_saldo'] for seg in segmentos.values())
            
            for segmento in segmentos.values():
                segmento['numero_clientes'] = len(segmento['clientes'])
                segmento['pct_clientes'] = round(
                    (segmento['numero_clientes'] / max(total_clientes, 1)) * 100, 2
                )
                segmento['pct_cartera'] = round(
                    (segmento['total_saldo'] / max(total_cartera, 1)) * 100, 2
                )
            
            return {
                'fecha_analisis': fecha_reciente,
                'total_clientes_activos': total_clientes,
                'total_cartera': total_cartera,
                'segmentos': segmentos
            }
            
        except Exception as e:
            logger.error(f"Error en segmentación de clientes: {str(e)}")
            raise
    
    @staticmethod
    def top_clientes_por_metrica(metrica: str = 'saldo', limite: int = 10) -> List[Dict]:
        """
        Obtiene top N clientes según diferentes métricas.
        
        Args:
            metrica: 'saldo', 'facturas', 'pagos', 'dias_vencido'
            limite: Número de clientes a retornar
        """
        from ..models import SaldoCliente, PagoVenta
        
        try:
            if metrica == 'saldo':
                # Top por saldo total
                resultados = SaldoCliente.objects.values(
                    'cliente__nombre', 'cliente__id'
                ).annotate(
                    total_saldo=Sum('saldo_pendiente'),
                    numero_facturas=Count('id')
                ).filter(
                    total_saldo__gt=0
                ).order_by('-total_saldo')[:limite]
                
                return [
                    {
                        'cliente_id': r['cliente__id'],
                        'cliente_nombre': r['cliente__nombre'],
                        'valor_metrica': float(r['total_saldo']),
                        'numero_facturas': r['numero_facturas'],
                        'metrica': 'Saldo Total'
                    }
                    for r in resultados
                ]
            
            elif metrica == 'facturas':
                # Top por número de facturas
                resultados = SaldoCliente.objects.values(
                    'cliente__nombre', 'cliente__id'
                ).annotate(
                    numero_facturas=Count('id'),
                    total_saldo=Sum('saldo_pendiente')
                ).filter(
                    total_saldo__gt=0
                ).order_by('-numero_facturas')[:limite]
                
                return [
                    {
                        'cliente_id': r['cliente__id'],
                        'cliente_nombre': r['cliente__nombre'],
                        'valor_metrica': r['numero_facturas'],
                        'total_saldo': float(r['total_saldo']),
                        'metrica': 'Número de Facturas'
                    }
                    for r in resultados
                ]
            
            elif metrica == 'pagos':
                # Top por monto de pagos recibidos
                resultados = PagoVenta.objects.values(
                    'venta__cliente__nombre', 'venta__cliente__id'
                ).annotate(
                    total_pagos=Sum('monto_pago'),
                    numero_pagos=Count('id')
                ).order_by('-total_pagos')[:limite]
                
                return [
                    {
                        'cliente_id': r['venta__cliente__id'],
                        'cliente_nombre': r['venta__cliente__nombre'],
                        'valor_metrica': float(r['total_pagos']),
                        'numero_pagos': r['numero_pagos'],
                        'metrica': 'Total Pagos'
                    }
                    for r in resultados
                ]
            
            else:
                raise ValueError(f"Métrica '{metrica}' no soportada")
                
        except Exception as e:
            logger.error(f"Error obteniendo top clientes por {metrica}: {str(e)}")
            raise
    
    # =========================================================================
    # REPORTES EJECUTIVOS Y DASHBOARDS
    # =========================================================================
    
    @staticmethod
    def reporte_ejecutivo_completo() -> Dict:
        """
        Genera reporte ejecutivo completo con todos los KPIs principales.
        """
        try:
            reporte = {
                'fecha_reporte': timezone.now().isoformat(),
                'periodo_analisis': '30 días',
                
                # KPI principal
                'dso': CuentasPorCobrarMetrics.calcular_dso(),
                
                # Distribución de cartera
                'aging': CuentasPorCobrarMetrics.distribucion_aging_global(),
                
                # Eficiencia de cobranza
                'eficiencia': CuentasPorCobrarMetrics.tasa_recuperacion_cartera(),
                
                # Segmentación de clientes
                'segmentacion': CuentasPorCobrarMetrics.segmentacion_clientes_por_riesgo(),
                
                # Top performers
                'top_deudores': CuentasPorCobrarMetrics.top_clientes_por_metrica('saldo', 5),
                'top_pagadores': CuentasPorCobrarMetrics.top_clientes_por_metrica('pagos', 5),
                
                # Tendencias
                'tendencia_dso': CuentasPorCobrarMetrics.calcular_dso_tendencia(6),
                'evolucion_cartera': CuentasPorCobrarMetrics.evolucion_cartera_mensual(6),
            }
            
            # Agregar análisis y recomendaciones
            reporte['analisis'] = CuentasPorCobrarMetrics._generar_analisis_ejecutivo(reporte)
            
            return reporte
            
        except Exception as e:
            logger.error(f"Error generando reporte ejecutivo: {str(e)}")
            raise
    
    @staticmethod
    def _generar_analisis_ejecutivo(reporte: Dict) -> Dict:
        """
        Genera análisis automático y recomendaciones basado en los KPIs.
        """
        analisis = {
            'alertas': [],
            'oportunidades': [],
            'recomendaciones': [],
            'score_salud': 0
        }
        
        # Análisis DSO
        dso = reporte['dso']['dso_dias']
        if dso > 60:
            analisis['alertas'].append("DSO crítico: Más de 60 días promedio de cobranza")
            analisis['recomendaciones'].append("Revisar y fortalecer procesos de cobranza")
        elif dso > 45:
            analisis['alertas'].append("DSO elevado: Revisar términos de crédito")
        else:
            analisis['oportunidades'].append("DSO dentro de parámetros aceptables")
        
        # Análisis aging
        aging = reporte['aging']
        cartera_critica_pct = aging['kpis']['cartera_critica_pct']
        
        if cartera_critica_pct > 25:
            analisis['alertas'].append(f"Cartera crítica alta: {cartera_critica_pct}% en +60 días")
            analisis['recomendaciones'].append("Implementar plan de recuperación de cartera vencida")
        elif cartera_critica_pct > 15:
            analisis['alertas'].append("Monitorear evolución de cartera vencida")
        else:
            analisis['oportunidades'].append("Cartera con aging saludable")
        
        # Análisis eficiencia
        eficiencia = reporte['eficiencia']['tasa_recuperacion_pct']
        if eficiencia < 50:
            analisis['alertas'].append("Baja tasa de recuperación de cartera")
            analisis['recomendaciones'].append("Revisar estrategias de cobranza y seguimiento")
        elif eficiencia > 80:
            analisis['oportunidades'].append("Excelente eficiencia de cobranza")
        
        # Calcular score de salud (0-100)
        score = 100
        score -= min(40, max(0, dso - 30))  # Penalizar DSO > 30
        score -= cartera_critica_pct * 2    # Penalizar cartera crítica
        score += min(20, eficiencia / 5)    # Bonificar eficiencia de cobranza
        
        analisis['score_salud'] = max(0, min(100, round(score)))
        
        return analisis