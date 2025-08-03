from django.core.management.base import BaseCommand
from decimal import Decimal, ROUND_HALF_UP
from accounts.models import Prix_heure

class Command(BaseCommand):
    help = "Met à jour le champ prix_heure_prof avec les 2/3 de prix_heure arrondis au dixième"

    def handle(self, *args, **options):
        updated_count = 0
        prix_heure_records = Prix_heure.objects.filter(prix_heure__isnull=False)

        for record in prix_heure_records:
            prix_heure = record.prix_heure
            prix_heure_prof = (prix_heure * Decimal('2') / Decimal('3')).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
            record.prix_heure_prof = prix_heure_prof
            record.save(update_fields=['prix_heure_prof'])
            updated_count += 1
            self.stdout.write(f"✅ Mis à jour: {record} → {prix_heure_prof} €/h")

        self.stdout.write(self.style.SUCCESS(f"{updated_count} enregistrements mis à jour."))
