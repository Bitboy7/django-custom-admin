import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import lru_cache
TOTAL = re.compile(r'(?:TOTAL|IMPORTE\s+TOTAL)\s*[:$#]?\s*([\d,.]+)', re.I)
DATE = re.compile(r'\b(\d{2}[/-]\d{2}[/-]\d{2,4})\b')
RFC = re.compile(r'\b[A-Z&?]{3,4}\d{6}[A-Z\d]{3}\b', re.I)
@lru_cache(maxsize=1)
def engine():
    try:
        from paddleocr import PaddleOCR
    except ImportError as exc:
        raise RuntimeError('PaddleOCR no est? instalado en el worker OCR.') from exc
    return PaddleOCR(lang='es')
def read_receipt(path):
    ocr=engine(); result=ocr.predict(str(path)) if hasattr(ocr,'predict') else ocr.ocr(str(path),cls=True)
    return str(result)
def money(value):
    value=value.replace('$','').replace(',','')
    try:return str(Decimal(value).quantize(Decimal('0.01')))
    except InvalidOperation:return None
def extract_receipt_fields(text):
    lines=[x.strip() for x in text.splitlines() if x.strip()]
    total,date,rfc=TOTAL.search(text),DATE.search(text),RFC.search(text)
    parsed=None
    if date:
        for fmt in ('%d/%m/%Y','%d/%m/%y'):
            try:parsed=datetime.strptime(date.group(1).replace('-','/'),fmt).date().isoformat();break
            except ValueError:pass
    fields={'proveedor':lines[0][:120] if lines else '', 'fecha':parsed, 'total':money(total.group(1)) if total else None, 'rfc':rfc.group(0).upper() if rfc else '', 'descripcion':' | '.join(lines[:4])[:500]}
    fields['confianza']=str(Decimal(sum(bool(fields[k]) for k in ('proveedor','fecha','total'))*100/3).quantize(Decimal('0.01')))
    return fields
