"""
Database interface for the Gastos MCP Server
"""
import pymysql
import pandas as pd
from typing import Dict, List, Any, Optional, Union
from .config import DB_CONFIG, logger

class DatabaseHandler:
    """Handles database connections and queries for Gastos MCP Server"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize database connection with config"""
        self.config = config or DB_CONFIG
        self.connection = None
    
    def connect(self) -> None:
        """Establish a connection to the MySQL database"""
        try:
            self.connection = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            logger.info(f"Connected to MySQL database at {self.config['host']}:{self.config['port']}")
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            raise
    
    def disconnect(self) -> None:
        """Close the database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
    
    def execute_query(self, query: str, params: Optional[Union[tuple, dict]] = None) -> List[Dict]:
        """Execute a SQL query and return results"""
        if not self.connection:
            self.connect()
        
        try:
            with self.connection.cursor() as cursor:
                logger.debug(f"Executing query: {query}")
                cursor.execute(query, params or ())
                results = cursor.fetchall()
                logger.debug(f"Query returned {len(results)} results")
                return results
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise
    
    def execute_to_dataframe(self, query: str, params: Optional[Union[tuple, dict]] = None) -> pd.DataFrame:
        """Execute a SQL query and return results as a pandas DataFrame"""
        results = self.execute_query(query, params)
        return pd.DataFrame(results) if results else pd.DataFrame()
    
    def list_tables(self) -> List[str]:
        """List all tables in the database"""
        results = self.execute_query("SHOW TABLES")
        return [list(table.values())[0] for table in results]
    
    def get_table_schema(self, table_name: str) -> List[Dict]:
        """Get schema information for a specific table"""
        return self.execute_query(f"DESCRIBE {table_name}")
    
    # Specific queries for the Gastos application
    def get_gastos(self, limit: int = 100) -> pd.DataFrame:
        """Get gastos (expenses) data with related information"""
        query = """
        SELECT 
            g.id, g.monto, g.descripcion, g.fecha, g.fecha_registro,
            s.nombre as sucursal,
            c.nombre as categoria,
            b.nombre as banco,
            cu.numero_cuenta
        FROM gastos_gastos g
        JOIN catalogo_sucursal s ON g.id_sucursal_id = s.id
        JOIN gastos_catgastos c ON g.id_cat_gastos_id = c.id
        JOIN gastos_cuenta cu ON g.id_cuenta_banco_id = cu.id
        JOIN gastos_banco b ON cu.id_banco_id = b.id
        ORDER BY g.fecha DESC
        LIMIT %s
        """
        return self.execute_to_dataframe(query, (limit,))
    
    def get_categoria_gastos(self) -> pd.DataFrame:
        """Get categories of expenses"""
        query = "SELECT id, nombre, fecha_registro FROM gastos_catgastos"
        return self.execute_to_dataframe(query)
    
    def get_bancos(self) -> pd.DataFrame:
        """Get banks information"""
        query = "SELECT id, nombre, telefono, direccion, fecha_registro FROM gastos_banco"
        return self.execute_to_dataframe(query)
    
    def get_cuentas(self) -> pd.DataFrame:
        """Get accounts information with related bank and branch"""
        query = """
        SELECT 
            c.id, c.numero_cuenta, c.numero_cliente, c.rfc, c.clabe, c.fecha_registro,
            b.nombre as banco,
            s.nombre as sucursal
        FROM gastos_cuenta c
        JOIN gastos_banco b ON c.id_banco_id = b.id
        JOIN catalogo_sucursal s ON c.id_sucursal_id = s.id
        """
        return self.execute_to_dataframe(query)
    
    def get_compras(self, limit: int = 100) -> pd.DataFrame:
        """Get purchases information"""
        query = """
        SELECT 
            c.id, c.fecha_compra, c.cantidad, c.precio_unitario, c.monto_total, 
            c.tipo_pago, c.fecha_registro,
            p.nombre as productor,
            pr.nombre as producto,
            cu.numero_cuenta,
            b.nombre as banco
        FROM gastos_compra c
        JOIN catalogo_productor p ON c.productor_id = p.id
        JOIN catalogo_producto pr ON c.producto_id = pr.id
        LEFT JOIN gastos_cuenta cu ON c.cuenta_id = cu.id
        LEFT JOIN gastos_banco b ON cu.id_banco_id = b.id
        ORDER BY c.fecha_compra DESC
        LIMIT %s
        """
        return self.execute_to_dataframe(query, (limit,))
    
    def get_saldos_mensuales(self) -> pd.DataFrame:
        """Get monthly balances"""
        query = """
        SELECT 
            sm.id, sm.año, sm.mes, sm.saldo_inicial, sm.saldo_final, 
            sm.fecha_registro, sm.ultima_modificacion,
            c.numero_cuenta,
            b.nombre as banco,
            s.nombre as sucursal
        FROM gastos_saldomensual sm
        JOIN gastos_cuenta c ON sm.cuenta_id = c.id
        JOIN gastos_banco b ON c.id_banco_id = b.id
        JOIN catalogo_sucursal s ON c.id_sucursal_id = s.id
        ORDER BY sm.año DESC, sm.mes DESC
        """
        return self.execute_to_dataframe(query)
    
    def analyze_gastos_por_categoria(self) -> pd.DataFrame:
        """Analyze expenses by category"""
        query = """
        SELECT 
            c.nombre as categoria,
            SUM(g.monto) as total_gastos,
            COUNT(g.id) as numero_gastos,
            AVG(g.monto) as promedio_gasto,
            MIN(g.monto) as minimo_gasto,
            MAX(g.monto) as maximo_gasto
        FROM gastos_gastos g
        JOIN gastos_catgastos c ON g.id_cat_gastos_id = c.id
        GROUP BY c.nombre
        ORDER BY total_gastos DESC
        """
        return self.execute_to_dataframe(query)
    
    def analyze_gastos_por_sucursal(self) -> pd.DataFrame:
        """Analyze expenses by branch"""
        query = """
        SELECT 
            s.nombre as sucursal,
            SUM(g.monto) as total_gastos,
            COUNT(g.id) as numero_gastos,
            AVG(g.monto) as promedio_gasto
        FROM gastos_gastos g
        JOIN catalogo_sucursal s ON g.id_sucursal_id = s.id
        GROUP BY s.nombre
        ORDER BY total_gastos DESC
        """
        return self.execute_to_dataframe(query)
    
    def analyze_gastos_por_fecha(self, periodo: str = 'mes') -> pd.DataFrame:
        """Analyze expenses by date (month or year)"""
        group_by = "YEAR(g.fecha)" if periodo == 'año' else "YEAR(g.fecha), MONTH(g.fecha)"
        date_format = "%Y" if periodo == 'año' else "%Y-%m"
        
        query = f"""
        SELECT 
            DATE_FORMAT(g.fecha, '{date_format}') as periodo,
            SUM(g.monto) as total_gastos,
            COUNT(g.id) as numero_gastos
        FROM gastos_gastos g
        GROUP BY {group_by}
        ORDER BY g.fecha DESC
        """
        return self.execute_to_dataframe(query)
    
    def analyze_compras_vs_gastos(self, periodo: str = 'mes', limit: int = 12) -> pd.DataFrame:
        """Compare purchases vs expenses over time"""
        group_by = "YEAR(fecha)" if periodo == 'año' else "YEAR(fecha), MONTH(fecha)"
        date_format = "%Y" if periodo == 'año' else "%Y-%m"
        
        # Gastos por periodo
        gastos_query = f"""
        SELECT 
            DATE_FORMAT(fecha, '{date_format}') as periodo,
            SUM(monto) as total_gastos
        FROM gastos_gastos
        GROUP BY {group_by}
        ORDER BY fecha DESC
        LIMIT {limit}
        """
        
        # Compras por periodo
        compras_query = f"""
        SELECT 
            DATE_FORMAT(fecha_compra, '{date_format}') as periodo,
            SUM(monto_total) as total_compras
        FROM gastos_compra
        GROUP BY {group_by}
        ORDER BY fecha_compra DESC
        LIMIT {limit}
        """
        
        gastos_df = self.execute_to_dataframe(gastos_query)
        compras_df = self.execute_to_dataframe(compras_query)
        
        # Merge dataframes
        result = pd.merge(gastos_df, compras_df, on='periodo', how='outer').fillna(0)
        result = result.sort_values('periodo', ascending=False)
        
        return result
    
    def execute_custom_query(self, query: str) -> pd.DataFrame:
        """Execute a custom SQL query with safety checks"""
        # Validate the query is SELECT only
        query = query.strip()
        if not query.lower().startswith('select'):
            raise ValueError("Only SELECT queries are allowed for security reasons")
        
        # Check for dangerous operations
        dangerous_keywords = ['drop', 'delete', 'insert', 'update', 'alter', 'create', 'truncate']
        if any(keyword in query.lower() for keyword in dangerous_keywords):
            raise ValueError("Query contains potentially dangerous operations")
        
        return self.execute_to_dataframe(query)