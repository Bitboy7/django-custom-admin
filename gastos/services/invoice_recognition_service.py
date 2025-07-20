"""
Servicio para el reconocimiento de facturas y estados de cuenta en formato PDF utilizando IA.
"""
import os
import logging
from io import BytesIO
import google.generativeai as genai
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import List

# Configurar logging
logger = logging.getLogger(__name__)

# Configura la API de Google
# Es recomendable almacenar la clave de API en variables de entorno
# y no directamente en el código.
from dotenv import load_dotenv
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

class GastoFactura(BaseModel):
    """
    Modelo de datos para la información extraída de la factura.
    """
    proveedor: str = Field(description="Nombre del proveedor o empresa que emite la factura.")
    fecha: str = Field(description="Fecha de emisión de la factura (formato YYYY-MM-DD).")
    total: float = Field(description="El monto total de la factura.")
    impuestos: float = Field(description="El monto total de impuestos (e.g., IVA).")
    descripcion: str = Field(description="Una descripción breve de los productos o servicios.")

class MovimientoEstadoCuenta(BaseModel):
    """
    Modelo de datos para un movimiento individual del estado de cuenta.
    """
    fecha: str = Field(description="Fecha del movimiento (formato YYYY-MM-DD).")
    descripcion: str = Field(description="Descripción o concepto del movimiento.")
    monto: float = Field(description="Monto del movimiento (positivo para ingresos, negativo para gastos).")
    tipo: str = Field(description="Tipo de movimiento: 'cargo', 'abono', 'comision', 'interes', etc.")
    referencia: str = Field(description="Número de referencia o folio del movimiento.", default="")
    categoria_sugerida: str = Field(description="ID de la categoría más apropiada para este movimiento según las categorías disponibles.", default="")

class EstadoCuentaCompleto(BaseModel):
    """
    Modelo de datos para todo el estado de cuenta.
    """
    banco: str = Field(description="Nombre del banco emisor del estado de cuenta.")
    numero_cuenta: str = Field(description="Número de cuenta (últimos 4 dígitos visibles).")
    periodo_inicio: str = Field(description="Fecha de inicio del periodo (formato YYYY-MM-DD).")
    periodo_fin: str = Field(description="Fecha de fin del periodo (formato YYYY-MM-DD).")
    saldo_inicial: float = Field(description="Saldo inicial del periodo.")
    saldo_final: float = Field(description="Saldo final del periodo.")
    movimientos: List[MovimientoEstadoCuenta] = Field(description="Lista de todos los movimientos del estado de cuenta.")

def reconocer_factura_pdf(pdf_file):
    """
    Procesa un archivo PDF de una factura para extraer información clave.

    Args:
        pdf_file: Un objeto de archivo PDF (por ejemplo, de un FileUpload de Django).

    Returns:
        Un diccionario con la información extraída de la factura.
    """
    logger.info("=== INICIANDO RECONOCIMIENTO DE FACTURA ===")
    logger.info(f"Nombre del archivo: {getattr(pdf_file, 'name', 'desconocido')}")
    logger.info(f"Tamaño del archivo: {getattr(pdf_file, 'size', 'desconocido')} bytes")
    
    try:
        # Guardar el contenido del archivo en un BytesIO para que PyPDFLoader lo pueda leer
        logger.info("Leyendo contenido del PDF...")
        pdf_content = BytesIO(pdf_file.read())
        
        # Crear un cargador de PDF temporal para leer el contenido
        temp_pdf_path = "temp_invoice.pdf"
        logger.info(f"Creando archivo temporal: {temp_pdf_path}")
        
        with open(temp_pdf_path, "wb") as f:
            f.write(pdf_content.getvalue())

        logger.info("Cargando PDF con PyPDFLoader...")
        loader = PyPDFLoader(temp_pdf_path)
        pages = loader.load_and_split()
        
        # Limpiar el archivo temporal
        os.remove(temp_pdf_path)
        logger.info("Archivo temporal eliminado")

        if not pages:
            logger.error("No se pudo leer el contenido del PDF - páginas vacías")
            return {"error": "No se pudo leer el contenido del PDF."}

        logger.info(f"PDF cargado exitosamente - {len(pages)} páginas encontradas")
        contenido_factura = " ".join(page.page_content for page in pages)
        logger.info(f"Contenido extraído: {len(contenido_factura)} caracteres")
        logger.debug(f"Primeros 200 caracteres del contenido: {contenido_factura[:200]}...")

        # Configurar el modelo de Gemini
        logger.info("Configurando modelo Google Gemini...")
        model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0)

        # Configurar el parser para obtener una salida JSON
        logger.info("Configurando parser JSON con modelo Pydantic...")
        parser = JsonOutputParser(pydantic_object=GastoFactura)

        # Crear el prompt para la extracción de información
        logger.info("Creando prompt para extracción de información...")
        prompt = PromptTemplate(
            template="""
            Eres un asistente experto en extraer información de facturas.
            Analiza el siguiente texto de una factura y extrae los datos solicitados.
            
            Texto de la factura:
            {factura}

            {format_instructions}
            """,
            input_variables=["factura"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        # Crear la cadena de procesamiento (chain)
        logger.info("Creando cadena de procesamiento LangChain...")
        chain = prompt | model | parser

        # Invocar la cadena con el contenido de la factura
        logger.info("=== INVOCANDO IA PARA PROCESAMIENTO ===")
        logger.info("Enviando contenido a Google Gemini para análisis...")
        
        resultado = chain.invoke({"factura": contenido_factura})
        
        logger.info("=== RESPUESTA DE IA RECIBIDA ===")
        logger.info(f"Tipo de resultado: {type(resultado)}")
        logger.info(f"Contenido del resultado: {resultado}")
        
        # Validar estructura del resultado
        if isinstance(resultado, dict):
            logger.info("✅ Resultado válido recibido de la IA")
            logger.info(f"Proveedor extraído: {resultado.get('proveedor', 'N/A')}")
            logger.info(f"Fecha extraída: {resultado.get('fecha', 'N/A')}")
            logger.info(f"Total extraído: {resultado.get('total', 'N/A')}")
            logger.info(f"Impuestos extraídos: {resultado.get('impuestos', 'N/A')}")
        else:
            logger.warning(f"⚠️ Resultado inesperado de la IA: {type(resultado)}")

        logger.info("=== RECONOCIMIENTO DE FACTURA COMPLETADO EXITOSAMENTE ===")
        return resultado

    except Exception as e:
        # Manejo de errores en caso de que la API falle o el PDF sea inválido
        logger.error("=== ERROR EN RECONOCIMIENTO DE FACTURA ===")
        logger.error(f"Tipo de error: {type(e).__name__}")
        logger.error(f"Mensaje de error: {str(e)}")
        logger.error(f"Detalles completos del error:", exc_info=True)
        
        error_message = f"Ocurrió un error al procesar la factura: {str(e)}"
        logger.error(f"Mensaje de error para usuario: {error_message}")
        
        return {"error": error_message}

def obtener_categorias_disponibles():
    """
    Obtiene todas las categorías de gastos disponibles en la base de datos.
    
    Returns:
        dict: Diccionario con ID y nombre de las categorías
    """
    try:
        from gastos.models import CatGastos
        
        categorias = CatGastos.objects.all()
        categorias_dict = {str(cat.id): cat.nombre for cat in categorias}
        
        logger.info(f"Categorías disponibles obtenidas: {len(categorias_dict)}")
        logger.debug(f"Categorías: {categorias_dict}")
        
        return categorias_dict
    except Exception as e:
        logger.error(f"Error al obtener categorías: {str(e)}")
        return {}

import time

def asignar_categoria_automatica(descripcion_movimiento, categorias_disponibles):
    """
    Utiliza Google Gemini para asignar automáticamente una categoría de gasto basándose 
    en la descripción del movimiento.
    
    Args:
        descripcion_movimiento (str): Descripción del movimiento bancario
        categorias_disponibles (dict): Diccionario de categorías disponibles {id: nombre}
    
    Returns:
        dict: Información de la categoría asignada {'id': int, 'nombre': str} o None si no se pudo asignar
    """
    if not descripcion_movimiento or not descripcion_movimiento.strip():
        logger.warning("⚠️ Descripción vacía - no se puede asignar categoría")
        return None
    
    if not categorias_disponibles:
        logger.warning("⚠️ No hay categorías disponibles")
        return None
    
    try:
        logger.info(f"Asignando categoría automática para: '{descripcion_movimiento}'")
        
        # Configurar el modelo de Gemini
        model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0)
        
        # Preparar lista de categorías para el prompt
        categorias_lista = "\n".join([f"- {cat_id}: {nombre}" for cat_id, nombre in categorias_disponibles.items()])
        
        # Crear el prompt
        prompt = f"""
        Analiza la siguiente descripción de un movimiento bancario y asigna la categoría de gasto más apropiada:

        DESCRIPCIÓN: "{descripcion_movimiento}"

        CATEGORÍAS DISPONIBLES:
        {categorias_lista}

        INSTRUCCIONES:
        1. Analiza la descripción y determina qué tipo de gasto representa
        2. Selecciona ÚNICAMENTE el ID numérico de la categoría más apropiada de la lista
        3. Si ninguna categoría es apropiada, responde exactamente: "NINGUNA"
        4. Responde SOLO con el número ID, sin explicaciones adicionales

        RESPUESTA:
        """

        # Hacer la consulta a Gemini
        response = model.predict(prompt)
        
        # Limpiar y procesar la respuesta
        categoria_id = response.strip()
        logger.info(f"Respuesta de IA para '{descripcion_movimiento}': '{categoria_id}'")
        
        # Verificar si la IA no encontró categoría apropiada
        if categoria_id.upper() in ['NINGUNA', 'NONE', 'N/A', 'NO']:
            logger.info("IA determinó que no hay categoría apropiada")
            return None
        
        if categoria_id in categorias_disponibles:
            categoria_nombre = categorias_disponibles[categoria_id]
            logger.info(f"✅ Categoría asignada: {categoria_nombre} (ID: {categoria_id})")
            return {
                'id': int(categoria_id),  # Convertir a entero para compatibilidad con Django
                'nombre': categoria_nombre
            }
        else:
            logger.warning(f"⚠️ IA devolvió ID inválido: {categoria_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error en asignación automática de categoría: {str(e)}")
        return None

def asignar_categorias_en_lotes(movimientos_gastos, categorias_disponibles, tamaño_lote=3, delay_entre_lotes=2):
    """
    Procesa la asignación de categorías en lotes para evitar límites de API.
    
    Args:
        movimientos_gastos (list): Lista de tuplas (índice, movimiento) a procesar
        categorias_disponibles (dict): Diccionario de categorías disponibles
        tamaño_lote (int): Número de movimientos a procesar por lote
        delay_entre_lotes (int): Segundos de espera entre lotes
    
    Returns:
        None: Modifica los movimientos in-place
    """
    total_movimientos = len(movimientos_gastos)
    logger.info(f"=== PROCESAMIENTO EN LOTES ===")
    logger.info(f"Total de movimientos a procesar: {total_movimientos}")
    logger.info(f"Tamaño de lote: {tamaño_lote}")
    logger.info(f"Delay entre lotes: {delay_entre_lotes} segundos")
    
    for i in range(0, total_movimientos, tamaño_lote):
        lote = movimientos_gastos[i:i+tamaño_lote]
        numero_lote = (i // tamaño_lote) + 1
        total_lotes = (total_movimientos + tamaño_lote - 1) // tamaño_lote
        
        logger.info(f"--- Procesando lote {numero_lote}/{total_lotes} ({len(lote)} movimientos) ---")
        
        for idx_en_lote, (indice_original, movimiento) in enumerate(lote):
            descripcion_movimiento = movimiento.get('descripcion', '')
            monto = movimiento.get('monto', 0)
            
            logger.info(f"Procesando {idx_en_lote + 1}/{len(lote)} en lote {numero_lote}: '{descripcion_movimiento}' (${monto})")
            
            try:
                categoria_info = asignar_categoria_automatica(descripcion_movimiento, categorias_disponibles)
                
                if categoria_info:
                    movimiento['categoria_sugerida'] = categoria_info
                    logger.info(f"✅ Categoría asignada: {categoria_info['nombre']} (ID: {categoria_info['id']})")
                else:
                    logger.info(f"⚠️ No se pudo asignar categoría")
                    
            except Exception as e:
                logger.error(f"❌ Error al procesar movimiento: {str(e)}")
                continue
        
        # Delay entre lotes (excepto el último)
        if i + tamaño_lote < total_movimientos:
            logger.info(f"⏳ Esperando {delay_entre_lotes} segundos antes del siguiente lote...")
            time.sleep(delay_entre_lotes)
    
    logger.info(f"=== PROCESAMIENTO EN LOTES COMPLETADO ===")

def asignar_categoria_automatica_old(descripcion_movimiento, categorias_disponibles):
    """
    Usa IA para asignar automáticamente la categoría más apropiada basada en la descripción.
    
    Args:
        descripcion_movimiento (str): Descripción del movimiento bancario
        categorias_disponibles (dict): Diccionario con las categorías disponibles {id: nombre}
        
    Returns:
        str: ID de la categoría más apropiada o string vacío si no se puede determinar
    """
    if not categorias_disponibles or not descripcion_movimiento:
        return ""
    
    logger.info(f"Asignando categoría para: '{descripcion_movimiento}'")
    
    try:
        # Preparar el prompt para clasificación
        categorias_texto = "\n".join([f"ID: {id_cat}, Nombre: {nombre}" for id_cat, nombre in categorias_disponibles.items()])
        
        # Configurar el modelo
        model = ChatGoogleGenerativeAI(model=os.getenv("GOOGLE_API_MODEL"), temperature=0)

        prompt_template = """
        Eres un asistente experto en clasificación de gastos bancarios.
        
        TAREA: Analiza la siguiente descripción de un movimiento bancario y selecciona la categoría MÁS APROPIADA de la lista disponible.
        
        DESCRIPCIÓN DEL MOVIMIENTO: "{descripcion}"
        
        CATEGORÍAS DISPONIBLES:
        {categorias}
        
        INSTRUCCIONES:
        1. Analiza cuidadosamente la descripción del movimiento
        2. Considera palabras clave, tipo de establecimiento, servicio o producto
        3. Selecciona ÚNICAMENTE el ID de la categoría más apropiada de la lista
        4. Si no hay una categoría claramente apropiada, responde con "NO_MATCH"
        5. Responde SOLO con el ID de la categoría (ejemplo: "3") o "NO_MATCH"
        
        EJEMPLOS:
        - "PAGO TARJETA CREDITO" → categoría de servicios financieros
        - "FARMACIA GUADALAJARA" → categoría de salud/medicinas
        - "GASOLINA PEMEX" → categoría de combustible/transporte
        - "DEPOSITO NOMINA" → NO_MATCH (es ingreso, no gasto)
        
        RESPUESTA:
        """
        
        prompt = prompt_template.format(
            descripcion=descripcion_movimiento,
            categorias=categorias_texto
        )
        
        logger.debug(f"Enviando prompt para clasificación: {prompt[:200]}...")
        
        # Invocar el modelo
        respuesta = model.invoke(prompt)
        categoria_id = respuesta.content.strip()
        
        logger.info(f"Respuesta de IA para categorización: '{categoria_id}'")
        
        # Validar que la respuesta sea un ID válido
        if categoria_id == "NO_MATCH":
            logger.info("IA determinó que no hay categoría apropiada")
            return None
        
        if categoria_id in categorias_disponibles:
            categoria_nombre = categorias_disponibles[categoria_id]
            logger.info(f"✅ Categoría asignada: {categoria_nombre} (ID: {categoria_id})")
            return {
                'id': int(categoria_id),  # Convertir a entero para compatibilidad con Django
                'nombre': categoria_nombre
            }
        else:
            logger.warning(f"⚠️ IA devolvió ID inválido: {categoria_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error en asignación automática de categoría: {str(e)}")
        return None

def reconocer_estado_cuenta_pdf(pdf_file, asignar_categorias_automaticamente=False):
    """
    Procesa un archivo PDF de un estado de cuenta bancario para extraer todos los movimientos.

    Args:
        pdf_file: Un objeto de archivo PDF del estado de cuenta.
        asignar_categorias_automaticamente: Si es True, intenta asignar categorías automáticamente (puede ser lento).

    Returns:
        Un diccionario con la información extraída del estado de cuenta.
    """
    logger.info("=== INICIANDO RECONOCIMIENTO DE ESTADO DE CUENTA ===")
    logger.info(f"Nombre del archivo: {getattr(pdf_file, 'name', 'desconocido')}")
    logger.info(f"Tamaño del archivo: {getattr(pdf_file, 'size', 'desconocido')} bytes")
    
    try:
        # Guardar el contenido del archivo en un BytesIO
        logger.info("Leyendo contenido del PDF del estado de cuenta...")
        pdf_content = BytesIO(pdf_file.read())
        
        # Crear un cargador de PDF temporal
        temp_pdf_path = "temp_statement.pdf"
        logger.info(f"Creando archivo temporal: {temp_pdf_path}")
        
        with open(temp_pdf_path, "wb") as f:
            f.write(pdf_content.getvalue())

        logger.info("Cargando PDF con PyPDFLoader...")
        loader = PyPDFLoader(temp_pdf_path)
        pages = loader.load_and_split()
        
        # Limpiar el archivo temporal
        os.remove(temp_pdf_path)
        logger.info("Archivo temporal eliminado")

        if not pages:
            logger.error("No se pudo leer el contenido del PDF - páginas vacías")
            return {"error": "No se pudo leer el contenido del PDF."}

        logger.info(f"PDF cargado exitosamente - {len(pages)} páginas encontradas")
        contenido_estado = " ".join(page.page_content for page in pages)
        logger.info(f"Contenido extraído: {len(contenido_estado)} caracteres")
        logger.debug(f"Primeros 300 caracteres del contenido: {contenido_estado[:300]}...")

        # Configurar el modelo de Gemini para estados de cuenta
        logger.info("Configurando modelo Google Gemini para estados de cuenta...")
        model = ChatGoogleGenerativeAI(model=os.getenv("GOOGLE_API_MODEL"), temperature=0)

        # Configurar el parser para obtener una salida JSON
        logger.info("Configurando parser JSON con modelo EstadoCuentaCompleto...")
        parser = JsonOutputParser(pydantic_object=EstadoCuentaCompleto)

        # Crear el prompt especializado para estados de cuenta
        logger.info("Creando prompt especializado para estados de cuenta...")
        prompt = PromptTemplate(
            template="""
            Eres un asistente experto en analizar estados de cuenta bancarios.
            Analiza el siguiente texto de un estado de cuenta y extrae TODOS los movimientos y datos solicitados.
            
            INSTRUCCIONES ESPECÍFICAS:
            1. Identifica todos los movimientos/transacciones en el estado de cuenta
            2. Para cada movimiento, extrae: fecha, descripción, monto, tipo y referencia
            3. Los montos negativos son gastos/cargos, los positivos son ingresos/abonos
            4. Incluye comisiones, intereses, transferencias, pagos, etc.
            5. No omitas ningún movimiento, por pequeño que sea
            6. Si hay abreviaciones bancarias, interprétalas (ej: TRF = Transferencia, COM = Comisión)
            
            Texto del estado de cuenta:
            {estado_cuenta}

            {format_instructions}
            """,
            input_variables=["estado_cuenta"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        # Crear la cadena de procesamiento
        logger.info("Creando cadena de procesamiento LangChain...")
        chain = prompt | model | parser

        # Invocar la cadena con el contenido del estado de cuenta
        logger.info("=== INVOCANDO IA PARA PROCESAMIENTO DE ESTADO DE CUENTA ===")
        logger.info("Enviando contenido a Google Gemini para análisis...")
        
        resultado = chain.invoke({"estado_cuenta": contenido_estado})
        
        logger.info("=== RESPUESTA DE IA RECIBIDA ===")
        logger.info(f"Tipo de resultado: {type(resultado)}")
        
        # Validar estructura del resultado
        if isinstance(resultado, dict):
            logger.info("✅ Resultado válido recibido de la IA")
            logger.info(f"Banco extraído: {resultado.get('banco', 'N/A')}")
            logger.info(f"Número de cuenta: {resultado.get('numero_cuenta', 'N/A')}")
            logger.info(f"Periodo: {resultado.get('periodo_inicio', 'N/A')} - {resultado.get('periodo_fin', 'N/A')}")
            
            movimientos = resultado.get('movimientos', [])
            logger.info(f"Número de movimientos extraídos: {len(movimientos)}")
            
            # Solo procesar categorías automáticamente si se solicita
            if movimientos and asignar_categorias_automaticamente:
                logger.info("=== INICIANDO ASIGNACIÓN AUTOMÁTICA DE CATEGORÍAS ===")
                logger.warning("⚠️ ATENCIÓN: La asignación automática puede exceder los límites de la API de Gemini")
                
                # Obtener categorías disponibles
                categorias_disponibles = obtener_categorias_disponibles()
                
                if categorias_disponibles:
                    # Filtrar solo los gastos (montos negativos) para procesar
                    gastos_a_procesar = [
                        (i, mov) for i, mov in enumerate(movimientos) 
                        if mov.get('monto', 0) < 0 and mov.get('descripcion', '').strip()
                    ]
                    
                    logger.info(f"Movimientos de gastos a procesar: {len(gastos_a_procesar)} de {len(movimientos)} total")
                    
                    if len(gastos_a_procesar) > 15:
                        logger.warning(f"⚠️ ADVERTENCIA: Se detectaron {len(gastos_a_procesar)} movimientos.")
                        logger.warning("⚠️ Esto puede exceder significativamente el límite de la API de Gemini (15 peticiones/minuto).")
                        logger.warning("⚠️ Procesando en lotes pequeños con delays para evitar errores...")
                        
                        # Usar procesamiento en lotes para muchos movimientos
                        asignar_categorias_en_lotes(gastos_a_procesar, categorias_disponibles, tamaño_lote=2, delay_entre_lotes=5)
                        
                    elif len(gastos_a_procesar) > 5:
                        logger.warning(f"⚠️ Procesando {len(gastos_a_procesar)} movimientos en lotes pequeños...")
                        
                        # Usar procesamiento en lotes con delay menor
                        asignar_categorias_en_lotes(gastos_a_procesar, categorias_disponibles, tamaño_lote=3, delay_entre_lotes=3)
                        
                    else:
                        logger.info(f"Procesando {len(gastos_a_procesar)} movimientos secuencialmente...")
                        
                        # Procesar normalmente para pocos movimientos
                        for idx, (i, movimiento) in enumerate(gastos_a_procesar):
                            descripcion = movimiento.get('descripcion', '')
                            monto = movimiento.get('monto', 0)
                            
                            logger.info(f"Procesando gasto {idx+1}/{len(gastos_a_procesar)}: '{descripcion}' (${monto})")
                            
                            try:
                                categoria_info = asignar_categoria_automatica_old(descripcion, categorias_disponibles)
                                
                                if categoria_info:
                                    movimiento['categoria_sugerida'] = categoria_info
                                    logger.info(f"✅ Categoría asignada: {categoria_info['nombre']} (ID: {categoria_info['id']})")
                                else:
                                    logger.info(f"⚠️ No se pudo asignar categoría")
                                    
                            except Exception as e:
                                logger.error(f"❌ Error al procesar movimiento {idx+1}: {str(e)}")
                                continue
                    
                    logger.info("=== ASIGNACIÓN DE CATEGORÍAS COMPLETADA ===")
                else:
                    logger.warning("⚠️ No hay categorías disponibles en la base de datos")
            elif movimientos and not asignar_categorias_automaticamente:
                logger.info("ℹ️ Asignación automática de categorías omitida (no solicitada)")
            elif not movimientos:
                logger.warning("⚠️ No se extrajeron movimientos del estado de cuenta")
            
            # Mostrar detalle de movimientos extraídos
            if movimientos:
                logger.info("=== DETALLE DE MOVIMIENTOS EXTRAÍDOS ===")
                for i, mov in enumerate(movimientos[:5]):  # Mostrar solo los primeros 5
                    categoria_info = ""
                    if mov.get('categoria_sugerida'):
                        cat_sug = mov['categoria_sugerida']
                        categoria_info = f" - Categoría: {cat_sug['nombre']} (ID: {cat_sug['id']})"
                    logger.info(f"Movimiento {i+1}: {mov.get('fecha', 'N/A')} - {mov.get('descripcion', 'N/A')} - ${mov.get('monto', 'N/A')}{categoria_info}")
                
                if len(movimientos) > 5:
                    logger.info(f"... y {len(movimientos) - 5} movimientos adicionales")
        else:
            logger.warning(f"⚠️ Resultado inesperado de la IA: {type(resultado)}")

        logger.info("=== RECONOCIMIENTO DE ESTADO DE CUENTA COMPLETADO EXITOSAMENTE ===")
        return resultado

    except Exception as e:
        logger.error("=== ERROR EN RECONOCIMIENTO DE ESTADO DE CUENTA ===")
        logger.error(f"Tipo de error: {type(e).__name__}")
        logger.error(f"Mensaje de error: {str(e)}")
        logger.error(f"Detalles completos del error:", exc_info=True)
        
        error_message = f"Ocurrió un error al procesar el estado de cuenta: {str(e)}"
        logger.error(f"Mensaje de error para usuario: {error_message}")
        
        return {"error": error_message}

def detectar_tipo_documento(pdf_file):
    """
    Detecta si el PDF es una factura o un estado de cuenta.
    
    Args:
        pdf_file: Un objeto de archivo PDF.
        
    Returns:
        str: 'factura' o 'estado_cuenta'
    """
    logger.info("=== INICIANDO DETECCIÓN DE TIPO DE DOCUMENTO ===")
    logger.info(f"Nombre del archivo: {getattr(pdf_file, 'name', 'desconocido')}")
    
    try:
        # Leer una muestra del contenido para detectar el tipo
        logger.info("Leyendo contenido para detección de tipo...")
        pdf_content = BytesIO(pdf_file.read())
        pdf_file.seek(0)  # Resetear el puntero para uso posterior
        
        temp_pdf_path = "temp_detect.pdf"
        logger.info(f"Creando archivo temporal para detección: {temp_pdf_path}")
        
        with open(temp_pdf_path, "wb") as f:
            f.write(pdf_content.getvalue())

        logger.info("Cargando PDF para detección de tipo...")
        loader = PyPDFLoader(temp_pdf_path)
        pages = loader.load_and_split()
        
        os.remove(temp_pdf_path)
        logger.info("Archivo temporal de detección eliminado")

        if not pages:
            logger.warning("No se pudo leer el contenido para detección - usando default 'factura'")
            return "factura"  # Default

        # Tomar solo las primeras páginas para detección rápida
        contenido_muestra = " ".join(page.page_content for page in pages[:2])
        contenido_muestra = contenido_muestra.lower()
        
        logger.info(f"Contenido para análisis: {len(contenido_muestra)} caracteres")
        logger.debug(f"Muestra del contenido: {contenido_muestra[:200]}...")

        # Palabras clave para estado de cuenta
        palabras_estado_cuenta = [
            'estado de cuenta', 'saldo anterior', 'saldo actual', 'movimientos',
            'periodo del', 'al', 'transferencia', 'deposito', 'retiro',
            'comision', 'interes', 'balance', 'statement'
        ]

        # Palabras clave para factura
        palabras_factura = [
            'factura', 'invoice', 'subtotal', 'iva', 'total a pagar',
            'proveedor', 'cliente', 'productos', 'servicios', 'cantidad'
        ]

        logger.info("Analizando palabras clave...")
        score_estado = sum(1 for palabra in palabras_estado_cuenta if palabra in contenido_muestra)
        score_factura = sum(1 for palabra in palabras_factura if palabra in contenido_muestra)
        
        logger.info(f"Score estado de cuenta: {score_estado}")
        logger.info(f"Score factura: {score_factura}")
        
        # Log de palabras encontradas
        palabras_encontradas_estado = [palabra for palabra in palabras_estado_cuenta if palabra in contenido_muestra]
        palabras_encontradas_factura = [palabra for palabra in palabras_factura if palabra in contenido_muestra]
        
        logger.info(f"Palabras de estado de cuenta encontradas: {palabras_encontradas_estado}")
        logger.info(f"Palabras de factura encontradas: {palabras_encontradas_factura}")

        tipo_detectado = "estado_cuenta" if score_estado > score_factura else "factura"
        logger.info(f"=== TIPO DE DOCUMENTO DETECTADO: {tipo_detectado.upper()} ===")
        
        return tipo_detectado

    except Exception as e:
        logger.error("=== ERROR EN DETECCIÓN DE TIPO DE DOCUMENTO ===")
        logger.error(f"Tipo de error: {type(e).__name__}")
        logger.error(f"Mensaje de error: {str(e)}")
        logger.error(f"Detalles completos del error:", exc_info=True)
        logger.info("Usando tipo por defecto: factura")
        
        return "factura"  # Default en caso de error
   
