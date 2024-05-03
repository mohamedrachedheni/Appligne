from django.conf import settings
from pathlib import Path
import openpyxl
from django.core.management.base import BaseCommand
from accounts.models import Departement, Commune

class Command(BaseCommand):
    help = 'Import communes with postal codes from Excel file'

    def handle(self, *args, **kwargs):
        file_path = Path(settings.STATIC_ROOT) / 'France.xlsx'  # Chemin vers le fichier Excel dans le répertoire static
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook['Feuil3']  # Assurez-vous de remplacer Feuil3 par le nom de votre feuille Excel
        
        # Itérer sur chaque ligne de la feuille Excel pour créer les objets Commune avec les codes postaux correspondants
        for row in sheet.iter_rows(min_row=2, values_only=True):  # Ignorer la première ligne qui contient les en-têtes
            departement_name, commune_name, code_postal = row  # Assurez-vous que les colonnes Département, Commune et Code Postal sont correctes
            
            # Récupérer l'objet Departement correspondant au nom du département
            departement = Departement.objects.get(departement=departement_name)
            
            # Créer l'objet Commune avec le code postal
            commune_obj, created = Commune.objects.get_or_create(
                departement=departement,
                commune=commune_name,
                code_postal=code_postal
            )
            
            # Si la commune est déjà existante, ne rien faire, sinon la créer
            if created:
                self.stdout.write(self.style.SUCCESS(f'La commune "{commune_name}" dans le département "{departement_name}" avec le code postal "{code_postal}" a été ajoutée avec succès.'))
            else:
                self.stdout.write(self.style.WARNING(f'La commune "{commune_name}" dans le département "{departement_name}" existe déjà.'))
