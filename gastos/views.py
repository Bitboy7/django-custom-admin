from django.shortcuts import render, redirect
from .forms import GastoForm

def registro_gasto(request):
    if request.method == 'POST':
        form = GastoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('gastos')
    else:
        form = GastoForm()
    return render(request, 'gastos/registro_gasto.html', {'form': form})