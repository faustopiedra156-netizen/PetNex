from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from citas.models import CodigoRecuperacionContrasena


class Command(BaseCommand):
    help = 'Elimina códigos de recuperación vencidos o utilizados hace más de 30 días.'

    def handle(self, *args, **options):
        limite = timezone.now() - timedelta(days=30)
        eliminados, _ = CodigoRecuperacionContrasena.objects.filter(
            Q(expira_en__lt=limite) | Q(usado_en__lt=limite)
        ).delete()
        self.stdout.write(self.style.SUCCESS(f'Códigos de recuperación eliminados: {eliminados}.'))
