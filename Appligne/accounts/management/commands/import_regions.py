from django.conf import settings
from pathlib import Path
import openpyxl
from django.core.management.base import BaseCommand
from accounts.models import Pays, Region  # Assurez-vous de remplacer myapp par le nom de votre application Django

class Command(BaseCommand):
    help = 'Import regions from Excel file'

    def handle(self, *args, **kwargs):
        file_path = Path(settings.STATIC_ROOT) / 'France.xlsx'  # Chemin vers le fichier Excel dans le répertoire static
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook['Feuil1']  # Assurez-vous de remplacer Feuil1 par le nom de votre feuille Excel
        
        # Itérer sur chaque ligne de la feuille Excel pour créer les objets Pays et Region
        for row in sheet.iter_rows(min_row=2, values_only=True):  # Ignorer la première ligne qui contient les en-têtes
            nom_pays, region_name = row  # Assurez-vous que les colonnes Pays et Région sont correctes
            
            # Vérifier si le pays existe déjà dans la base de données, sinon le créer
            pays, created = Pays.objects.get_or_create(nom_pays=nom_pays)
            
            # Créer l'objet Region lié au pays
            region_obj, created = Region.objects.get_or_create(
                nom_pays=pays,
                region=region_name
            )
            
            # Si la région est déjà existante, ne rien faire, sinon la créer
            if created:
                self.stdout.write(self.style.SUCCESS(f'La région "{region_name}" pour le pays "{nom_pays}" a été ajoutée avec succès.'))
            else:
                self.stdout.write(self.style.WARNING(f'La région "{region_name}" pour le pays "{nom_pays}" existe déjà.'))
