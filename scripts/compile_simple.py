import os
import struct

def compile_po_file(po_file, mo_file):
    """Compila un archivo .po simple a .mo"""
    translations = {}
    
    # Leer archivo .po
    with open(po_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parsear contenido básico
    lines = content.split('\n')
    msgid = None
    msgstr = None
    
    for line in lines:
        line = line.strip()
        if line.startswith('msgid '):
            msgid = line[6:].strip('"')
        elif line.startswith('msgstr '):
            msgstr = line[7:].strip('"')
            if msgid and msgstr and msgid != '' and msgstr != '':
                translations[msgid] = msgstr
            msgid = None
            msgstr = None
    
    # Crear archivo .mo básico
    if translations:
        # Codificar cadenas
        items = sorted(translations.items())
        keys = [k.encode('utf-8') for k, v in items]
        values = [v.encode('utf-8') for k, v in items]
        
        # Crear contenido binario simple
        output = bytearray()
        
        # Magic number
        output.extend(struct.pack('<I', 0x950412de))
        # Version
        output.extend(struct.pack('<I', 0))
        # Number of entries
        output.extend(struct.pack('<I', len(keys)))
        # Offsets (simplificados)
        output.extend(struct.pack('<I', 28))
        output.extend(struct.pack('<I', 28 + len(keys) * 8))
        output.extend(struct.pack('<I', 0))
        output.extend(struct.pack('<I', 0))
        
        # Tablas de longitud y offset
        offset = 28 + len(keys) * 16
        for key in keys:
            output.extend(struct.pack('<I', len(key)))
            output.extend(struct.pack('<I', offset))
            offset += len(key) + 1
            
        for value in values:
            output.extend(struct.pack('<I', len(value)))
            output.extend(struct.pack('<I', offset))
            offset += len(value) + 1
        
        # Strings
        for key in keys:
            output.extend(key)
            output.extend(b'\x00')
        for value in values:
            output.extend(value)
            output.extend(b'\x00')
        
        # Escribir archivo
        with open(mo_file, 'wb') as f:
            f.write(output)
        
        print(f"Archivo .mo creado: {mo_file}")
    else:
        print("No se encontraron traducciones válidas")

if __name__ == "__main__":
    po_file = "locale/es/LC_MESSAGES/django.po"
    mo_file = "locale/es/LC_MESSAGES/django.mo"
    
    if os.path.exists(po_file):
        compile_po_file(po_file, mo_file)
    else:
        print(f"No se encontró el archivo: {po_file}")
