from django.shortcuts import render, redirect, get_object_or_404
from .models import Anticipo, Ventas
from .forms import AnticipoForm

def lista_anticipos(request):
    anticipos = Anticipo.objects.all()
    return render(request, 'lista_anticipos.html', {'anticipos': anticipos})

def crear_anticipo(request):
    if request.method == 'POST':
        form = AnticipoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_anticipos')
    else:
        form = AnticipoForm()
    return render(request, 'crear_anticipo.html', {'form': form})

def detalle_venta(request, venta_id):
    venta = get_object_or_404(Ventas, id=venta_id)
    monto_final = venta.calcular_monto_final()
    return render(request, 'detalle_venta.html', {'venta': venta, 'monto_final': monto_final})