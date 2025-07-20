"""
Script de prueba para verificar la configuración de la API de Google Gemini
"""
import os
import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

import django
django.setup()

from dotenv import load_dotenv
import google.generativeai as genai

def test_google_api():
    """Verificar la configuración de la API de Google"""
    print("=== VERIFICANDO CONFIGURACIÓN DE GOOGLE GEMINI API ===")
    
    # Cargar variables de entorno
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        print("❌ ERROR: GOOGLE_API_KEY no encontrada en variables de entorno")
        print("Asegúrate de:")
        print("1. Crear un archivo .env en la raíz del proyecto")
        print("2. Agregar la línea: GOOGLE_API_KEY=tu_clave_aqui")
        return False
    
    print(f"✅ API Key encontrada: {api_key[:10]}...")
    
    try:
        # Configurar la API
        genai.configure(api_key=api_key)
        
        # Probar una solicitud simple
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content("Hola, ¿cómo estás?")
        
        print("✅ Conexión exitosa con Google Gemini API")
        print(f"Respuesta de prueba: {response.text[:100]}...")
        return True
        
    except Exception as e:
        print(f"❌ ERROR al conectar con Google Gemini API: {str(e)}")
        print("Verifica que:")
        print("1. La API key sea válida")
        print("2. Tengas créditos disponibles en tu cuenta de Google AI")
        print("3. La API de Gemini esté habilitada")
        return False

def test_langchain_integration():
    """Verificar la integración con LangChain"""
    print("\n=== VERIFICANDO INTEGRACIÓN CON LANGCHAIN ===")
    
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.prompts import PromptTemplate
        from langchain_core.output_parsers import JsonOutputParser
        
        print("✅ Importaciones de LangChain exitosas")
        
        # Probar el modelo
        model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0)
        response = model.invoke("Di 'Hola mundo' en JSON con formato {'mensaje': 'tu_respuesta'}")
        
        print("✅ Modelo de LangChain funcional")
        print(f"Respuesta: {response.content[:100]}...")
        return True
        
    except Exception as e:
        print(f"❌ ERROR en integración con LangChain: {str(e)}")
        return False

def test_pdf_processing():
    """Verificar el procesamiento de PDFs"""
    print("\n=== VERIFICANDO PROCESAMIENTO DE PDFs ===")
    
    try:
        from langchain_community.document_loaders import PyPDFLoader
        print("✅ PyPDFLoader importado correctamente")
        
        # Verificar que pypdf esté instalado
        import pypdf
        print("✅ pypdf disponible")
        return True
        
    except Exception as e:
        print(f"❌ ERROR en procesamiento de PDFs: {str(e)}")
        print("Ejecuta: pip install pypdf")
        return False

def test_django_forms():
    """Verificar los formularios de Django"""
    print("\n=== VERIFICANDO FORMULARIOS DE DJANGO ===")
    
    try:
        from gastos.forms import FacturaUploadForm
        form = FacturaUploadForm()
        print("✅ FacturaUploadForm creado correctamente")
        print(f"Campos del formulario: {list(form.fields.keys())}")
        return True
        
    except Exception as e:
        print(f"❌ ERROR en formularios de Django: {str(e)}")
        return False

def main():
    """Ejecutar todas las pruebas"""
    print("🧪 INICIANDO PRUEBAS DEL SISTEMA DE RECONOCIMIENTO DE DOCUMENTOS")
    print("=" * 70)
    
    tests = [
        test_google_api,
        test_langchain_integration,
        test_pdf_processing,
        test_django_forms
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
    
    print("\n" + "=" * 70)
    print("📊 RESUMEN DE PRUEBAS:")
    
    if all(results):
        print("🎉 ¡TODAS LAS PRUEBAS PASARON! El sistema está listo para usar.")
    else:
        print("⚠️ Algunas pruebas fallaron. Revisa los errores arriba.")
        failed_tests = [i for i, result in enumerate(results) if not result]
        print(f"Pruebas fallidas: {failed_tests}")

if __name__ == "__main__":
    main()
