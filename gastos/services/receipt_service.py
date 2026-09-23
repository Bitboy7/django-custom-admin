import hashlib
import logging
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from gastos.models import ComprobanteGasto
from gastos.services.receipt_ocr_service import extract_receipt_fields, read_receipt

logger = logging.getLogger(__name__)


@contextmanager
def _local_copy(field_file):
    """Expose a FileField as a local path for OCR engines that require one."""
    suffix = Path(field_file.name).suffix
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            with field_file.open('rb') as source:
                shutil.copyfileobj(source, temp_file)
        yield temp_path
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

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
        # PaddleOCR necesita una ruta local. Esto funciona tanto con disco local
        # como con Cloudflare R2, cuyo FileField no implementa `.path`.
        with _local_copy(receipt.archivo) as local_path:
            text = read_receipt(local_path)
        fields = extract_receipt_fields(text)
        receipt.texto_ocr, receipt.datos_extraidos, receipt.confianza = text, fields, fields['confianza']
        receipt.estado, receipt.procesado_en = ComprobanteGasto.Estado.REVISION, timezone.now()
        receipt.save(update_fields=['texto_ocr', 'datos_extraidos', 'confianza', 'estado', 'procesado_en'])
    except Exception as exc:
        logger.exception('OCR failed for receipt %s', receipt.pk)
        receipt.estado, receipt.error_procesamiento, receipt.procesado_en = ComprobanteGasto.Estado.ERROR, str(exc)[:2000], timezone.now()
        receipt.save(update_fields=['estado', 'error_procesamiento', 'procesado_en'])
    return receipt
