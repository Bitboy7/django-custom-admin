"""
Gastos MCP Server - Main implementation
"""
import json
import sys
import io
import base64
from typing import Dict, List, Any, Optional
from model_context_protocol import MCPServer, Action, Resource, Parameter
from model_context_protocol.schema import ParameterSchema, StringSchema, NumberSchema, BooleanSchema, EnumSchema
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import numpy as np

from .db import DatabaseHandler
from .config import RESOURCES, logger

class GastosMCPServer(MCPServer):
    """MCP Server for analyzing expenses from MySQL database"""
    
    def __init__(self):
        """Initialize the server with available resources and actions"""
        super().__init__(
            name="Gastos MCP Server",
            description="A Model Context Protocol server for analyzing expenses stored in a MySQL database",
            version="0.1.0"
        )
        
        # Initialize database handler
        self.db_handler = DatabaseHandler()
        
        # Register resources and actions
        self._register_resources()
    
    def _register_resources(self) -> None:
        """Register all available resources and their actions"""
        
        # Gastos (Expenses) resource
        self.register_resource(Resource(
            name="gastos",
            description="Expenses information from the database",
            actions=[
                Action(
                    name="list",
                    description="Get a list of recent expenses",
                    parameters=[
                        Parameter(name="limit", schema=NumberSchema(min=1, max=1000), description="Maximum number of expenses to return", required=False)
                    ],
                    handler=self.list_gastos
                ),
                Action(
                    name="analyze_by_category",
                    description="Analyze expenses grouped by category",
                    handler=self.analyze_gastos_por_categoria
                ),
                Action(
                    name="analyze_by_branch",
                    description="Analyze expenses grouped by branch (sucursal)",
                    handler=self.analyze_gastos_por_sucursal
                ),
                Action(
                    name="analyze_by_date",
                    description="Analyze expenses over time",
                    parameters=[
                        Parameter(
                            name="period", 
                            schema=EnumSchema(["mes", "año"]),
                            description="Group by month (mes) or year (año)",
                            required=False
                        )
                    ],
                    handler=self.analyze_gastos_por_fecha
                ),
                Action(
                    name="plot_by_category",
                    description="Generate a pie chart of expenses by category",
                    parameters=[
                        Parameter(name="top_n", schema=NumberSchema(min=1, max=20), description="Show only top N categories", required=False)
                    ],
                    handler=self.plot_gastos_por_categoria
                ),
                Action(
                    name="plot_over_time",
                    description="Generate a line chart of expenses over time",
                    parameters=[
                        Parameter(
                            name="period", 
                            schema=EnumSchema(["mes", "año"]),
                            description="Group by month (mes) or year (año)",
                            required=False
                        ),
                        Parameter(
                            name="limit", 
                            schema=NumberSchema(min=1, max=60),
                            description="Number of periods to include",
                            required=False
                        )
                    ],
                    handler=self.plot_gastos_over_time
                )
            ]
        ))
        
        # Categories resource
        self.register_resource(Resource(
            name="cat_gastos",
            description="Categories of expenses",
            actions=[
                Action(
                    name="list",
                    description="Get a list of expense categories",
                    handler=self.list_categorias
                )
            ]
        ))
        
        # Banks resource
        self.register_resource(Resource(
            name="bancos",
            description="Bank information",
            actions=[
                Action(
                    name="list",
                    description="Get a list of banks",
                    handler=self.list_bancos
                )
            ]
        ))
        
        # Accounts resource
        self.register_resource(Resource(
            name="cuentas",
            description="Bank accounts information",
            actions=[
                Action(
                    name="list",
                    description="Get a list of bank accounts",
                    handler=self.list_cuentas
                )
            ]
        ))
        
        # Purchases resource
        self.register_resource(Resource(
            name="compras",
            description="Purchases information",
            actions=[
                Action(
                    name="list",
                    description="Get a list of recent purchases",
                    parameters=[
                        Parameter(name="limit", schema=NumberSchema(min=1, max=1000), description="Maximum number of purchases to return", required=False)
                    ],
                    handler=self.list_compras
                )
            ]
        ))
        
        # Comparative Analysis resource
        self.register_resource(Resource(
            name="analisis_comparativo",
            description="Comparative analysis between different data",
            actions=[
                Action(
                    name="compras_vs_gastos",
                    description="Compare purchases vs expenses over time",
                    parameters=[
                        Parameter(
                            name="period", 
                            schema=EnumSchema(["mes", "año"]),
                            description="Group by month (mes) or year (año)",
                            required=False
                        ),
                        Parameter(
                            name="limit", 
                            schema=NumberSchema(min=1, max=60),
                            description="Number of periods to include",
                            required=False
                        )
                    ],
                    handler=self.compare_compras_gastos
                ),
                Action(
                    name="plot_compras_vs_gastos",
                    description="Generate a chart comparing purchases vs expenses over time",
                    parameters=[
                        Parameter(
                            name="period", 
                            schema=EnumSchema(["mes", "año"]),
                            description="Group by month (mes) or year (año)",
                            required=False
                        ),
                        Parameter(
                            name="limit", 
                            schema=NumberSchema(min=1, max=60),
                            description="Number of periods to include",
                            required=False
                        )
                    ],
                    handler=self.plot_compras_vs_gastos
                )
            ]
        ))
        
        # SQL Query resource - for advanced users
        self.register_resource(Resource(
            name="sql_query",
            description="Execute custom SQL queries (SELECT only)",
            actions=[
                Action(
                    name="execute",
                    description="Execute a custom SQL SELECT query",
                    parameters=[
                        Parameter(
                            name="query", 
                            schema=StringSchema(),
                            description="SQL SELECT query to execute (only SELECT statements allowed)",
                            required=True
                        )
                    ],
                    handler=self.execute_custom_query
                )
            ]
        ))
    
    # Handler methods for actions
    def list_gastos(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for listing expenses"""
        limit = params.get('limit', 100)
        with self.db_handler as db:
            df = db.get_gastos(limit=limit)
        
        if df.empty:
            return {"result": "No expenses found in the database."}
        
        return {
            "result": df.to_dict(orient='records'),
            "count": len(df)
        }
    
    def analyze_gastos_por_categoria(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for analyzing expenses by category"""
        with self.db_handler as db:
            df = db.analyze_gastos_por_categoria()
        
        if df.empty:
            return {"result": "No expense data found for analysis."}
        
        return {
            "result": df.to_dict(orient='records'),
            "count": len(df),
            "summary": f"Analysis of expenses across {len(df)} categories."
        }
    
    def analyze_gastos_por_sucursal(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for analyzing expenses by branch"""
        with self.db_handler as db:
            df = db.analyze_gastos_por_sucursal()
        
        if df.empty:
            return {"result": "No expense data found for analysis."}
        
        return {
            "result": df.to_dict(orient='records'),
            "count": len(df),
            "summary": f"Analysis of expenses across {len(df)} branches."
        }
    
    def analyze_gastos_por_fecha(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for analyzing expenses by date"""
        periodo = params.get('period', 'mes')
        with self.db_handler as db:
            df = db.analyze_gastos_por_fecha(periodo=periodo)
        
        if df.empty:
            return {"result": "No expense data found for analysis."}
        
        period_type = "months" if periodo == 'mes' else "years"
        return {
            "result": df.to_dict(orient='records'),
            "count": len(df),
            "summary": f"Analysis of expenses across {len(df)} {period_type}."
        }
    
    def plot_gastos_por_categoria(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for generating a pie chart of expenses by category"""
        top_n = params.get('top_n', 10)
        
        with self.db_handler as db:
            df = db.analyze_gastos_por_categoria()
        
        if df.empty:
            return {"error": "No expense data found for plotting."}
        
        # Keep only top N categories and group the rest as "Others"
        if len(df) > top_n:
            top_df = df.head(top_n)
            others = pd.DataFrame({
                'categoria': ['Otros'],
                'total_gastos': [df['total_gastos'][top_n:].sum()],
                'numero_gastos': [df['numero_gastos'][top_n:].sum()],
                'promedio_gasto': [df['total_gastos'][top_n:].sum() / df['numero_gastos'][top_n:].sum()]
            })
            df = pd.concat([top_df, others])
        
        # Create pie chart
        plt.figure(figsize=(10, 7))
        plt.pie(
            df['total_gastos'],
            labels=df['categoria'],
            autopct='%1.1f%%',
            startangle=90,
            shadow=True
        )
        plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
        plt.title('Gastos por Categoría')
        
        # Convert plot to base64 image
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
        
        return {
            "image": image_base64,
            "format": "png",
            "summary": f"Pie chart showing distribution of expenses across top {min(top_n, len(df))} categories."
        }
    
    def plot_gastos_over_time(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for generating a line chart of expenses over time"""
        periodo = params.get('period', 'mes')
        limit = params.get('limit', 12)
        
        with self.db_handler as db:
            df = db.analyze_gastos_por_fecha(periodo=periodo)
            
        if df.empty:
            return {"error": "No expense data found for plotting."}
        
        # Limit the number of periods
        df = df.head(limit)
        
        # Sort by period (ascending for the chart)
        df = df.sort_values('periodo')
        
        # Create line chart
        plt.figure(figsize=(12, 6))
        plt.plot(df['periodo'], df['total_gastos'], marker='o', linewidth=2)
        plt.grid(True, alpha=0.3)
        period_type = "Mes" if periodo == 'mes' else "Año"
        plt.title(f'Gastos Totales por {period_type}')
        plt.xlabel(period_type)
        plt.ylabel('Monto Total (MXN)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Convert plot to base64 image
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
        
        return {
            "image": image_base64,
            "format": "png",
            "summary": f"Line chart showing expenses over {len(df)} {periodo}s."
        }
    
    def list_categorias(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for listing expense categories"""
        with self.db_handler as db:
            df = db.get_categoria_gastos()
        
        if df.empty:
            return {"result": "No expense categories found in the database."}
        
        return {
            "result": df.to_dict(orient='records'),
            "count": len(df)
        }
    
    def list_bancos(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for listing banks"""
        with self.db_handler as db:
            df = db.get_bancos()
        
        if df.empty:
            return {"result": "No banks found in the database."}
        
        return {
            "result": df.to_dict(orient='records'),
            "count": len(df)
        }
    
    def list_cuentas(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for listing bank accounts"""
        with self.db_handler as db:
            df = db.get_cuentas()
        
        if df.empty:
            return {"result": "No bank accounts found in the database."}
        
        return {
            "result": df.to_dict(orient='records'),
            "count": len(df)
        }
    
    def list_compras(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for listing purchases"""
        limit = params.get('limit', 100)
        with self.db_handler as db:
            df = db.get_compras(limit=limit)
        
        if df.empty:
            return {"result": "No purchases found in the database."}
        
        return {
            "result": df.to_dict(orient='records'),
            "count": len(df)
        }
    
    def compare_compras_gastos(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for comparing purchases vs expenses"""
        periodo = params.get('period', 'mes')
        limit = params.get('limit', 12)
        
        with self.db_handler as db:
            df = db.analyze_compras_vs_gastos(periodo=periodo, limit=limit)
        
        if df.empty:
            return {"result": "No data found for comparison."}
        
        # Calculate net balance (purchases - expenses)
        df['balance_neto'] = df['total_compras'] - df['total_gastos']
        
        return {
            "result": df.to_dict(orient='records'),
            "count": len(df),
            "summary": f"Comparison of purchases vs expenses over {len(df)} {periodo}s."
        }
    
    def plot_compras_vs_gastos(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for generating a chart comparing purchases vs expenses"""
        periodo = params.get('period', 'mes')
        limit = params.get('limit', 12)
        
        with self.db_handler as db:
            df = db.analyze_compras_vs_gastos(periodo=periodo, limit=limit)
        
        if df.empty:
            return {"error": "No data found for plotting."}
        
        # Calculate net balance
        df['balance_neto'] = df['total_compras'] - df['total_gastos']
        
        # Sort by period (ascending for the chart)
        df = df.sort_values('periodo')
        
        # Create bar chart
        fig, ax = plt.subplots(figsize=(14, 7))
        
        x = np.arange(len(df))
        width = 0.35
        
        bar1 = ax.bar(x - width/2, df['total_compras'], width, label='Compras')
        bar2 = ax.bar(x + width/2, df['total_gastos'], width, label='Gastos')
        
        # Add net balance line
        ax2 = ax.twinx()
        ax2.plot(x, df['balance_neto'], 'r-', marker='o', label='Balance Neto')
        
        # Add some text for labels, title and axes
        period_type = "Mes" if periodo == 'mes' else "Año"
        ax.set_title(f'Compras vs Gastos por {period_type}')
        ax.set_xlabel(period_type)
        ax.set_ylabel('Monto (MXN)')
        ax2.set_ylabel('Balance Neto (MXN)', color='r')
        ax.set_xticks(x)
        ax.set_xticklabels(df['periodo'], rotation=45)
        
        # Add legends
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='best')
        
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # Convert plot to base64 image
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
        
        return {
            "image": image_base64,
            "format": "png",
            "summary": f"Bar chart comparing purchases vs expenses over {len(df)} {periodo}s with net balance line."
        }
    
    def execute_custom_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for executing a custom SQL query"""
        query = params.get('query', '')
        
        try:
            with self.db_handler as db:
                df = db.execute_custom_query(query)
            
            if df.empty:
                return {"result": "Query executed successfully but returned no data."}
            
            return {
                "result": df.to_dict(orient='records'),
                "count": len(df),
                "columns": df.columns.tolist()
            }
        except Exception as e:
            return {"error": f"Error executing query: {str(e)}"}

def main():
    """Main entry point for the MCP server"""
    server = GastosMCPServer()
    server.run()

if __name__ == "__main__":
    main()