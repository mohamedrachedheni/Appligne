from django.core.management.base import BaseCommand
import openpyxl
from pathlib import Path
from django.conf import settings
from accounts.models import Matiere, Matiere_cathegorie

class Command(BaseCommand):
    help = 'Importe des données de matieres depuis un fichier Excel'

    def handle(self, *args, **kwargs):
        # Chemin du fichier Excel
        file_path = Path(settings.STATIC_ROOT) / 'France.xlsx'

        # Charger le fichier Excel
        try:
            workbook = openpyxl.load_workbook(file_path)
            sheet = workbook['Feuil8']  # Feuille spécifique
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erreur lors du chargement du fichier Excel: {e}"))
            return
        
        # Ignorer la première ligne (en-tête)
        rows = list(sheet.iter_rows(min_row=2, values_only=True))

        for index, row in enumerate(rows, start=2):
            if row and len(row) >= 2:  # Vérifier que la ligne a au moins 2 colonnes
                mat_cathegorie_name, matiere_name = row[0], row[1]
                
                if mat_cathegorie_name and matiere_name:  # Vérifier que les colonnes ne sont pas vides
                    try:
                        # Chercher la catégorie de matière correspondante
                        mat_cathegorie, created = Matiere_cathegorie.objects.get_or_create(
                            mat_cathegorie=mat_cathegorie_name
                        )

                        # Vérifier si la matière existe déjà
                        if not Matiere.objects.filter(matiere=matiere_name, mat_cathegorie=mat_cathegorie).exists():
                            Matiere.objects.create(
                                mat_cathegorie=mat_cathegorie,
                                matiere=matiere_name
                            )
                            self.stdout.write(self.style.SUCCESS(f"Ligne {index}: Matiere '{matiere_name}' ajoutée."))
                        else:
                            self.stdout.write(self.style.WARNING(f"Ligne {index}: Matiere '{matiere_name}' existe déjà."))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Ligne {index}: Erreur lors de l'importation: {e}"))
                else:
                    self.stdout.write(self.style.ERROR(f"Ligne {index}: Colonnes vides trouvées."))
            else:
                self.stdout.write(self.style.ERROR(f"Ligne {index}: Ligne vide ou format incorrect."))

        self.stdout.write(self.style.SUCCESS("Importation terminée."))
