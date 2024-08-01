from django.shortcuts import render, redirect
from .models import Productor
from .forms import ProductorForm

def index(request):
    return render(request, 'index.html')

def data(request):
    return render(request, 'data.html')

def catalogo_list(request):
    return render(request, 'catalogo.html')

def insertar_productor(request):
    if request.method == 'POST':
        form = ProductorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('index')
    else:
        form = ProductorForm()
    
    return render(request, 'catalogo.html', {'form': form})

def listar_productores(request):
    productores = Productor.objects.all()
    return render(request, 'catalogo.html', {'productores': productores})


