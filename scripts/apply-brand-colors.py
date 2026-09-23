#!/usr/bin/env python3
"""
Script para propagar la paleta oficial de Agrícola de la Costa
a todos los archivos HTML, CSS y JS del ERP.

Colores oficiales:
  --shadow-grey: #2d232e
  --gunmetal:    #474448
  --taupe-grey:  #534b52
  --bone:        #e0ddcf
  --parchment:   #f1f0ea
"""

import os
import re
from pathlib import Path

BASE_DIR = Path(r"C:\Users\dev-y\Documents\django-custom-admin")

# Extensiones a procesar
EXTENSIONS = {".html", ".css", ".js", ".py"}

# Carpetas a excluir
EXCLUDE_DIRS = {
    ".git", "__pycache__", "venv", "node_modules", ".pytest_cache",
    "migrations", "media", "staticfiles", ".agents", "static-only", "CACHE",
    "import_export", "jazzmin", "vendor", "unfold", "django_extensions"
}

# Reemplazos de colores hex exactos
HEX_REPLACEMENTS = {
    # Navy/azul antiguo → shadow-grey
    "#1e3a8a": "#2d232e",
    "#1e40af": "#474448",
    "#1d4ed8": "#474448",
    "#2563eb": "#474448",
    "#3b82f6": "#474448",
    "#0d2a47": "#2d232e",
    "#1e3a5f": "#2d232e",
    "#0a6473": "#2d232e",
    "#0c4a6e": "#2d232e",
    "#0e7490": "#474448",
    "#0891b2": "#474448",
    "#06b6d4": "#474448",
    "#22d3ee": "#e0ddcf",
    "#67e8f9": "#e0ddcf",
    "#164e63": "#2d232e",
    "#155e75": "#2d232e",
    "#0e4f5e": "#2d232e",
    
    # Teal/turquesa antiguo → bone
    "#0d8fa2": "#e0ddcf",
    "#08b5ab": "#e0ddcf",
    "#1aadbc": "#e0ddcf",
    "#14b8a6": "#e0ddcf",
    "#10b981": "#534b52",
    "#7de8f0": "#e0ddcf",
    "#0d9488": "#e0ddcf",
    "#0f766e": "#2d232e",
    "#115e59": "#2d232e",
    "#134e4a": "#2d232e",
    
    # Verde esmeralda antiguo → verde terroso
    "#16a34a": "#534b52",
    "#22c55e": "#534b52",
    "#15803d": "#2d232e",
    "#166534": "#2d232e",
    "#14532d": "#2d232e",
    "#10b981": "#534b52",
    "#059669": "#534b52",
    "#047857": "#534b52",
    "#065f46": "#534b52",
    "#064e3b": "#2d232e",
    
    # Rojo antiguo → rojo terracota
    "#dc2626": "#b85450",
    "#ef4444": "#b85450",
    "#b91c1c": "#b85450",
    "#991b1b": "#b85450",
    "#7f1d1d": "#8b4545",
    "#fca5a5": "#e8b4b0",
    "#fecaca": "#e8b4b0",
    "#fee2e2": "rgba(184,84,80,.1)",
    "#f87171": "#e8b4b0",
    
    # Ámbar/amarillo → ocre dorado
    "#d97706": "#c9a227",
    "#c2780a": "#c9a227",
    "#f59e0b": "#c9a227",
    "#b45309": "#c9a227",
    "#92400e": "#c9a227",
    "#78350f": "#c9a227",
    "#fde68a": "rgba(201,162,39,.15)",
    "#fef3c7": "rgba(201,162,39,.08)",
    
    # Grises y neutros antiguos
    "#8a9bb0": "#474448",
    "#b0bec5": "#e0ddcf",
    "#dde3ec": "#e0ddcf",
    "#1a2332": "#2d232e",
    "#f2f4f7": "#f1f0ea",
    "#e5e9f0": "#f1f0ea",
    "#f0f4f8": "#f1f0ea",
    "#e2e8f0": "#e0ddcf",
    "#cbd5e1": "#e0ddcf",
    "#94a3b8": "#474448",
    "#64748b": "#474448",
    "#475569": "#474448",
    "#334155": "#2d232e",
    "#1e293b": "#2d232e",
    "#0f172a": "#2d232e",
    "#374151": "#474448",
    "#4b5563": "#474448",
    "#6b7280": "#474448",
    "#9ca3af": "#e0ddcf",
    "#d1d5db": "#e0ddcf",
    "#e5e7eb": "#e0ddcf",
    "#f3f4f6": "#f1f0ea",
    "#f9fafb": "#f1f0ea",
    "#e0e7ff": "rgba(224,221,207,.15)",
    "#c7d2fe": "rgba(224,221,207,.2)",
    "#a5b4fc": "rgba(224,221,207,.3)",
    "#818cf8": "#e0ddcf",
    "#6366f1": "#474448",
    "#4f46e5": "#474448",
    "#4338ca": "#2d232e",
    "#3730a3": "#2d232e",
    "#312e81": "#2d232e",
    
    # Fondos de color pastel
    "#bfdbfe": "rgba(224,221,207,.3)",
    "#dcfce7": "rgba(224,221,207,.2)",
    "#dbeafe": "rgba(224,221,207,.15)",
    "#eff6ff": "rgba(224,221,207,.1)",
    "#ede9fe": "rgba(45,35,46,.05)",
    "#b2e4ec": "#e0ddcf",
    "#bae6fd": "rgba(224,221,207,.3)",
    "#cffafe": "rgba(224,221,207,.15)",
    "#ccfbf1": "rgba(224,221,207,.1)",
    "#d1fae5": "rgba(224,221,207,.1)",
    
    # Específicos del dashboard antiguo
    "#c4f0f5": "rgba(224,221,207,.3)",
    "#2d5282": "#474448",
    "#3b8ea5": "#474448",
    "#4a9eff": "#474448",
    "#0f4c75": "#2d232e",
    "#3282b8": "#474448",
    "#bbe1fa": "rgba(224,221,207,.3)",
    "#1b262c": "#2d232e",
    "#0f4c5c": "#2d232e",
    "#5f0a87": "#2d232e",
    "#a4508b": "#474448",
}

# Reemplazos de clases Tailwind
TAILWIND_REPLACEMENTS = {
    # Backgrounds
    r'\bbg-blue-50\b': 'bg-[rgba(224,221,207,.15)]',
    r'\bbg-blue-100\b': 'bg-[rgba(224,221,207,.2)]',
    r'\bbg-blue-200\b': 'bg-[rgba(224,221,207,.3)]',
    r'\bbg-blue-500\b': 'bg-[#474448]',
    r'\bbg-blue-600\b': 'bg-[#2d232e]',
    r'\bbg-blue-700\b': 'bg-[#2d232e]',
    r'\bbg-blue-800\b': 'bg-[#2d232e]',
    r'\bbg-blue-900\b': 'bg-[#2d232e]',
    r'\bbg-emerald-50\b': 'bg-[rgba(224,221,207,.1)]',
    r'\bbg-emerald-100\b': 'bg-[rgba(224,221,207,.15)]',
    r'\bbg-emerald-200\b': 'bg-[rgba(224,221,207,.3)]',
    r'\bbg-emerald-500\b': 'bg-[#534b52]',
    r'\bbg-emerald-600\b': 'bg-[#534b52]',
    r'\bbg-emerald-700\b': 'bg-[#534b52]',
    r'\bbg-green-50\b': 'bg-[rgba(224,221,207,.1)]',
    r'\bbg-green-100\b': 'bg-[rgba(224,221,207,.15)]',
    r'\bbg-green-200\b': 'bg-[rgba(224,221,207,.3)]',
    r'\bbg-green-500\b': 'bg-[#534b52]',
    r'\bbg-green-600\b': 'bg-[#534b52]',
    r'\bbg-green-700\b': 'bg-[#534b52]',
    r'\bbg-red-50\b': 'bg-[rgba(184,84,80,.1)]',
    r'\bbg-red-100\b': 'bg-[rgba(184,84,80,.15)]',
    r'\bbg-red-200\b': 'bg-[rgba(184,84,80,.3)]',
    r'\bbg-red-500\b': 'bg-[#b85450]',
    r'\bbg-red-600\b': 'bg-[#b85450]',
    r'\bbg-red-700\b': 'bg-[#b85450]',
    r'\bbg-amber-50\b': 'bg-[rgba(201,162,39,.08)]',
    r'\bbg-amber-100\b': 'bg-[rgba(201,162,39,.15)]',
    r'\bbg-amber-200\b': 'bg-[rgba(201,162,39,.3)]',
    r'\bbg-amber-500\b': 'bg-[#c9a227]',
    r'\bbg-amber-600\b': 'bg-[#c9a227]',
    r'\bbg-amber-700\b': 'bg-[#c9a227]',
    r'\bbg-slate-50\b': 'bg-[#f1f0ea]',
    r'\bbg-slate-100\b': 'bg-[#f1f0ea]',
    r'\bbg-slate-200\b': 'bg-[#e0ddcf]',
    r'\bbg-slate-300\b': 'bg-[#e0ddcf]',
    r'\bbg-slate-500\b': 'bg-[#474448]',
    r'\bbg-slate-600\b': 'bg-[#2d232e]',
    r'\bbg-slate-700\b': 'bg-[#2d232e]',
    r'\bbg-slate-800\b': 'bg-[#2d232e]',
    r'\bbg-slate-900\b': 'bg-[#2d232e]',
    r'\bbg-gray-50\b': 'bg-[#f1f0ea]',
    r'\bbg-gray-100\b': 'bg-[#f1f0ea]',
    r'\bbg-gray-200\b': 'bg-[#e0ddcf]',
    r'\bbg-gray-300\b': 'bg-[#e0ddcf]',
    r'\bbg-gray-500\b': 'bg-[#474448]',
    r'\bbg-gray-600\b': 'bg-[#474448]',
    r'\bbg-gray-700\b': 'bg-[#2d232e]',
    r'\bbg-gray-800\b': 'bg-[#2d232e]',
    r'\bbg-gray-900\b': 'bg-[#2d232e]',
    r'\bbg-indigo-50\b': 'bg-[rgba(45,35,46,.05)]',
    r'\bbg-indigo-100\b': 'bg-[rgba(224,221,207,.15)]',
    r'\bbg-indigo-500\b': 'bg-[#474448]',
    r'\bbg-indigo-600\b': 'bg-[#2d232e]',
    r'\bbg-indigo-700\b': 'bg-[#2d232e]',
    r'\bbg-indigo-800\b': 'bg-[#2d232e]',
    r'\bbg-indigo-900\b': 'bg-[#2d232e]',
    r'\bbg-cyan-50\b': 'bg-[rgba(224,221,207,.1)]',
    r'\bbg-cyan-100\b': 'bg-[rgba(224,221,207,.15)]',
    r'\bbg-cyan-200\b': 'bg-[rgba(224,221,207,.3)]',
    r'\bbg-cyan-500\b': 'bg-[#474448]',
    r'\bbg-cyan-600\b': 'bg-[#2d232e]',
    r'\bbg-cyan-700\b': 'bg-[#2d232e]',
    r'\bbg-cyan-800\b': 'bg-[#2d232e]',
    r'\bbg-cyan-900\b': 'bg-[#2d232e]',
    r'\bbg-teal-50\b': 'bg-[rgba(224,221,207,.1)]',
    r'\bbg-teal-100\b': 'bg-[rgba(224,221,207,.15)]',
    r'\bbg-teal-200\b': 'bg-[rgba(224,221,207,.3)]',
    r'\bbg-teal-500\b': 'bg-[#474448]',
    r'\bbg-teal-600\b': 'bg-[#2d232e]',
    r'\bbg-teal-700\b': 'bg-[#2d232e]',
    r'\bbg-teal-800\b': 'bg-[#2d232e]',
    r'\bbg-teal-900\b': 'bg-[#2d232e]',
    r'\bbg-white\b': 'bg-[#f1f0ea]',
    
    # Text colors
    r'\btext-blue-500\b': 'text-[#474448]',
    r'\btext-blue-600\b': 'text-[#2d232e]',
    r'\btext-blue-700\b': 'text-[#2d232e]',
    r'\btext-blue-800\b': 'text-[#2d232e]',
    r'\btext-blue-900\b': 'text-[#2d232e]',
    r'\btext-emerald-500\b': 'text-[#534b52]',
    r'\btext-emerald-600\b': 'text-[#534b52]',
    r'\btext-emerald-700\b': 'text-[#534b52]',
    r'\btext-emerald-800\b': 'text-[#534b52]',
    r'\btext-green-500\b': 'text-[#534b52]',
    r'\btext-green-600\b': 'text-[#534b52]',
    r'\btext-green-700\b': 'text-[#534b52]',
    r'\btext-green-800\b': 'text-[#534b52]',
    r'\btext-red-500\b': 'text-[#b85450]',
    r'\btext-red-600\b': 'text-[#b85450]',
    r'\btext-red-700\b': 'text-[#b85450]',
    r'\btext-red-800\b': 'text-[#b85450]',
    r'\btext-amber-500\b': 'text-[#c9a227]',
    r'\btext-amber-600\b': 'text-[#c9a227]',
    r'\btext-amber-700\b': 'text-[#c9a227]',
    r'\btext-amber-800\b': 'text-[#c9a227]',
    r'\btext-gray-300\b': 'text-[#e0ddcf]',
    r'\btext-gray-400\b': 'text-[#e0ddcf]',
    r'\btext-gray-500\b': 'text-[#474448]',
    r'\btext-gray-600\b': 'text-[#474448]',
    r'\btext-gray-700\b': 'text-[#474448]',
    r'\btext-gray-800\b': 'text-[#2d232e]',
    r'\btext-gray-900\b': 'text-[#2d232e]',
    r'\btext-slate-500\b': 'text-[#474448]',
    r'\btext-slate-600\b': 'text-[#474448]',
    r'\btext-slate-700\b': 'text-[#474448]',
    r'\btext-slate-800\b': 'text-[#2d232e]',
    r'\btext-slate-900\b': 'text-[#2d232e]',
    r'\btext-indigo-500\b': 'text-[#474448]',
    r'\btext-indigo-600\b': 'text-[#2d232e]',
    r'\btext-indigo-700\b': 'text-[#2d232e]',
    r'\btext-indigo-800\b': 'text-[#2d232e]',
    r'\btext-indigo-900\b': 'text-[#2d232e]',
    r'\btext-cyan-500\b': 'text-[#474448]',
    r'\btext-cyan-600\b': 'text-[#2d232e]',
    r'\btext-cyan-700\b': 'text-[#2d232e]',
    r'\btext-cyan-800\b': 'text-[#2d232e]',
    r'\btext-teal-500\b': 'text-[#474448]',
    r'\btext-teal-600\b': 'text-[#2d232e]',
    r'\btext-teal-700\b': 'text-[#2d232e]',
    r'\btext-teal-800\b': 'text-[#2d232e]',
    r'\btext-white\b': 'text-[#f1f0ea]',
    
    # Borders
    r'\bborder-blue-200\b': 'border-[rgba(224,221,207,.3)]',
    r'\bborder-blue-300\b': 'border-[#e0ddcf]',
    r'\bborder-blue-500\b': 'border-[#474448]',
    r'\bborder-blue-600\b': 'border-[#2d232e]',
    r'\bborder-emerald-200\b': 'border-[rgba(224,221,207,.3)]',
    r'\bborder-emerald-300\b': 'border-[#e0ddcf]',
    r'\bborder-green-200\b': 'border-[rgba(224,221,207,.3)]',
    r'\bborder-green-300\b': 'border-[#e0ddcf]',
    r'\bborder-red-200\b': 'border-[rgba(184,84,80,.3)]',
    r'\bborder-red-300\b': 'border-[#e8b4b0]',
    r'\bborder-amber-200\b': 'border-[rgba(201,162,39,.3)]',
    r'\bborder-amber-300\b': 'border-[#c9a227]',
    r'\bborder-gray-200\b': 'border-[#e0ddcf]',
    r'\bborder-gray-300\b': 'border-[#e0ddcf]',
    r'\bborder-slate-200\b': 'border-[#e0ddcf]',
    r'\bborder-slate-300\b': 'border-[#e0ddcf]',
    r'\bborder-indigo-200\b': 'border-[rgba(224,221,207,.3)]',
    r'\bborder-indigo-300\b': 'border-[#e0ddcf]',
    r'\bborder-cyan-200\b': 'border-[rgba(224,221,207,.3)]',
    r'\bborder-cyan-300\b': 'border-[#e0ddcf]',
    r'\bborder-teal-200\b': 'border-[rgba(224,221,207,.3)]',
    r'\bborder-teal-300\b': 'border-[#e0ddcf]',
    
    # Hover states backgrounds
    r'\bhover:bg-blue-700\b': 'hover:bg-[#474448]',
    r'\bhover:bg-blue-800\b': 'hover:bg-[#474448]',
    r'\bhover:bg-emerald-700\b': 'hover:bg-[#474448]',
    r'\bhover:bg-emerald-800\b': 'hover:bg-[#474448]',
    r'\bhover:bg-green-700\b': 'hover:bg-[#474448]',
    r'\bhover:bg-green-800\b': 'hover:bg-[#474448]',
    r'\bhover:bg-red-700\b': 'hover:bg-[#8b4545]',
    r'\bhover:bg-red-800\b': 'hover:bg-[#8b4545]',
    r'\bhover:bg-gray-50\b': 'hover:bg-[rgba(224,221,207,.1)]',
    r'\bhover:bg-gray-100\b': 'hover:bg-[rgba(224,221,207,.1)]',
    r'\bhover:bg-slate-50\b': 'hover:bg-[rgba(224,221,207,.1)]',
    r'\bhover:bg-slate-100\b': 'hover:bg-[rgba(224,221,207,.1)]',
    
    # Hover states text
    r'\bhover:text-blue-500\b': 'hover:text-[#e0ddcf]',
    r'\bhover:text-blue-700\b': 'hover:text-[#474448]',
    r'\bhover:text-blue-800\b': 'hover:text-[#474448]',
    r'\bhover:text-emerald-700\b': 'hover:text-[#474448]',
    r'\bhover:text-gray-700\b': 'hover:text-[#474448]',
    r'\bhover:text-gray-900\b': 'hover:text-[#2d232e]',
    r'\bhover:text-slate-700\b': 'hover:text-[#474448]',
    r'\bhover:text-slate-900\b': 'hover:text-[#2d232e]',
    r'\bhover:text-indigo-700\b': 'hover:text-[#474448]',
    r'\bhover:text-indigo-900\b': 'hover:text-[#2d232e]',
    
    # Focus states
    r'\bfocus:ring-blue-500\b': 'focus:ring-[#e0ddcf]',
    r'\bfocus:ring-emerald-500\b': 'focus:ring-[#e0ddcf]',
    r'\bfocus:ring-green-500\b': 'focus:ring-[#e0ddcf]',
    r'\bfocus:ring-red-500\b': 'focus:ring-[#b85450]',
    r'\bfocus:ring-indigo-500\b': 'focus:ring-[#e0ddcf]',
    r'\bfocus:ring-cyan-500\b': 'focus:ring-[#e0ddcf]',
    r'\bfocus:ring-teal-500\b': 'focus:ring-[#e0ddcf]',
    r'\bfocus:border-blue-500\b': 'focus:border-[#e0ddcf]',
    r'\bfocus:border-emerald-500\b': 'focus:border-[#e0ddcf]',
    r'\bfocus:border-green-500\b': 'focus:border-[#e0ddcf]',
    r'\bfocus:border-indigo-500\b': 'focus:border-[#e0ddcf]',
    r'\bfocus:border-cyan-500\b': 'focus:border-[#e0ddcf]',
    r'\bfocus:border-teal-500\b': 'focus:border-[#e0ddcf]',
    
    # Gradients (Tailwind)
    r'\bfrom-blue-600\b': 'from-[#2d232e]',
    r'\bfrom-blue-700\b': 'from-[#2d232e]',
    r'\bfrom-blue-800\b': 'from-[#2d232e]',
    r'\bfrom-blue-900\b': 'from-[#2d232e]',
    r'\bto-blue-700\b': 'to-[#2d232e]',
    r'\bto-blue-800\b': 'to-[#474448]',
    r'\bto-blue-600\b': 'to-[#474448]',
    r'\bfrom-emerald-600\b': 'from-[#2d232e]',
    r'\bfrom-emerald-700\b': 'from-[#2d232e]',
    r'\bto-emerald-700\b': 'to-[#2d232e]',
    r'\bto-emerald-800\b': 'to-[#474448]',
    r'\bfrom-green-600\b': 'from-[#2d232e]',
    r'\bfrom-green-700\b': 'from-[#2d232e]',
    r'\bto-green-700\b': 'to-[#2d232e]',
    r'\bto-green-800\b': 'to-[#474448]',
    r'\bfrom-red-600\b': 'from-[#b85450]',
    r'\bto-red-500\b': 'to-[#8b4545]',
    r'\bfrom-amber-600\b': 'from-[#c9a227]',
    r'\bto-amber-700\b': 'to-[#c9a227]',
    r'\bfrom-indigo-600\b': 'from-[#2d232e]',
    r'\bfrom-indigo-700\b': 'from-[#2d232e]',
    r'\bto-indigo-700\b': 'to-[#2d232e]',
    r'\bto-indigo-800\b': 'to-[#474448]',
    r'\bfrom-cyan-600\b': 'from-[#2d232e]',
    r'\bfrom-cyan-700\b': 'from-[#2d232e]',
    r'\bto-cyan-700\b': 'to-[#2d232e]',
    r'\bto-cyan-800\b': 'to-[#474448]',
    r'\bfrom-teal-600\b': 'from-[#2d232e]',
    r'\bfrom-teal-700\b': 'from-[#2d232e]',
    r'\bto-teal-700\b': 'to-[#2d232e]',
    r'\bto-teal-800\b': 'to-[#474448]',
    
    # Ring
    r'\bring-blue-500\b': 'ring-[#e0ddcf]',
    r'\bring-emerald-500\b': 'ring-[#e0ddcf]',
    r'\bring-green-500\b': 'ring-[#e0ddcf]',
    r'\bring-red-500\b': 'ring-[#b85450]',
    r'\bring-indigo-500\b': 'ring-[#e0ddcf]',
    r'\bring-cyan-500\b': 'ring-[#e0ddcf]',
    r'\bring-teal-500\b': 'ring-[#e0ddcf]',
}

# Compilar regexes
tailwind_patterns = {re.compile(k): v for k, v in TAILWIND_REPLACEMENTS.items()}


def should_process(path: Path) -> bool:
    """Determinar si un archivo debe ser procesado."""
    if path.suffix.lower() not in EXTENSIONS:
        return False
    if path.name == "apply-brand-colors.py":
        return False
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return False
    return True


def replace_in_content(content: str) -> tuple[str, int]:
    """Aplicar reemplazos a contenido de archivo."""
    count = 0
    
    # 1. Reemplazos hex exactos (case-insensitive)
    for old, new in HEX_REPLACEMENTS.items():
        pattern = re.compile(re.escape(old), re.IGNORECASE)
        matches = len(pattern.findall(content))
        if matches:
            content = pattern.sub(new, content)
            count += matches
    
    # 2. Reemplazos Tailwind
    for pattern, replacement in tailwind_patterns.items():
        matches = len(pattern.findall(content))
        if matches:
            content = pattern.sub(replacement, content)
            count += matches
    
    return content, count


def main():
    files_processed = 0
    files_changed = 0
    total_replacements = 0
    
    for root, dirs, files in os.walk(BASE_DIR):
        # Filtrar directorios excluidos
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for filename in files:
            filepath = Path(root) / filename
            if not should_process(filepath):
                continue
            
            files_processed += 1
            
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except (UnicodeDecodeError, IOError):
                continue
            
            new_content, replacements = replace_in_content(content)
            
            if replacements > 0:
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    files_changed += 1
                    total_replacements += replacements
                    print(f"  [{replacements:3d}] {filepath.relative_to(BASE_DIR)}")
                except IOError as e:
                    print(f"  ERROR escribiendo {filepath}: {e}")
    
    print(f"\n{'='*60}")
    print(f"Archivos procesados: {files_processed}")
    print(f"Archivos modificados: {files_changed}")
    print(f"Total reemplazos: {total_replacements}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

