#!/usr/bin/env python3
"""
Simple Python script to compile .po files to .mo files
This is a basic implementation for development purposes
"""
import os
import struct
from pathlib import Path

def compile_po_to_mo(po_file, mo_file):
    """
    Compile a .po file to .mo file
    Simple implementation that handles basic msgid/msgstr pairs
    """
    entries = {}
    current_msgid = None
    current_msgstr = None
    in_msgid = False
    in_msgstr = False
    
    with open(po_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            
            # Skip comments and empty lines
            if line.startswith('#') or not line:
                continue
                
            if line.startswith('msgid '):
                if current_msgid is not None and current_msgstr is not None:
                    entries[current_msgid] = current_msgstr
                current_msgid = line[6:].strip('"')
                current_msgstr = None
                in_msgid = True
                in_msgstr = False
                
            elif line.startswith('msgstr '):
                current_msgstr = line[7:].strip('"')
                in_msgid = False
                in_msgstr = True
                
            elif line.startswith('"') and in_msgid:
                current_msgid += line.strip('"')
                
            elif line.startswith('"') and in_msgstr:
                current_msgstr += line.strip('"')
                
    # Add the last entry
    if current_msgid is not None and current_msgstr is not None:
        entries[current_msgid] = current_msgstr
    
    # Remove empty msgid (header)
    if '' in entries:
        del entries['']
    
    # Create .mo file content
    keys = list(entries.keys())
    values = list(entries.values())
    
    # Encode strings
    kencoded = [k.encode('utf-8') for k in keys]
    vencoded = [v.encode('utf-8') for v in values]
    
    keystart = 7 * 4 + 16 * len(keys)
    valuestart = keystart + sum(len(k) for k in kencoded)
    
    # Generate binary data
    output = []
    output.append(struct.pack('<I', 0x950412de))  # Magic number
    output.append(struct.pack('<I', 0))  # Version
    output.append(struct.pack('<I', len(keys)))  # Number of entries
    output.append(struct.pack('<I', 7 * 4))  # Key table offset
    output.append(struct.pack('<I', 7 * 4 + len(keys) * 8))  # Value table offset
    output.append(struct.pack('<I', 0))  # Hash table size
    output.append(struct.pack('<I', 0))  # Hash table offset
    
    # Add key table
    keyoffset = keystart
    for k in kencoded:
        output.append(struct.pack('<I', len(k)))
        output.append(struct.pack('<I', keyoffset))
        keyoffset += len(k)
    
    # Add value table
    valueoffset = valuestart
    for v in vencoded:
        output.append(struct.pack('<I', len(v)))
        output.append(struct.pack('<I', valueoffset))
        valueoffset += len(v)
    
    # Add keys
    for k in kencoded:
        output.append(k)
    
    # Add values
    for v in vencoded:
        output.append(v)
    
    # Write to file
    os.makedirs(os.path.dirname(mo_file), exist_ok=True)
    with open(mo_file, 'wb') as f:
        f.write(b''.join(output))
    
    print(f"Compiled {po_file} -> {mo_file}")

if __name__ == "__main__":
    # Find all .po files and compile them
    locale_dir = Path("locale")
    
    for po_file in locale_dir.glob("*/LC_MESSAGES/django.po"):
        mo_file = po_file.with_suffix('.mo')
        compile_po_to_mo(str(po_file), str(mo_file))
    
    print("All .po files compiled successfully!")
