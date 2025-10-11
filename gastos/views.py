from django.shortcuts import render, redirect, get_object_or_404
from .forms import GastoForm
from .models import Cuenta, Compra, Banco, SaldoMensual
from catalogo.models import Productor, Producto
from django.utils import timezone
import decimal
import numpy as np
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.db.models import Sum, Avg, Count, Max, Min
from django.contrib.auth.decorators import user_passes_test
from datetime import date, datetime, timedelta
import json
from app.services.utils import UtilService
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .forms import CompraForm
from .services.invoice_recognition_service import reconocer_factura_pdf, reconocer_estado_cuenta_pdf, detectar_tipo_documento
from .forms import FacturaUploadForm, GastoForm
from .models import Gastos
import os
import logging
from django.conf import settings

# Configurar logger para las vistas
logger = logging.getLogger(__name__)

@login_required
def ingresar_gasto_factura(request):
    """
    Vista para ingresar gastos a partir de una factura o estado de cuenta en PDF.
    """
    logger.info("=== VISTA INGRESAR GASTO FACTURA INICIADA ===")
    logger.info(f"Usuario: {request.user.username}")
    logger.info(f"Método HTTP: {request.method}")
    
    if request.method == 'POST':
        logger.info("Procesando formulario POST...")
        form = FacturaUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            logger.info("✅ Formulario válido")
            documento_pdf = request.FILES['documento_pdf']
            tipo_documento = form.cleaned_data['tipo_documento']
            asignar_categorias = form.cleaned_data.get('asignar_categorias', False)
            
            logger.info(f"Archivo recibido: {documento_pdf.name}")
            logger.info(f"Tamaño del archivo: {documento_pdf.size} bytes")
            logger.info(f"Tipo de documento seleccionado: {tipo_documento}")
            logger.info(f"Asignación automática de categorías: {'SÍ' if asignar_categorias else 'NO'}")
            
            # Guardar temporalmente el archivo
            temp_file_path = os.path.join(settings.MEDIA_ROOT, 'temp_documents', documento_pdf.name)
            logger.info(f"Guardando archivo temporal en: {temp_file_path}")
            
            os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
            with open(temp_file_path, 'wb+') as destination:
                for chunk in documento_pdf.chunks():
                    destination.write(chunk)
            logger.info("✅ Archivo temporal guardado exitosamente")

            try:
                with open(temp_file_path, 'rb') as pdf_file:
                    logger.info("=== INICIANDO PROCESAMIENTO DE DOCUMENTO ===")
                    
                    # Detectar tipo de documento si es automático
                    if tipo_documento == 'auto':
                        logger.info("Detección automática de tipo de documento activada")
                        tipo_documento = detectar_tipo_documento(pdf_file)
                        pdf_file.seek(0)  # Resetear puntero
                        logger.info(f"Tipo detectado automáticamente: {tipo_documento}")
                    else:
                        logger.info(f"Tipo de documento especificado manualmente: {tipo_documento}")
                    
                    # Procesar según el tipo de documento
                    if tipo_documento == 'estado_cuenta':
                        logger.info("=== PROCESANDO COMO ESTADO DE CUENTA ===")
                        # Usar la opción del usuario para asignación automática
                        datos_extraidos = reconocer_estado_cuenta_pdf(pdf_file, asignar_categorias_automaticamente=asignar_categorias)
                        
                        if 'error' in datos_extraidos:
                            logger.error(f"❌ Error en reconocimiento de estado de cuenta: {datos_extraidos['error']}")
                            return render(request, 'gastos/ingresar_gasto_factura.html', {
                                'form': form,
                                'error': datos_extraidos['error']
                            })
                        
                        logger.info("✅ Estado de cuenta procesado exitosamente")
                        movimientos = datos_extraidos.get('movimientos', [])
                        logger.info(f"Redirigiendo a confirmación con {len(movimientos)} movimientos")
                        
                        # Renderizar template para estado de cuenta con tabla de movimientos
                        return render(request, 'gastos/confirmar_estado_cuenta.html', {
                            'estado_cuenta': datos_extraidos,
                            'movimientos': movimientos
                        })
                    
                    else:  # factura
                        logger.info("=== PROCESANDO COMO FACTURA ===")
                        datos_extraidos = reconocer_factura_pdf(pdf_file)
                        
                        if 'error' in datos_extraidos:
                            logger.error(f"❌ Error en reconocimiento de factura: {datos_extraidos['error']}")
                            return render(request, 'gastos/ingresar_gasto_factura.html', {
                                'form': form,
                                'error': datos_extraidos['error']
                            })
                        
                        logger.info("✅ Factura procesada exitosamente")
                        logger.info(f"Datos extraídos: {datos_extraidos}")
                        
                        # Crear formulario de gasto pre-llenado
                        logger.info("Creando formulario de gasto pre-llenado...")
                        gasto_form = GastoForm(initial={
                            'monto': datos_extraidos.get('total'),
                            'descripcion': datos_extraidos.get('descripcion'),
                            'fecha': datos_extraidos.get('fecha'),
                        })
                        
                        logger.info("Redirigiendo a confirmación de factura")
                        return render(request, 'gastos/confirmar_gasto_factura.html', {
                            'gasto_form': gasto_form,
                            'proveedor': datos_extraidos.get('proveedor')
                        })
                        
            except Exception as e:
                logger.error("=== ERROR GENERAL EN PROCESAMIENTO ===")
                logger.error(f"Tipo de error: {type(e).__name__}")
                logger.error(f"Mensaje: {str(e)}")
                logger.error(f"Detalles completos:", exc_info=True)
                
                return render(request, 'gastos/ingresar_gasto_factura.html', {
                    'form': form,
                    'error': f'Error al procesar el documento: {str(e)}'
                })
                        
            finally:
                # Eliminar archivo temporal
                logger.info("Limpiando archivo temporal...")
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    logger.info("✅ Archivo temporal eliminado")
                else:
                    logger.warning("⚠️ Archivo temporal no encontrado para eliminar")
        else:
            logger.warning("❌ Formulario no válido")
            logger.warning(f"Errores del formulario: {form.errors}")
    else:
        logger.info("Mostrando formulario GET (inicial)")
        form = FacturaUploadForm()
    
    logger.info("=== VISTA INGRESAR GASTO FACTURA FINALIZADA ===")
    return render(request, 'gastos/ingresar_gasto_factura.html', {'form': form})

@login_required
def guardar_gasto_factura(request):
    """
    Guarda el gasto confirmado por el usuario.
    """
    logger.info("=== VISTA GUARDAR GASTO FACTURA INICIADA ===")
    logger.info(f"Usuario: {request.user.username}")
    
    if request.method == 'POST':
        logger.info("Procesando guardado de gasto desde factura...")
        gasto_form = GastoForm(request.POST)
        if gasto_form.is_valid():
            gasto_form.save()
            return redirect('gastos:compras_balances') # Redirigir a una vista de éxito
    
    # Si el formulario no es válido, o no es un POST, redirigir al inicio del proceso
    return redirect('gastos:ingresar_gasto_factura')

@login_required
def guardar_gastos_estado_cuenta(request):
    """
    Guarda múltiples gastos seleccionados desde un estado de cuenta.
    """
    logger.info("=== VISTA GUARDAR GASTOS ESTADO DE CUENTA INICIADA ===")
    logger.info(f"Usuario: {request.user.username}")
    
    if request.method == 'POST':
        logger.info("Procesando guardado de gastos desde estado de cuenta...")
        
        # Obtener los movimientos seleccionados
        movimientos_seleccionados = request.POST.getlist('movimientos_seleccionados')
        logger.info(f"Movimientos seleccionados: {len(movimientos_seleccionados)}")
        logger.info(f"IDs de movimientos: {movimientos_seleccionados}")
        
        gastos_creados = 0
        errores = []
        
        for i, movimiento_id in enumerate(movimientos_seleccionados):
            logger.info(f"--- Procesando movimiento {i+1}/{len(movimientos_seleccionados)} (ID: {movimiento_id}) ---")
            
            try:
                # Obtener datos del movimiento desde el formulario
                fecha = request.POST.get(f'movimiento_{movimiento_id}_fecha')
                descripcion = request.POST.get(f'movimiento_{movimiento_id}_descripcion')
                monto = request.POST.get(f'movimiento_{movimiento_id}_monto')
                categoria = request.POST.get(f'movimiento_{movimiento_id}_categoria')
                cuenta = request.POST.get(f'movimiento_{movimiento_id}_cuenta')
                
                logger.info(f"Datos del movimiento {i+1}:")
                logger.info(f"  - Fecha: {fecha}")
                logger.info(f"  - Descripción: {descripcion}")
                logger.info(f"  - Monto: {monto}")
                logger.info(f"  - Categoría ID: {categoria}")
                logger.info(f"  - Cuenta ID: {cuenta}")
                
                # Validar que los datos estén completos
                if not all([fecha, descripcion, monto, categoria, cuenta]):
                    error_msg = f"Datos incompletos para el movimiento {i+1}"
                    logger.warning(f"⚠️ {error_msg}")
                    errores.append(error_msg)
                    continue
                
                # Normalizar el formato del monto (convertir comas a puntos)
                def normalizar_monto(monto_str):
                    """Convierte formato de número con coma a formato con punto para float"""
                    if isinstance(monto_str, str):
                        # Remover espacios y signos de moneda
                        monto_limpio = monto_str.strip().replace('$', '').replace(' ', '')
                        
                        # Si contiene solo números, punto y/o signo negativo, ya está en formato correcto
                        if ',' not in monto_limpio:
                            return monto_limpio
                        
                        # Determinar si la coma es separador decimal o de miles
                        # Si hay punto Y coma, la coma probablemente es decimal
                        if '.' in monto_limpio and ',' in monto_limpio:
                            # Formato como 1.234,56 - punto para miles, coma para decimales
                            partes = monto_limpio.split(',')
                            if len(partes) == 2:
                                parte_entera = partes[0].replace('.', '')  # Remover puntos de miles
                                parte_decimal = partes[1]
                                monto_limpio = f"{parte_entera}.{parte_decimal}"
                        else:
                            # Solo hay comas, probablemente es separador decimal
                            monto_limpio = monto_limpio.replace(',', '.')
                        
                        return monto_limpio
                    return monto_str
                
                # Aplicar normalización al monto
                try:
                    monto_normalizado = normalizar_monto(monto)
                    monto_float = float(monto_normalizado)
                    logger.info(f"Monto original: '{monto}' → normalizado: '{monto_normalizado}' → float: {monto_float}")
                except ValueError as e:
                    error_msg = f"Error en formato de datos para movimiento {i+1}: {str(e)}"
                    logger.error(f"❌ {error_msg}")
                    errores.append(error_msg)
                    continue
                
                # Crear el gasto
                logger.info(f"Creando gasto en base de datos...")
                from .models import Gastos, CatGastos, Cuenta
                from catalogo.models import Sucursal
                
                # Obtener la primera sucursal como default
                sucursal_default = Sucursal.objects.first()
                if not sucursal_default:
                    error_msg = "No hay sucursales registradas en el sistema"
                    logger.error(f"❌ {error_msg}")
                    errores.append(error_msg)
                    continue
                
                logger.info(f"Sucursal default: {sucursal_default}")
                
                gasto = Gastos(
                    monto=abs(monto_float),  # Usar el monto normalizado y convertir a positivo
                    descripcion=descripcion,
                    fecha=fecha,
                    id_sucursal=sucursal_default,
                    id_cat_gastos=CatGastos.objects.get(id=categoria),
                    id_cuenta_banco=Cuenta.objects.get(id=cuenta)
                )
                gasto.save()
                gastos_creados += 1
                
                logger.info(f"✅ Gasto {i+1} creado exitosamente (ID: {gasto.id})")
                
            except CatGastos.DoesNotExist:
                error_msg = f"Categoría no encontrada para movimiento {i+1}"
                logger.error(f"❌ {error_msg}")
                errores.append(error_msg)
            except Cuenta.DoesNotExist:
                error_msg = f"Cuenta no encontrada para movimiento {i+1}"
                logger.error(f"❌ {error_msg}")
                errores.append(error_msg)
            except ValueError as e:
                error_msg = f"Error en formato de datos para movimiento {i+1}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                errores.append(error_msg)
            except Exception as e:
                error_msg = f"Error al guardar movimiento {i+1}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                logger.error(f"Detalles del error:", exc_info=True)
                errores.append(error_msg)
        
        # Preparar mensaje de resultado
        logger.info("=== RESUMEN DEL PROCESAMIENTO ===")
        logger.info(f"Gastos creados exitosamente: {gastos_creados}")
        logger.info(f"Errores encontrados: {len(errores)}")
        
        if errores:
            logger.warning("Lista de errores:")
            for error in errores:
                logger.warning(f"  - {error}")
        
        if gastos_creados > 0:
            if errores:
                mensaje = f"Se registraron {gastos_creados} gastos exitosamente, pero se encontraron {len(errores)} errores."
                logger.info(f"✅ {mensaje}")
            else:
                mensaje = f"Se registraron todos los {gastos_creados} gastos exitosamente."
                logger.info(f"✅ {mensaje}")
        else:
            mensaje = "No se pudo registrar ningún gasto."
            logger.warning(f"⚠️ {mensaje}")
        
        logger.info("Redirigiendo a página de resultados...")
        return render(request, 'gastos/resultado_estado_cuenta.html', {
            'gastos_creados': gastos_creados,
            'errores': errores,
            'mensaje': mensaje
        })
    
    # Si no es POST, redirigir al formulario principal
    logger.warning("Acceso no POST - redirigiendo al formulario principal")
    return redirect('gastos:ingresar_gasto_factura')


from app.services.compras_service import ComprasAnalysisService

@login_required
def compras_balances_view(request):
    """
    Vista para análisis de compras usando el servicio modular
    
    Similar a balances_view pero adaptado para compras de fruta
    """
    service = ComprasAnalysisService()
    context = service.get_full_context(request)
    
    return render(request, 'compras/compras_balances.html', context)
