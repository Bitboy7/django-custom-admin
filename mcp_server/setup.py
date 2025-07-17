"""
Setup file for Gastos MCP Server
"""
from setuptools import setup, find_packages

setup(
    name="gastos_mcp_server",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "model-context-protocol>=0.1.0",
        "pymysql>=1.1.0",
        "python-dotenv>=1.0.0",
        "cryptography>=41.0.0",
        "pandas>=2.0.0",
        "matplotlib>=3.7.0",
        "numpy>=1.24.0"
    ],
    author="Admin",
    author_email="admin@example.com",
    description="A Model Context Protocol (MCP) server for analyzing expenses from MySQL database",
    keywords="mcp, mysql, expenses, analysis",
    entry_points={
        'console_scripts': [
            'gastos-mcp=gastos_mcp_server.server:main',
        ],
    },
)