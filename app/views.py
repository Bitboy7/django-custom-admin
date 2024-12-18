from django.shortcuts import render

def reportes(request):
    # Lógica para generar reportes
    context = {
        'report_data': 'Aquí va la información del reporte'
    }
    return render(request, 'reportes.html', context)