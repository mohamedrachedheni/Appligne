from django.core.management.base import BaseCommand
import openpyxl
from pathlib import Path
from django.conf import settings
from accounts.models import Niveau_cathegorie

class Command(BaseCommand):
    help = 'Importe des données de niveaux depuis un fichier Excel'

    def handle(self, *args, **kwargs):
        # Chemin du fichier Excel
        file_path = Path(settings.STATIC_ROOT) / 'France.xlsx'

        # Charger le fichier Excel
        try:
            workbook = openpyxl.load_workbook(file_path)
            sheet = workbook['Feuil9']  # Feuille spécifique
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erreur lors du chargement du fichier Excel: {e}"))
            return
        
        # Ignorer la première ligne (en-tête)
        rows = list(sheet.iter_rows(min_row=2, values_only=True))

        for index, row in enumerate(rows, start=2):
            if row and len(row) >= 2:  # Vérifier que la ligne a au moins 2 colonnes
                niv_cathegorie_name, niv_cat_ordre = row[0], row[1]
                
                if niv_cathegorie_name and niv_cat_ordre is not None:  # Vérifier que les colonnes ne sont pas vides
                    try:
                        # Vérifier si la catégorie de niveau existe déjà
                        niv_cathegorie, created = Niveau_cathegorie.objects.get_or_create(
                            niv_cathegorie=niv_cathegorie_name,
                            defaults={'niv_cat_ordre': niv_cat_ordre}
                        )

                        if created:
                            self.stdout.write(self.style.SUCCESS(f"Ligne {index}: Niveau catégorie '{niv_cathegorie_name}' ajoutée avec succès."))
                        else:
                            self.stdout.write(self.style.WARNING(f"Ligne {index}: Niveau catégorie '{niv_cathegorie_name}' existe déjà."))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Ligne {index}: Erreur lors de l'importation: {e}"))
                else:
                    self.stdout.write(self.style.ERROR(f"Ligne {index}: Colonnes vides trouvées."))
            else:
                self.stdout.write(self.style.ERROR(f"Ligne {index}: Ligne vide ou format incorrect."))

        self.stdout.write(self.style.SUCCESS("Importation terminée."))
