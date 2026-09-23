import json
import logging
import os
import tempfile
from pathlib import Path
from django.conf import settings
import threading
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Avg, Count, Max, Min
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from app.services.utils import UtilService
from catalogo.models import Productor, Producto, Sucursal
from .forms import CompraForm, FacturaUploadForm, GastoForm
from .models import Cuenta, Compra, Banco, SaldoMensual, Gastos
from .services.invoice_recognition_service import reconocer_factura_pdf, reconocer_estado_cuenta_pdf, detectar_tipo_documento

# Configurar logger para las vistas
logger = logging.getLogger(__name__)

# Helper functions
def _is_htmx(request):
    """Check if request is from HTMX"""
    return request.headers.get('HX-Request') == 'true'

def _render_htmx_or_full(request, full_template, htmx_template, context):
    """Render HTMX partial or full template based on request"""
    if _is_htmx(request):
        return render(request, htmx_template, context)
    return render(request, full_template, context)

def _hx_trigger_response(response, trigger_type, title, message):
    """Add HX-Trigger header with toast notification"""
    trigger_data = {
        'showToast': {
            'type': trigger_type,
            'title': title,
            'message': message
        }
    }
    response['HX-Trigger'] = json.dumps(trigger_data)
    return response
@login_required
def ingresar_gasto_factura(request):
    """
    Vista para ingresar gastos a partir de una factura o estado de cuenta en PDF.
    Soporta HTMX para actualizaci&oacute;n parcial sin recarga completa.
    """
    logger.info("=== VISTA INGRESAR GASTO FACTURA INICIADA ===")
    logger.info(f"Usuario: {request.user.username}")
    logger.info(f"M&eacute;todo HTTP: {request.method}")
    logger.info(f"HTMX: {_is_htmx(request)}")

    if request.method == 'POST':
        logger.info("Procesando formulario POST...")
        form = FacturaUploadForm(request.POST, request.FILES)

        if form.is_valid():
            logger.info("&#9989; Formulario v&aacute;lido")
            documento_pdf = request.FILES['documento_pdf']
            tipo_documento = form.cleaned_data['tipo_documento']
            asignar_categorias = form.cleaned_data.get('asignar_categorias', False)
            modelo_ia = form.cleaned_data.get('modelo_ia', None)

            # El reconocimiento necesita una ruta local, pero el documento aún
            # no es un archivo persistente: se usa el directorio temporal del SO.
            suffix = Path(documento_pdf.name).suffix
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as destination:
                temp_file_path = destination.name
                for chunk in documento_pdf.chunks():
                    destination.write(chunk)

            try:
                with open(temp_file_path, 'rb') as pdf_file:
                    if tipo_documento == 'auto':
                        tipo_documento = detectar_tipo_documento(pdf_file)
                        pdf_file.seek(0)

                    if tipo_documento == 'estado_cuenta':
                        datos_extraidos = reconocer_estado_cuenta_pdf(pdf_file, asignar_categorias_automaticamente=asignar_categorias, modelo=modelo_ia)
                        if 'error' in datos_extraidos:
                            return _render_htmx_or_full(request, 'gastos/ingresar_gasto_factura.html', 'gastos/ingresar_gasto_factura.html', {
                                'form': form, 'error': datos_extraidos['error']
                            })
                        movimientos = datos_extraidos.get('movimientos', [])
                        return _render_htmx_or_full(request, 'gastos/confirmar_estado_cuenta.html', 'gastos/partials/confirmar_estado_cuenta.html', {
                            'estado_cuenta': datos_extraidos, 'movimientos': movimientos
                        })
                    else:
                        datos_extraidos = reconocer_factura_pdf(pdf_file, modelo=modelo_ia)
                        if 'error' in datos_extraidos:
                            return _render_htmx_or_full(request, 'gastos/ingresar_gasto_factura.html', 'gastos/ingresar_gasto_factura.html', {
                                'form': form, 'error': datos_extraidos['error']
                            })
                        gasto_form = GastoForm(initial={
                            'monto': datos_extraidos.get('total'),
                            'descripcion': datos_extraidos.get('descripcion'),
                            'fecha': datos_extraidos.get('fecha'),
                        })
                        return _render_htmx_or_full(request, 'gastos/confirmar_gasto_factura.html', 'gastos/partials/confirmar_gasto_factura.html', {
                            'gasto_form': gasto_form, 'proveedor': datos_extraidos.get('proveedor')
                        })
            except Exception as e:
                logger.error(f"Error general: {e}", exc_info=True)
                return _render_htmx_or_full(request, 'gastos/ingresar_gasto_factura.html', 'gastos/ingresar_gasto_factura.html', {
                    'form': form, 'error': f'Error al procesar el documento: {str(e)}'
                })
            finally:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
        else:
            logger.warning(f"&#10060; Formulario no v&aacute;lido: {form.errors}")
    else:
        form = FacturaUploadForm()

    return render(request, 'gastos/ingresar_gasto_factura.html', {'form': form})


@login_required
def guardar_gasto_factura(request):
    """
    Guarda el gasto confirmado por el usuario.
    Con HTMX devuelve toast de &eacute;xito sin redirecci&oacute;n forzada.
    """
    logger.info("=== VISTA GUARDAR GASTO FACTURA INICIADA ===")
    logger.info(f"Usuario: {request.user.username}")

    if request.method == 'POST':
        gasto_form = GastoForm(request.POST)
        if gasto_form.is_valid():
            gasto = gasto_form.save()
            if _is_htmx(request):
                response = HttpResponse(
                    f'<div class="text-center py-12">'
                    f'<div class="inline-flex items-center justify-center w-16 h-16 bg-[#5a7d6b] rounded-xl mb-4 shadow-lg">'
                    f'<svg class="w-8 h-8 text-[#f4f4f9]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>'
                    f'</div><h2 class="text-2xl font-bold text-[#2f4550] mb-2">&#161;Gasto guardado exitosamente!</h2>'
                    f'<p class="text-[#586f7c] mb-6">El gasto ha sido registrado correctamente.</p>'
                    f'<a href="{reverse("gastos:ingresar_gasto_factura")}" class="inline-flex items-center px-6 py-3 border border-transparent text-sm font-medium rounded-lg text-[#f4f4f9] bg-gradient-to-r from-[#2f4550] to-[#2f4550] hover:from-[#2f4550] hover:to-[#586f7c] shadow-lg">'
                    f'<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path></svg>'
                    f'Procesar otro documento</a>'
                    f'</div>'
                )
                return _hx_trigger_response(response, 'success', 'Gasto guardado', f'El gasto por ${gasto.monto} fue registrado correctamente.')
            return redirect('gastos:compras_balances')

    return redirect('gastos:ingresar_gasto_factura')


@login_required
def guardar_gastos_estado_cuenta(request):
    """
    Guarda m&uacute;ltiples gastos seleccionados desde un estado de cuenta.
    Con HTMX devuelve resultado parcial con toast.
    """
    logger.info("=== VISTA GUARDAR GASTOS ESTADO DE CUENTA INICIADA ===")
    logger.info(f"Usuario: {request.user.username}")

    if request.method == 'POST':
        movimientos_seleccionados = request.POST.getlist('movimientos_seleccionados')
        gastos_creados = 0
        errores = []

        for i, movimiento_id in enumerate(movimientos_seleccionados):
            try:
                fecha = request.POST.get(f'movimiento_{movimiento_id}_fecha')
                descripcion = request.POST.get(f'movimiento_{movimiento_id}_descripcion')
                monto = request.POST.get(f'movimiento_{movimiento_id}_monto')
                categoria = request.POST.get(f'movimiento_{movimiento_id}_categoria')
                cuenta = request.POST.get(f'movimiento_{movimiento_id}_cuenta')

                if not all([fecha, descripcion, monto, categoria, cuenta]):
                    errores.append(f"Datos incompletos para el movimiento {i+1}")
                    continue

                def normalizar_monto(monto_str):
                    if isinstance(monto_str, str):
                        monto_limpio = monto_str.strip().replace('$', '').replace(' ', '')
                        if ',' not in monto_limpio:
                            return monto_limpio
                        if '.' in monto_limpio and ',' in monto_limpio:
                            partes = monto_limpio.split(',')
                            if len(partes) == 2:
                                parte_entera = partes[0].replace('.', '')
                                parte_decimal = partes[1]
                                monto_limpio = f"{parte_entera}.{parte_decimal}"
                        else:
                            monto_limpio = monto_limpio.replace(',', '.')
                        return monto_limpio
                    return monto_str

                monto_normalizado = normalizar_monto(monto)
                monto_float = float(monto_normalizado)

                from .models import Gastos, CatGastos, Cuenta
                from catalogo.models import Sucursal
                sucursal_default = Sucursal.objects.first()
                if not sucursal_default:
                    errores.append("No hay sucursales registradas en el sistema")
                    continue

                gasto = Gastos(
                    monto=abs(monto_float),
                    descripcion=descripcion,
                    fecha=fecha,
                    id_sucursal=sucursal_default,
                    id_cat_gastos=CatGastos.objects.get(id=categoria),
                    id_cuenta_banco=Cuenta.objects.get(id=cuenta)
                )
                gasto.save()
                gastos_creados += 1

            except CatGastos.DoesNotExist:
                errores.append(f"Categor&iacute;a no encontrada para movimiento {i+1}")
            except Cuenta.DoesNotExist:
                errores.append(f"Cuenta no encontrada para movimiento {i+1}")
            except ValueError as e:
                errores.append(f"Error en formato de datos para movimiento {i+1}: {str(e)}")
            except Exception as e:
                errores.append(f"Error al guardar movimiento {i+1}: {str(e)}")

        if gastos_creados > 0:
            if errores:
                mensaje = f"Se registraron {gastos_creados} gastos exitosamente, pero se encontraron {len(errores)} errores."
            else:
                mensaje = f"Se registraron todos los {gastos_creados} gastos exitosamente."
        else:
            mensaje = "No se pudo registrar ning&uacute;n gasto."

        context = {'gastos_creados': gastos_creados, 'errores': errores, 'mensaje': mensaje}

        if _is_htmx(request):
            response = render(request, 'gastos/partials/resultado_estado_cuenta.html', context)
            if gastos_creados > 0 and not errores:
                response = _hx_trigger_response(response, 'success', 'Gastos registrados', f'{gastos_creados} movimientos guardados exitosamente.')
            elif gastos_creados > 0 and errores:
                response = _hx_trigger_response(response, 'warning', 'Gastos parciales', f'{gastos_creados} guardados, {len(errores)} errores.')
            else:
                response = _hx_trigger_response(response, 'error', 'Error al registrar', 'No se pudo registrar ning&uacute;n gasto.')
            return response

        return render(request, 'gastos/resultado_estado_cuenta.html', context)

    return redirect('gastos:ingresar_gasto_factura')



from django.db import transaction
from django.http import FileResponse, Http404
from .forms import ComprobanteUploadForm
from .models import ComprobanteGasto
from .services.receipt_service import create_receipt, process_next_receipt


def _comprobante_para_usuario(request, pk):
    comprobante = get_object_or_404(ComprobanteGasto, pk=pk)
    if not request.user.is_staff and comprobante.creado_por_id != request.user.id:
        raise Http404('Comprobante no encontrado.')
    return comprobante


@login_required
def capturar_comprobante(request):
    if request.method == 'POST':
        form = ComprobanteUploadForm(request.POST, request.FILES)
        if form.is_valid():
            comprobante = create_receipt(form.cleaned_data['comprobante'], request.user)
            # Docker runs a dedicated worker. Local DEBUG starts a daemon worker so
            # runserver remains usable without a second terminal.
            if settings.DEBUG:
                threading.Thread(target=process_next_receipt, daemon=True, name='receipt-ocr').start()
            return redirect('gastos:revisar_comprobante', pk=comprobante.pk)
    else:
        form = ComprobanteUploadForm()
    return render(request, 'gastos/capturar_comprobante.html', {'form': form})


@login_required
def revisar_comprobante(request, pk):
    comprobante = _comprobante_para_usuario(request, pk)
    if request.method == 'POST':
        with transaction.atomic():
            comprobante = ComprobanteGasto.objects.select_for_update().get(pk=comprobante.pk)
            if comprobante.estado != ComprobanteGasto.Estado.REVISION:
                raise Http404('El comprobante a?n no est? listo para revisi?n.')
            form = GastoForm(request.POST)
            if form.is_valid():
                gasto = form.save()
                comprobante.gasto = gasto
                comprobante.estado = ComprobanteGasto.Estado.REGISTRADO
                comprobante.save(update_fields=['gasto', 'estado'])
                return redirect('gastos:revisar_comprobante', pk=comprobante.pk)
    else:
        extracted = comprobante.datos_extraidos or {}
        form = GastoForm(initial={'monto': extracted.get('total'), 'fecha': extracted.get('fecha'), 'descripcion': extracted.get('descripcion')})
    return render(request, 'gastos/revisar_comprobante.html', {'comprobante': comprobante, 'gasto_form': form})


@login_required
def estado_comprobante(request, pk):
    comprobante = _comprobante_para_usuario(request, pk)
    return JsonResponse({'estado': comprobante.estado, 'detalle_url': reverse('gastos:revisar_comprobante', kwargs={'pk': comprobante.pk})})


@login_required
@require_POST
def reintentar_comprobante(request, pk):
    comprobante = _comprobante_para_usuario(request, pk)
    if comprobante.estado == ComprobanteGasto.Estado.ERROR:
        comprobante.estado, comprobante.error_procesamiento = ComprobanteGasto.Estado.PENDIENTE, ''
        comprobante.save(update_fields=['estado', 'error_procesamiento'])
    return redirect('gastos:revisar_comprobante', pk=comprobante.pk)


@login_required
def archivo_comprobante(request, pk):
    comprobante = _comprobante_para_usuario(request, pk)
    return FileResponse(comprobante.archivo.open('rb'), content_type=comprobante.content_type, filename=comprobante.nombre_original)
