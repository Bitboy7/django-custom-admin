import hashlib
import logging
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from gastos.models import ComprobanteGasto
from gastos.services.receipt_ocr_service import extract_receipt_fields, read_receipt

logger = logging.getLogger(__name__)

def create_receipt(upload, user):
    digest = hashlib.sha256()
    for chunk in upload.chunks():
        digest.update(chunk)
    upload.seek(0)
    receipt = ComprobanteGasto(archivo=upload, nombre_original=upload.name[:255], content_type=upload.content_type or '', tamano_bytes=upload.size, sha256=digest.hexdigest(), creado_por=user)
    receipt.save()
    return receipt

def process_next_receipt():
    """Claims one job safely; multiple workers can run concurrently on MySQL 8."""
    with transaction.atomic():
        receipt = (ComprobanteGasto.objects.select_for_update(skip_locked=True)
                   .filter(estado=ComprobanteGasto.Estado.PENDIENTE)
                   .order_by('creado_en').first())
        if receipt is None:
            return None
        receipt.estado = ComprobanteGasto.Estado.PROCESANDO
        receipt.error_procesamiento = ''
        receipt.save(update_fields=['estado', 'error_procesamiento'])
    try:
        text = read_receipt(Path(receipt.archivo.path))
        fields = extract_receipt_fields(text)
        receipt.texto_ocr, receipt.datos_extraidos, receipt.confianza = text, fields, fields['confianza']
        receipt.estado, receipt.procesado_en = ComprobanteGasto.Estado.REVISION, timezone.now()
        receipt.save(update_fields=['texto_ocr', 'datos_extraidos', 'confianza', 'estado', 'procesado_en'])
    except Exception as exc:
        logger.exception('OCR failed for receipt %s', receipt.pk)
        receipt.estado, receipt.error_procesamiento, receipt.procesado_en = ComprobanteGasto.Estado.ERROR, str(exc)[:2000], timezone.now()
        receipt.save(update_fields=['estado', 'error_procesamiento', 'procesado_en'])
    return receipt
