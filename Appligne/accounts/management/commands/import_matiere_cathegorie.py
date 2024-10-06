from django.core.management.base import BaseCommand
import openpyxl
from pathlib import Path
from django.conf import settings
from accounts.models import Matiere_cathegorie

class Command(BaseCommand):
    help = 'Importe des données de matieres depuis un fichier Excel'

    def handle(self, *args, **kwargs):
        # Chemin du fichier Excel
        file_path = Path(settings.STATIC_ROOT) / 'France.xlsx'

        # Charger le fichier Excel
        try:
            workbook = openpyxl.load_workbook(file_path)
            sheet = workbook['Feuil7']  # Feuille spécifique
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erreur lors du chargement du fichier Excel: {e}"))
            return
        
        # Ignorer la première ligne (en-tête)
        rows = list(sheet.iter_rows(min_row=2, values_only=True))

        for index, row in enumerate(rows, start=2):
            if row and len(row) >= 2:  # Vérifier que la ligne a au moins 2 colonnes
                mat_cathegorie, mat_cat_ordre = row[0], row[1]
                
                if mat_cathegorie and mat_cat_ordre:  # Vérifier que les colonnes ne sont pas vides
                    if not Matiere_cathegorie.objects.filter(mat_cathegorie=mat_cathegorie).exists():
                        Matiere_cathegorie.objects.create(
                            mat_cathegorie=mat_cathegorie,
                            mat_cat_ordre=mat_cat_ordre
                        )
                        self.stdout.write(self.style.SUCCESS(f"Ligne {index}: Matiere '{mat_cathegorie}' ajoutée."))
                    else:
                        self.stdout.write(self.style.WARNING(f"Ligne {index}: Matiere '{mat_cathegorie}' existe déjà."))
                else:
                    self.stdout.write(self.style.ERROR(f"Ligne {index}: Colonnes vides trouvées."))
            else:
                self.stdout.write(self.style.ERROR(f"Ligne {index}: Ligne vide ou format incorrect."))

        self.stdout.write(self.style.SUCCESS("Importation terminée."))
