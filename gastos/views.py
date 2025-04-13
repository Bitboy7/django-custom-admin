from django.shortcuts import render, redirect, get_object_or_404
from .forms import GastoForm
from .models import Cuenta, Compra, Banco, SaldoMensual
from catalogo.models import Productor, Producto
from django.db.models import Sum, Avg, Count, Max, Min
from django.contrib.auth.decorators import user_passes_test
from datetime import date, datetime, timedelta
import json
from app.views import is_admin
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .forms import CompraForm

# Vista existente
@login_required
def registro_gasto(request):
    if request.method == 'POST':
        form = GastoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('gastos')
    else:
        form = GastoForm()
    return render(request, 'gastos/registro_gasto.html', {'form': form})

# vista para compras a productores
@login_required
@user_passes_test(is_admin)
def compras_productores(request):
    # Obtener datos de compras
    compras = Compra.objects.all().order_by('-fecha_compra')
    productores = Productor.objects.all()
    productos = Producto.objects.all()
    cuentas = Cuenta.objects.all()
    
    # Crear una instancia del formulario para usar en la plantilla
    form = CompraForm()
    
    # Estadísticas generales
    total_compras = Compra.objects.aggregate(total=Sum('monto_total'))['total'] or 0
    compras_mes_actual = Compra.objects.filter(
        fecha_compra__year=datetime.now().year,
        fecha_compra__month=datetime.now().month
    ).aggregate(total=Sum('monto_total'))['total'] or 0
    
    # Top productores con más compras
    top_productores = Compra.objects.values(
        'productor__nombre_completo', 
        'productor__id'
    ).annotate(
        total_compras=Sum('monto_total'),
        cantidad_compras=Count('id')
    ).order_by('-total_compras')[:5]
    
    # Compras por tipo de pago
    compras_por_tipo = Compra.objects.values('tipo_pago').annotate(
        total=Sum('monto_total'),
        cantidad=Count('id')
    ).order_by('-total')
    
    # Histórico mensual (últimos 6 meses)
    meses = []
    datos_meses = []
    for i in range(5, -1, -1):
        fecha = datetime.now() - timedelta(days=30*i)
        mes = fecha.month
        anio = fecha.year
        compras_mes = Compra.objects.filter(
            fecha_compra__year=anio, 
            fecha_compra__month=mes
        ).aggregate(total=Sum('monto_total'))['total'] or 0
        meses.append(f"{fecha.strftime('%b')} {anio}")
        datos_meses.append(float(compras_mes))
    
    # Productos más comprados
    productos_comprados = Compra.objects.values(
        'producto__nombre', 
        'producto__variedad'
    ).annotate(
        total=Sum('monto_total'),
        cantidad=Sum('cantidad')
    ).order_by('-cantidad')[:5]
    
    context = {
        'compras': compras,
        'productores': productores,
        'productos': productos,
        'cuentas': cuentas,
        'form': form,  # Pasar el formulario a la plantilla
        'today': date.today(),
        'total_compras': total_compras,
        'compras_mes_actual': compras_mes_actual,
        'top_productores': top_productores,
        'compras_por_tipo': compras_por_tipo,
        'meses': json.dumps(meses),
        'datos_meses': json.dumps(datos_meses),
        'productos_comprados': productos_comprados,
    }
    
    return render(request, 'compras/compras_productores.html', context)

@login_required                                                                              
@user_passes_test(is_admin)
def detalle_productor_compras(request, productor_id):
    productor = get_object_or_404(Productor, id=productor_id)
    compras = Compra.objects.filter(productor=productor).order_by('-fecha_compra')
    
    # Estadísticas del productor
    total_compras = compras.aggregate(total=Sum('monto_total'))['total'] or 0
    cantidad_productos = compras.aggregate(cantidad=Sum('cantidad'))['cantidad'] or 0
    promedio_compra = compras.aggregate(promedio=Avg('monto_total'))['promedio'] or 0
    
    # Compras por producto
    compras_por_producto = compras.values('producto__nombre', 'producto__variedad').annotate(
        total=Sum('monto_total'),
        cantidad=Sum('cantidad')
    ).order_by('-total')
    
    context = {
        'productor': productor,
        'compras': compras,
        'total_compras': total_compras,
        'cantidad_productos': cantidad_productos,
        'promedio_compra': promedio_compra,
        'compras_por_producto': compras_por_producto
    }
    
    return render(request, 'compras/detalle_productor_compras.html', context)

@login_required
@require_POST
@user_passes_test(is_admin)
def guardar_compra(request):
    try:
        # Obtener datos del formulario
        fecha_compra = request.POST.get('fecha_compra')
        productor_id = request.POST.get('productor')
        producto_id = request.POST.get('producto')
        cuenta_id = request.POST.get('cuenta')
        cantidad = request.POST.get('cantidad')
        precio_unitario = request.POST.get('precio_unitario')
        monto_total = request.POST.get('monto_total')
        tipo_pago = request.POST.get('tipo_pago')
        observaciones = request.POST.get('observaciones', '')  # Campo opcional
        
        # Validaciones básicas
        if not all([fecha_compra, productor_id, producto_id, cuenta_id, cantidad, precio_unitario, monto_total, tipo_pago]):
            return JsonResponse({'success': False, 'error': 'Todos los campos son requeridos'})
        
        try:
            # Convertir tipos de datos
            productor = Productor.objects.get(id=int(productor_id))
            producto = Producto.objects.get(id=int(producto_id))
            cuenta = Cuenta.objects.get(id=int(cuenta_id))
            cantidad = int(cantidad)
            precio_unitario = float(precio_unitario)
            monto_total = float(monto_total)
            
            # Crear nueva compra
            nueva_compra = Compra(
                fecha_compra=fecha_compra,
                productor=productor,
                producto=producto,
                cuenta=cuenta,
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                monto_total=monto_total,
                tipo_pago=tipo_pago,
                observaciones=observaciones  # Guardar las observaciones
            )
            nueva_compra.save()
            
            # Recalcular saldos si es necesario
            saldo_mensual = SaldoMensual.objects.filter(
                cuenta=cuenta,
                año=datetime.strptime(fecha_compra, '%Y-%m-%d').year,
                mes=datetime.strptime(fecha_compra, '%Y-%m-%d').month
            ).first()
            
            if saldo_mensual:
                saldo_mensual.calcular_saldo_final()
            
            # Dentro de la función guardar_compra, en el bloque de retorno de la respuesta exitosa:
            return JsonResponse({
                'success': True,
                'compra': {
                    'id': nueva_compra.id,
                    'fecha_compra': nueva_compra.fecha_compra.strftime('%d/%m/%Y'),
                    'productor_nombre': productor.nombre_completo,
                    'producto_nombre': f"{producto.nombre} - {producto.variedad}",
                    'cantidad': cantidad,
                    'precio_unitario': str(precio_unitario),
                    'monto_total': str(monto_total),
                    'tipo_pago': tipo_pago,
                    'observaciones': observaciones  # Añade esta línea
                }
            })
                
        except (Productor.DoesNotExist, Producto.DoesNotExist, Cuenta.DoesNotExist) as e:
            return JsonResponse({'success': False, 'error': f'Error al buscar información: {str(e)}'})
        except ValueError as e:
            return JsonResponse({'success': False, 'error': f'Error en el formato de los datos: {str(e)}'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error al guardar la compra: {str(e)}'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error inesperado: {str(e)}'})
    
@login_required
@user_passes_test(is_admin)
def estadisticas_compras(request):
    # Obtener estadísticas actualizadas
    total_compras = Compra.objects.aggregate(total=Sum('monto_total'))['total'] or 0
    compras_mes_actual = Compra.objects.filter(
        fecha_compra__year=datetime.now().year,
        fecha_compra__month=datetime.now().month
    ).aggregate(total=Sum('monto_total'))['total'] or 0
    
    # Histórico mensual (últimos 6 meses)
    meses = []
    datos_meses = []
    for i in range(5, -1, -1):
        fecha = datetime.now() - timedelta(days=30*i)
        mes = fecha.month
        anio = fecha.year
        compras_mes = Compra.objects.filter(
            fecha_compra__year=anio, 
            fecha_compra__month=mes
        ).aggregate(total=Sum('monto_total'))['total'] or 0
        meses.append(f"{fecha.strftime('%b')} {anio}")
        datos_meses.append(float(compras_mes))
    
    return JsonResponse({
        'total_compras': float(total_compras),
        'compras_mes_actual': float(compras_mes_actual),
        'meses': meses,
        'datos_meses': datos_meses
    })
