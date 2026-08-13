import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import lru_cache

os.environ.setdefault('PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK', 'True')
TOTAL = re.compile(r'(?:TOTAL|IMPORTE\s+TOTAL|PRECIO)\s*[:$#]?\s*([\d,.]+)', re.I)
DATE = re.compile(r'\b(\d{4}[/-]\d{2}[/-]\d{2}|\d{2}[/-]\d{2}[/-]\d{2,4})\b')
RFC = re.compile(r'\b[A-Z&?]{3,4}\d{6}[A-Z\d]{3}\b', re.I)
@lru_cache(maxsize=1)
def engine():
    try:
        from paddleocr import PaddleOCR
    except ImportError as exc:
        raise RuntimeError('PaddleOCR no est? instalado en el worker OCR.') from exc
    return PaddleOCR(
        device='cpu', cpu_threads=2, enable_mkldnn=False,
        use_doc_orientation_classify=False, use_doc_unwarping=False,
        use_textline_orientation=False,
        text_detection_model_name='PP-OCRv5_mobile_det',
        text_recognition_model_name='latin_PP-OCRv5_mobile_rec',
    )
def read_receipt(path):
    ocr = engine()
    if hasattr(ocr, 'predict'):
        lines = []
        for result in ocr.predict(str(path)):
            # PaddleOCR 3.x returns a dict-like OCRResult.
            lines.extend(text for text in result.get('rec_texts', []) if text)
        return '\n'.join(lines)

    result = ocr.ocr(str(path), cls=True)
    return '\n'.join(item[1][0] for page in result for item in (page or []))
def money(value):
    value=value.replace('$','').replace(',','')
    try:return str(Decimal(value).quantize(Decimal('0.01')))
    except InvalidOperation:return None
def extract_receipt_fields(text):
    lines=[x.strip() for x in text.splitlines() if x.strip()]
    total,date,rfc=TOTAL.search(text),DATE.search(text),RFC.search(text)
    parsed=None
    if date:
        for fmt in ('%Y/%m/%d','%d/%m/%Y','%d/%m/%y'):
            try:parsed=datetime.strptime(date.group(1).replace('-','/'),fmt).date().isoformat();break
            except ValueError:pass
    fields={'proveedor':lines[0][:120] if lines else '', 'fecha':parsed, 'total':money(total.group(1)) if total else None, 'rfc':rfc.group(0).upper() if rfc else '', 'descripcion':' | '.join(lines[:4])[:500]}
    fields['confianza']=str(Decimal(sum(bool(fields[k]) for k in ('proveedor','fecha','total'))*100/3).quantize(Decimal('0.01')))
    return fields
