from django.db.models import Sum
from datetime import datetime
from .models import Cuenta, Ventas, Compra, Gastos

def calcular_saldo_anterior(cuenta, fecha):
    # Sumar las ventas asociadas a la cuenta
    ventas_total = Ventas.objects.filter(
        sucursal_id=cuenta.id_sucursal,
        fecha_registro__lt=fecha
    ).aggregate(Sum('monto'))['monto__sum'] or 0

    # Sumar las compras asociadas a la cuenta
    compras_total = Compra.objects.filter(
        fecha_registro__lt=fecha
    ).aggregate(Sum('monto_total'))['monto_total__sum'] or 0

    # Sumar los gastos asociados a la cuenta
    gastos_total = Gastos.objects.filter(
        id_cuenta_banco=cuenta,
        fecha_registro__lt=fecha
    ).aggregate(Sum('monto'))['monto__sum'] or 0

    # Calcular el saldo anterior
    saldo_anterior = ventas_total - compras_total - gastos_total

    return saldo_anterior