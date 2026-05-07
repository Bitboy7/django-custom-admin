# ventas/services/cuentas_por_cobrar_service.py

"""
Servicio principal para operaciones de cuentas por cobrar.
Implementa los 4 requerimientos funcionales principales:

RF1: Sincronización automática de deuda por ventas a crédito
RF2: Registro de abonos multiforma con actualización instantánea  
RF3: Cálculo de antigüedad de saldos en rangos estándar
RF4: Generación de estados de cuenta históricos por cliente
"""

from django.db import transaction, models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum, Count, Avg, Max, Min, Q
from django.core.cache import cache
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Union
import logging

# Imports de modelos (se cargan dinámicamente para evitar import circular)
from ..models import (
    Ventas, PagoVenta, Cliente, SaldoCliente, 
    AntigüedadSaldo, EstadoCuentaCliente, ConfiguracionCuentasPorCobrar
)

logger = logging.getLogger(__name__)


class CuentasPorCobrarService:
    """
    Servicio principal para operaciones de cuentas por cobrar.
    Centraliza la lógica de negocio y mantiene consistencia de datos.
    """
    
    # =========================================================================
    # RF1: SINCRONIZACIÓN AUTOMÁTICA DE DEUDA
    # =========================================================================
    
    @staticmethod
    @transaction.atomic
    def sincronizar_deuda_venta(venta_id: int, usuario_creacion: str = 'Sistema') -> Optional[SaldoCliente]:
        """
        RF1: Crea automáticamente registro en SaldoCliente 
        cuando se registra venta a crédito.
        
        Args:
            venta_id: ID de la venta que genera la deuda
            usuario_creacion: Usuario que registra (para auditoría)
            
        Returns:
            SaldoCliente creado o None si no aplica
            
        Raises:
            ValidationError: Si la venta no es válida o ya tiene saldo
            ValueError: Si los datos son inconsistentes
        """
        try:
            venta = Ventas.objects.select_for_update().get(id=venta_id)
            
            # Validar que sea venta a crédito
            if venta.modalidad_pago not in [Ventas.ModalidadPago.CREDITO]:
                logger.info(f"Venta {venta_id} no es a crédito, no se crea saldo")
                return None
                
            # Verificar que no existe saldo previo
            if hasattr(venta, 'saldo_cxc'):
                raise ValidationError(f"Ya existe saldo para venta {venta.id}")
            
            # Validar que tenga fecha de vencimiento
            if not venta.fecha_vencimiento:
                if venta.termino_credito:
                    venta.fecha_vencimiento = venta.fecha_deposito + timedelta(
                        days=venta.termino_credito.dias_credito
                    )
                    venta.save()
                else:
                    raise ValidationError("Venta a crédito debe tener término de crédito o fecha de vencimiento")
            
            # Determinar monto a crédito
            monto_credito = venta.monto
            
            # Crear registro de saldo
            saldo = SaldoCliente.objects.create(
                cliente=venta.cliente,
                venta=venta,
                monto_original=monto_credito,
                saldo_pendiente=monto_credito,
                fecha_vencimiento=venta.fecha_vencimiento,
                moneda=venta.moneda_venta or 'MXN',
                estado=SaldoCliente.EstadosSaldo.PENDIENTE
            )
            
            # Actualizar estado de cobranza en la venta
            venta.estado_cobranza = Ventas.EstadoCobranza.PENDIENTE
            venta.monto_pagado.amount = 0
            venta.save()
            
            # Invalidar cache del cliente
            CuentasPorCobrarService._invalidar_cache_cliente(venta.cliente.id)
            
            logger.info(f"Saldo creado automáticamente: {saldo.id} para venta {venta.id}")
            return saldo
            
        except Ventas.DoesNotExist:
            logger.error(f"Venta {venta_id} no encontrada")
            raise ValidationError(f"Venta {venta_id} no existe")
        except Exception as e:
            logger.error(f"Error sincronizando deuda venta {venta_id}: {str(e)}")
            raise
    
    # =========================================================================
    # RF2: REGISTRO DE ABONOS MULTIFORMA
    # =========================================================================
    
    @staticmethod
    @transaction.atomic
    def registrar_abono(
        saldo_id: int, 
        monto_abono: float, 
        metodo_pago: str, 
        fecha_pago: Optional[date] = None,
        referencia: str = '', 
        cuenta_destino_id: Optional[int] = None,
        notas: str = '',
        usuario: str = 'Sistema'
    ) -> Tuple[PagoVenta, SaldoCliente]:
        """
        RF2: Registra abono parcial y actualiza saldo instantáneamente.
        
        Args:
            saldo_id: ID del saldo a abonar
            monto_abono: Cantidad a abonar
            metodo_pago: Método de pago (efectivo, transferencia, etc.)
            fecha_pago: Fecha del pago (hoy si no se especifica)
            referencia: Referencia o comprobante del pago
            cuenta_destino_id: ID de cuenta bancaria destino
            notas: Notas adicionales
            usuario: Usuario que registra el pago
            
        Returns:
            Tuple con (PagoVenta creado, SaldoCliente actualizado)
            
        Raises:
            ValidationError: Si el abono es inválido
            ValueError: Si los montos no coinciden
        """
        try:
            # Obtener saldo con lock para evitar concurrencia
            saldo = SaldoCliente.objects.select_for_update().get(id=saldo_id)
            
            # Validaciones básicas
            if monto_abono <= 0:
                raise ValidationError("El monto del abono debe ser positivo")
                
            if monto_abono > float(saldo.saldo_pendiente.amount):
                config = ConfiguracionCuentasPorCobrar.obtener_configuracion()
                if not config.permitir_sobregiro_credito:
                    raise ValidationError(
                        f"El abono ({monto_abono}) excede el saldo pendiente ({saldo.saldo_pendiente})"
                    )
            
            # Validar método de pago
            if metodo_pago not in [choice[0] for choice in PagoVenta.MetodoPago.choices]:
                raise ValidationError(f"Método de pago '{metodo_pago}' no válido")
            
            # Obtener cuenta destino (usar cuenta por defecto de la venta si no se especifica)
            from gastos.models import Cuenta
            
            if cuenta_destino_id:
                try:
                    cuenta_destino = Cuenta.objects.get(id=cuenta_destino_id)
                except Cuenta.DoesNotExist:
                    raise ValidationError(f"Cuenta destino {cuenta_destino_id} no existe")
            else:
                cuenta_destino = saldo.venta.cuenta
                if not cuenta_destino:
                    raise ValidationError("Debe especificar cuenta destino para el pago")
            
            # Crear registro de pago
            pago = PagoVenta.objects.create(
                venta=saldo.venta,
                fecha_pago=fecha_pago or timezone.now().date(),
                monto_pago=monto_abono,
                cuenta_destino=cuenta_destino,
                metodo_pago=metodo_pago,
                referencia=referencia or '',
                notas=notas or ''
            )
            
            # Actualizar saldo
            nuevo_saldo = float(saldo.saldo_pendiente.amount) - monto_abono
            saldo.saldo_pendiente.amount = max(0, nuevo_saldo)
            saldo.fecha_ultimo_pago = pago.fecha_pago
            
            # Actualizar estado según saldo restante
            if saldo.saldo_pendiente.amount <= 0:
                saldo.estado = SaldoCliente.EstadosSaldo.PAGADO
                saldo.venta.estado_cobranza = Ventas.EstadoCobranza.PAGADO
            elif saldo.saldo_pendiente.amount < float(saldo.monto_original.amount):
                if saldo.dias_vencido() > 0:
                    saldo.estado = SaldoCliente.EstadosSaldo.VENCIDO
                    saldo.venta.estado_cobranza = Ventas.EstadoCobranza.VENCIDO
                else:
                    saldo.estado = SaldoCliente.EstadosSaldo.PARCIAL
                    saldo.venta.estado_cobranza = Ventas.EstadoCobranza.PARCIAL
            
            # Actualizar monto pagado en la venta
            total_pagos = saldo.venta.pagos.aggregate(
                total=Sum('monto_pago')
            )['total'] or 0
            saldo.venta.monto_pagado.amount = float(total_pagos)
            
            # Guardar cambios
            saldo.save()
            saldo.venta.save()
            
            # Invalidar caches
            CuentasPorCobrarService._invalidar_cache_cliente(saldo.cliente.id)
            
            logger.info(
                f"Abono registrado: {monto_abono} para saldo {saldo.id}, "
                f"nuevo saldo: {saldo.saldo_pendiente}"
            )
            
            return pago, saldo
            
        except SaldoCliente.DoesNotExist:
            logger.error(f"Saldo {saldo_id} no encontrado")
            raise ValidationError(f"Saldo {saldo_id} no existe")
        except Exception as e:
            logger.error(f"Error registrando abono para saldo {saldo_id}: {str(e)}")
            raise
    
    # =========================================================================
    # RF3: CÁLCULO DE ANTIGÜEDAD DE SALDOS
    # =========================================================================
    
    @staticmethod
    def calcular_antiguedad_cliente(
        cliente_id: int, 
        fecha_corte: Optional[date] = None,
        forzar_recalculo: bool = False
    ) -> AntigüedadSaldo:
        """
        RF3: Calcula y clasifica antigüedad de saldos por cliente.
        
        Args:
            cliente_id: ID del cliente a analizar
            fecha_corte: Fecha de corte para el análisis (hoy si no se especifica)
            forzar_recalculo: Si True, recalcula aunque ya exista para la fecha
            
        Returns:
            AntigüedadSaldo con la clasificación por buckets de aging
            
        Raises:
            ValidationError: Si el cliente no existe
            ValueError: Si hay errores en el cálculo
        """
        if fecha_corte is None:
            fecha_corte = timezone.now().date()
            
        try:
            cliente = Cliente.objects.get(id=cliente_id)
            
            # Verificar si ya existe cálculo para esta fecha
            if not forzar_recalculo:
                try:
                    return AntigüedadSaldo.objects.get(
                        cliente=cliente,
                        fecha_calculo=fecha_corte
                    )
                except AntigüedadSaldo.DoesNotExist:
                    pass  # Continuar con el cálculo
            
            # Obtener configuración de rangos
            config = ConfiguracionCuentasPorCobrar.obtener_configuracion()
            
            # Obtener saldos pendientes del cliente
            saldos = SaldoCliente.objects.filter(
                cliente=cliente,
                estado__in=[
                    SaldoCliente.EstadosSaldo.PENDIENTE,
                    SaldoCliente.EstadosSaldo.PARCIAL,
                    SaldoCliente.EstadosSaldo.VENCIDO
                ]
            ).exclude(saldo_pendiente__lte=0)
            
            # Inicializar buckets de aging
            aging_buckets = {
                'corriente': 0,
                'vencido_1': 0,
                'vencido_2': 0,
                'vencido_3': 0,
                'numero_facturas': saldos.count(),
                'total_dias_pago': 0,
                'facturas_con_pagos': 0
            }
            
            # Clasificar cada saldo por antigüedad
            for saldo in saldos:
                dias_desde_vencimiento = (fecha_corte - saldo.fecha_vencimiento).days
                monto_saldo = float(saldo.saldo_pendiente.amount)
                
                # Clasificar en bucket apropiado
                if dias_desde_vencimiento <= 0:
                    aging_buckets['corriente'] += monto_saldo
                elif dias_desde_vencimiento <= config.dias_corriente:
                    aging_buckets['corriente'] += monto_saldo
                elif dias_desde_vencimiento <= config.dias_vencido_1:
                    aging_buckets['vencido_1'] += monto_saldo
                elif dias_desde_vencimiento <= config.dias_vencido_2:
                    aging_buckets['vencido_2'] += monto_saldo
                else:
                    aging_buckets['vencido_3'] += monto_saldo
                
                # Calcular promedio de días de pago si hay historial
                if saldo.fecha_ultimo_pago:
                    dias_pago = (saldo.fecha_ultimo_pago - saldo.fecha_creacion.date()).days
                    aging_buckets['total_dias_pago'] += dias_pago
                    aging_buckets['facturas_con_pagos'] += 1
            
            # Calcular promedio de días de pago
            promedio_dias_pago = None
            if aging_buckets['facturas_con_pagos'] > 0:
                promedio_dias_pago = aging_buckets['total_dias_pago'] / aging_buckets['facturas_con_pagos']
            
            # Crear o actualizar registro de antigüedad
            total_saldo = sum([
                aging_buckets['corriente'],
                aging_buckets['vencido_1'],
                aging_buckets['vencido_2'],
                aging_buckets['vencido_3']
            ])
            
            antiguedad, created = AntigüedadSaldo.objects.update_or_create(
                cliente=cliente,
                fecha_calculo=fecha_corte,
                defaults={
                    'corriente': aging_buckets['corriente'],
                    'vencido_1': aging_buckets['vencido_1'],
                    'vencido_2': aging_buckets['vencido_2'],
                    'vencido_3': aging_buckets['vencido_3'],
                    'total_saldo': total_saldo,
                    'numero_facturas': aging_buckets['numero_facturas'],
                    'promedio_dias_pago': promedio_dias_pago,
                    'calculado_por': 'Sistema'
                }
            )
            
            action = 'creado' if created else 'actualizado'
            logger.info(f"Aging {action} para cliente {cliente.nombre}: total {total_saldo}")
            
            return antiguedad
            
        except Cliente.DoesNotExist:
            logger.error(f"Cliente {cliente_id} no encontrado")
            raise ValidationError(f"Cliente {cliente_id} no existe")
        except Exception as e:
            logger.error(f"Error calculando antigüedad cliente {cliente_id}: {str(e)}")
            raise
    
    @staticmethod
    def calcular_aging_masivo(fecha_corte: Optional[date] = None) -> Dict[str, int]:
        """
        Calcula aging para todos los clientes con saldos pendientes.
        
        Args:
            fecha_corte: Fecha de corte para el análisis
            
        Returns:
            Dict con estadísticas del proceso (procesados, errores, etc.)
        """
        if fecha_corte is None:
            fecha_corte = timezone.now().date()
            
        clientes_procesados = 0
        errores = 0
        clientes_con_saldos = Cliente.objects.filter(
            saldos_cxc__estado__in=[
                SaldoCliente.EstadosSaldo.PENDIENTE,
                SaldoCliente.EstadosSaldo.PARCIAL,
                SaldoCliente.EstadosSaldo.VENCIDO
            ]
        ).distinct()
        
        for cliente in clientes_con_saldos:
            try:
                CuentasPorCobrarService.calcular_antiguedad_cliente(
                    cliente.id, 
                    fecha_corte, 
                    forzar_recalculo=True
                )
                clientes_procesados += 1
            except Exception as e:
                logger.error(f"Error calculando aging cliente {cliente.id}: {str(e)}")
                errores += 1
        
        return {
            'fecha_corte': fecha_corte,
            'clientes_procesados': clientes_procesados,
            'errores': errores,
            'total_clientes': clientes_con_saldos.count()
        }
    
    # =========================================================================
    # RF4: GENERACIÓN DE ESTADOS DE CUENTA HISTÓRICOS  
    # =========================================================================
    
    @staticmethod
    def generar_estado_cuenta(
        cliente_id: int, 
        fecha_inicio: date, 
        fecha_fin: date,
        formato: str = 'WEB',
        usuario: str = 'Sistema',
        incluir_pagos_fuera_periodo: bool = True
    ) -> Dict:
        """
        RF4: Genera estado de cuenta histórico por cliente.
        Muestra: Venta Original - Suma de Abonos = Saldo Pendiente
        
        Args:
            cliente_id: ID del cliente
            fecha_inicio: Fecha de inicio del período
            fecha_fin: Fecha de fin del período
            formato: Formato de salida ('WEB', 'PDF', 'EXCEL')
            usuario: Usuario que genera el reporte
            incluir_pagos_fuera_periodo: Si incluir pagos fuera del período
            
        Returns:
            Dict con estado_cuenta, movimientos y resumen
            
        Raises:
            ValidationError: Si los parámetros son inválidos
        """
        try:
            cliente = Cliente.objects.get(id=cliente_id)
            
            # Validar fechas
            if fecha_inicio > fecha_fin:
                raise ValidationError("La fecha de inicio debe ser anterior a la fecha de fin")
            if fecha_fin > timezone.now().date():
                fecha_fin = timezone.now().date()
            
            # Obtener ventas del período (RF4: Venta Original)
            ventas_periodo = Ventas.objects.filter(
                cliente=cliente,
                fecha_deposito__range=[fecha_inicio, fecha_fin],
                modalidad_pago=Ventas.ModalidadPago.CREDITO
            ).order_by('fecha_deposito')
            
            # Obtener pagos del período o relacionados a ventas del período
            if incluir_pagos_fuera_periodo:
                # Incluir todos los pagos de ventas del período, sin importar cuándo se pagaron
                venta_ids = list(ventas_periodo.values_list('id', flat=True))
                pagos_periodo = PagoVenta.objects.filter(
                    venta__id__in=venta_ids
                ).order_by('fecha_pago')
            else:
                # Solo pagos dentro del período específico
                pagos_periodo = PagoVenta.objects.filter(
                    venta__cliente=cliente,
                    fecha_pago__range=[fecha_inicio, fecha_fin]
                ).order_by('fecha_pago')
            
            # Construir movimientos cronológicos para el estado de cuenta
            movimientos = []
            saldo_acumulado = 0
            
            # Obtener saldo inicial (ventas anteriores al período)
            ventas_anteriores = Ventas.objects.filter(
                cliente=cliente,
                fecha_deposito__lt=fecha_inicio,
                modalidad_pago=Ventas.ModalidadPago.CREDITO
            )
            
            for venta_anterior in ventas_anteriores:
                saldo_acumulado += float(venta_anterior.monto.amount)
                # Restar pagos anteriores al período
                pagos_anteriores = PagoVenta.objects.filter(
                    venta=venta_anterior,
                    fecha_pago__lt=fecha_inicio
                )
                for pago in pagos_anteriores:
                    saldo_acumulado -= float(pago.monto_pago.amount)
            
            # Guardar para el registro del modelo
            saldo_inicial_periodo = saldo_acumulado
            
            # Agregar saldo inicial si existe
            if abs(saldo_acumulado) > 0.01:  # Evitar mostrar centavos insignificantes
                movimientos.append({
                    'fecha': fecha_inicio,
                    'tipo': 'SALDO_INICIAL',
                    'referencia': 'SALDO-INICIAL',
                    'concepto': 'Saldo inicial del período',
                    'cargo': saldo_acumulado if saldo_acumulado > 0 else 0,
                    'abono': abs(saldo_acumulado) if saldo_acumulado < 0 else 0,
                    'saldo': saldo_acumulado,
                    'venta_id': None
                })
            
            # Agregar ventas del período (RF4: Venta Original)
            for venta in ventas_periodo:
                monto_venta = float(venta.monto.amount)
                saldo_acumulado += monto_venta
                
                movimientos.append({
                    'fecha': venta.fecha_deposito,
                    'tipo': 'VENTA',
                    'referencia': venta.carga or f'V-{venta.id}',
                    'concepto': f'Venta a crédito - {venta.producto.nombre}' if venta.producto else 'Venta a crédito',
                    'cargo': monto_venta,
                    'abono': 0,
                    'saldo': saldo_acumulado,
                    'venta_id': venta.id
                })
            
            # Agregar pagos (RF4: Suma de Abonos)
            for pago in pagos_periodo:
                monto_pago = float(pago.monto_pago.amount)
                saldo_acumulado -= monto_pago
                
                movimientos.append({
                    'fecha': pago.fecha_pago,
                    'tipo': 'PAGO',
                    'referencia': pago.referencia or f'P-{pago.id}',
                    'concepto': f'Pago - {pago.get_metodo_pago_display()}',
                    'cargo': 0,
                    'abono': monto_pago,
                    'saldo': saldo_acumulado,
                    'venta_id': pago.venta.id
                })
            
            # Ordenar movimientos cronológicamente
            movimientos.sort(key=lambda x: (x['fecha'], x['tipo'] == 'PAGO'))
            
            # Recalcular saldos acumulados después del ordenamiento
            saldo_running = 0
            if movimientos and movimientos[0]['tipo'] == 'SALDO_INICIAL':
                saldo_running = movimientos[0]['saldo']
                
            for i, movimiento in enumerate(movimientos):
                if movimiento['tipo'] != 'SALDO_INICIAL':
                    saldo_running += movimiento['cargo'] - movimiento['abono']
                    movimiento['saldo'] = saldo_running
            
            # Calcular totales para el resumen (RF4: Venta Original - Suma de Abonos = Saldo Pendiente)
            total_ventas = sum(v.monto.amount for v in ventas_periodo)
            total_abonos = sum(p.monto_pago.amount for p in pagos_periodo)
            saldo_final = saldo_acumulado  # RF4: Saldo Pendiente
            
            # Crear ou actualizar registro del estado de cuenta (evita duplicados en regenerar)
            estado_cuenta, _ = EstadoCuentaCliente.objects.update_or_create(
                cliente=cliente,
                periodo_inicio=fecha_inicio,
                periodo_fin=fecha_fin,
                defaults={
                    'saldo_inicial': saldo_inicial_periodo,
                    'total_ventas': total_ventas,
                    'total_abonos': total_abonos,
                    'saldo_final': saldo_final,
                    'numero_facturas': ventas_periodo.count(),
                    'generado_por': usuario,
                    'formato_generado': formato,
                }
            )
            
            # Preparar resumen del estado de cuenta
            resumen = {
                'cliente': cliente,
                'periodo_inicio': fecha_inicio,
                'periodo_fin': fecha_fin,
                'saldo_inicial': saldo_inicial_periodo,
                'total_ventas': total_ventas,
                'total_abonos': total_abonos,
                'saldo_final': saldo_final,
                'numero_facturas': ventas_periodo.count(),
                'numero_pagos': pagos_periodo.count(),
                'porcentaje_recuperacion': estado_cuenta.porcentaje_recuperacion,
                'promedio_por_factura': estado_cuenta.promedio_por_factura,
                'limite_credito': cliente.limite_credito.amount,
                'credito_disponible': cliente.credito_disponible(),
            }
            
            logger.info(
                f"Estado de cuenta generado para {cliente.nombre}: "
                f"período {fecha_inicio} - {fecha_fin}, saldo final {saldo_final}"
            )
            
            return {
                'estado_cuenta': estado_cuenta,
                'movimientos': movimientos,
                'resumen': resumen,
                'metadata': {
                    'formato': formato,
                    'generado_por': usuario,
                    'fecha_generacion': timezone.now(),
                    'total_movimientos': len(movimientos)
                }
            }
            
        except Cliente.DoesNotExist:
            logger.error(f"Cliente {cliente_id} no encontrado")
            raise ValidationError(f"Cliente {cliente_id} no existe")
        except Exception as e:
            logger.error(f"Error generando estado de cuenta cliente {cliente_id}: {str(e)}")
            raise
    
    # =========================================================================
    # MÉTODOS AUXILIARES Y UTILIDADES
    # =========================================================================
    
    @staticmethod
    def _invalidar_cache_cliente(cliente_id: int):
        """Invalida el cache para un cliente específico"""
        cache_keys = [
            f'cxc_metricas_{cliente_id}',
            f'cliente_saldos_{cliente_id}',
            'cxc_dashboard_global'
        ]
        cache.delete_many(cache_keys)
    
    @staticmethod
    def validar_limite_credito(cliente_id: int, monto_venta: float) -> Dict[str, Union[bool, float, str]]:
        """
        Valida si una venta no excede el límite de crédito del cliente.
        
        Returns:
            Dict con resultado de validación y detalles
        """
        try:
            cliente = Cliente.objects.get(id=cliente_id)
            
            if cliente.tipo_cliente == Cliente.TipoCliente.CONTADO:
                return {
                    'aprobado': False,
                    'razon': 'Cliente solo acepta ventas de contado',
                    'limite_credito': 0,
                    'credito_disponible': 0,
                    'monto_solicitado': monto_venta
                }
            
            credito_disponible = cliente.credito_disponible()
            
            if monto_venta <= credito_disponible:
                return {
                    'aprobado': True,
                    'razon': 'Crédito dentro del límite disponible',
                    'limite_credito': float(cliente.limite_credito.amount),
                    'credito_disponible': credito_disponible,
                    'monto_solicitado': monto_venta
                }
            
            # Verificar si se puede aprobar con sobregiro
            config = ConfiguracionCuentasPorCobrar.obtener_configuracion()
            if config.permitir_sobregiro_credito:
                limite_con_sobregiro = float(cliente.limite_credito.amount) * (
                    1 + config.porcentaje_sobregiro_permitido / 100
                )
                
                if monto_venta <= limite_con_sobregiro:
                    return {
                        'aprobado': True,
                        'razon': f'Aprobado con sobregiro ({config.porcentaje_sobregiro_permitido}%)',
                        'limite_credito': float(cliente.limite_credito.amount),
                        'credito_disponible': credito_disponible,
                        'monto_solicitado': monto_venta,
                        'requiere_autorizacion': True
                    }
            
            return {
                'aprobado': False,
                'razon': f'Excede límite de crédito (disponible: {credito_disponible})',
                'limite_credito': float(cliente.limite_credito.amount),
                'credito_disponible': credito_disponible,
                'monto_solicitado': monto_venta
            }
            
        except Cliente.DoesNotExist:
            return {
                'aprobado': False,
                'razon': 'Cliente no encontrado',
                'limite_credito': 0,
                'credito_disponible': 0,
                'monto_solicitado': monto_venta
            }
    
    @staticmethod
    def obtener_resumen_cliente(cliente_id: int) -> Dict:
        """
        Obtiene resumen completo de cuentas por cobrar para un cliente.
        Incluye saldos actuales, aging, y métricas de pago.
        """
        try:
            cliente = Cliente.objects.get(id=cliente_id)
            
            # Saldos actuales
            saldos = SaldoCliente.objects.filter(cliente=cliente)
            saldos_activos = saldos.exclude(estado=SaldoCliente.EstadosSaldo.PAGADO)
            
            total_saldos = saldos_activos.aggregate(
                total=Sum('saldo_pendiente')
            )['total'] or 0
            
            # Aging más reciente
            aging_reciente = AntigüedadSaldo.objects.filter(
                cliente=cliente
            ).order_by('-fecha_calculo').first()
            
            # Historial de pagos
            historico_pagos = PagoVenta.objects.filter(
                venta__cliente=cliente
            ).aggregate(
                total_pagos=Sum('monto_pago'),
                ultimo_pago=Max('fecha_pago'),
                promedio_pago=Avg('monto_pago')
            )
            
            return {
                'cliente': cliente,
                'saldos': {
                    'total_pendiente': float(total_saldos),
                    'numero_facturas': saldos_activos.count(),
                    'saldo_vencido': float(saldos_activos.filter(
                        dias_vencido__gt=0
                    ).aggregate(
                        total=Sum('saldo_pendiente')
                    )['total'] or 0)
                },
                'credito': {
                    'limite': float(cliente.limite_credito.amount),
                    'disponible': cliente.credito_disponible(),
                    'utilizacion_pct': round(
                        (float(total_saldos) / float(cliente.limite_credito.amount) * 100) 
                        if cliente.limite_credito.amount > 0 else 0, 2
                    )
                },
                'aging': aging_reciente,
                'pagos': historico_pagos,
                'fecha_consulta': timezone.now().date()
            }
            
        except Cliente.DoesNotExist:
            raise ValidationError(f"Cliente {cliente_id} no existe")


# =============================================================================
# FUNCIONES DE UTILIDAD GLOBALES
# =============================================================================

def sincronizar_saldos_huerfanos():
    """
    Función de mantenimiento: busca ventas a crédito sin saldo y los crea.
    Útil para migrar datos históricos o corregir inconsistencias.
    """
    ventas_sin_saldo = Ventas.objects.filter(
        modalidad_pago=Ventas.ModalidadPago.CREDITO
    ).exclude(
        id__in=SaldoCliente.objects.values_list('venta_id', flat=True)
    )
    
    creados = 0
    errores = 0
    
    for venta in ventas_sin_saldo:
        try:
            CuentasPorCobrarService.sincronizar_deuda_venta(venta.id, 'Migración')
            creados += 1
        except Exception as e:
            logger.error(f"Error creando saldo para venta {venta.id}: {str(e)}")
            errores += 1
    
    return {
        'ventas_procesadas': ventas_sin_saldo.count(),
        'saldos_creados': creados,
        'errores': errores
    }


def recalcular_estados_cobranza():
    """
    Función de mantenimiento: recalcula estados de cobranza basado en pagos reales.
    """
    saldos_inconsistentes = 0
    saldos_corregidos = 0
    
    for saldo in SaldoCliente.objects.all():
        try:
            # Recalcular saldo basado en pagos reales
            total_pagos = saldo.venta.pagos.aggregate(
                total=Sum('monto_pago')
            )['total'] or 0
            
            saldo_real = float(saldo.monto_original.amount) - float(total_pagos)
            
            if abs(float(saldo.saldo_pendiente.amount) - saldo_real) > 0.01:
                saldos_inconsistentes += 1
                
                # Corregir saldo
                saldo.saldo_pendiente.amount = max(0, saldo_real)
                
                # Recalcular estado
                if saldo.saldo_pendiente.amount <= 0:
                    saldo.estado = SaldoCliente.EstadosSaldo.PAGADO
                elif saldo.saldo_pendiente.amount < float(saldo.monto_original.amount):
                    if saldo.dias_vencido() > 0:
                        saldo.estado = SaldoCliente.EstadosSaldo.VENCIDO
                    else:
                        saldo.estado = SaldoCliente.EstadosSaldo.PARCIAL
                        
                saldo.save()
                saldos_corregidos += 1
                
        except Exception as e:
            logger.error(f"Error recalculando saldo {saldo.id}: {str(e)}")
    
    return {
        'saldos_revisados': SaldoCliente.objects.count(),
        'inconsistencias_encontradas': saldos_inconsistentes,
        'saldos_corregidos': saldos_corregidos
    }