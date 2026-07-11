import time
from django.core.management.base import BaseCommand
from gastos.services.receipt_service import process_next_receipt

class Command(BaseCommand):
    help = 'Processes queued expense-receipt OCR jobs.'
    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=1)
        parser.add_argument('--loop', action='store_true')
        parser.add_argument('--sleep', type=float, default=2)
    def handle(self, *args, **options):
        count = 0
        while True:
            receipt = process_next_receipt()
            if receipt:
                count += 1
                self.stdout.write(f'Processed receipt {receipt.pk}: {receipt.estado}')
            if not options['loop'] and count >= options['limit']:
                return
            if receipt is None:
                if not options['loop']:
                    return
                time.sleep(options['sleep'])
