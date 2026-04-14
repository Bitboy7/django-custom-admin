import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from ventas.services.reporte_cobranza_service import generar_reporte_cobranza
from datetime import date

datos = generar_reporte_cobranza(date(2025,1,1), date(2025,3,31))

print('\n=== VENTAS X COBRAR (filas con saldo pendiente) ===')
for f in datos['ventas_por_cliente']:
    print('  {:30s}  total={:>12,.2f}'.format(f['cliente'].nombre[:30], f['total']))
print('  TOTAL: {:>12,.2f}'.format(datos['totales_ventas']['total']))

print('\n=== MAQUILA X COBRAR ===')
for f in datos['maquila_por_cliente']:
    print('  {:30s}  total={:>12,.2f} USD'.format(f['cliente'].nombre[:30], f['total']))
print('  TOTAL USD: {:>10,.2f}'.format(datos['totales_maquila']['total']))
print('  TOTAL MXN: {:>10,.2f}  (TC={})'.format(datos['totales_maquila']['total_mxn'], datos['tipo_cambio']))
