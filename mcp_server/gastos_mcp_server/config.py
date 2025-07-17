"""
Configuration for the Gastos MCP Server
"""
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger('gastos_mcp')

# Load environment variables from .env file or parent Django project
load_dotenv()

# Database configuration - First try specific MCP env vars, then fall back to Django ones
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST') or os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT') or os.getenv('DB_PORT', 3306)),
    'user': os.getenv('MYSQL_USER') or os.getenv('DB_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD') or os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('MYSQL_DATABASE') or os.getenv('DB_NAME', 'django-custom-admin'),
}

# Available resources
RESOURCES = [
    'gastos',
    'cat_gastos',
    'bancos',
    'cuentas',
    'compras',
    'saldos_mensuales',
]