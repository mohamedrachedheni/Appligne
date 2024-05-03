from django.conf import settings
from pathlib import Path
import openpyxl
from django.core.management.base import BaseCommand
from accounts.models import Region, Departement

class Command(BaseCommand):
    help = 'Import departments from Excel file'

    def handle(self, *args, **kwargs):
        file_path = Path(settings.STATIC_ROOT) / 'France.xlsx'  # Chemin vers le fichier Excel dans le répertoire static
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook['Feuil2']  # Assurez-vous de remplacer Feuil2 par le nom de votre feuille Excel
        
        # Itérer sur chaque ligne de la feuille Excel pour créer les objets Departement
        for row in sheet.iter_rows(min_row=2, values_only=True):  # Ignorer la première ligne qui contient les en-têtes
            region_name, departement_name = row  # Assurez-vous que les colonnes Région et Département sont correctes
            
            # Récupérer l'objet Region correspondant au nom de la région
            region = Region.objects.get(region=region_name)
            
            # Créer l'objet Departement lié à la région
            departement_obj, created = Departement.objects.get_or_create(
                region=region,
                departement=departement_name
            )
            
            # Si le département est déjà existant, ne rien faire, sinon le créer
            if created:
                self.stdout.write(self.style.SUCCESS(f'Le département "{departement_name}" pour la région "{region_name}" a été ajouté avec succès.'))
            else:
                self.stdout.write(self.style.WARNING(f'Le département "{departement_name}" pour la région "{region_name}" existe déjà.'))
