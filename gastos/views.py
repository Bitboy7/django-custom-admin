from django.shortcuts import render, redirect, get_object_or_404
from .forms import GastoForm
from .models import Cuenta

def registro_gasto(request):
    if request.method == 'POST':
        form = GastoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('gastos')
    else:
        form = GastoForm()
    return render(request, 'gastos/registro_gasto.html', {'form': form})
