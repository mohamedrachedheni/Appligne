from django.core.management.base import BaseCommand
import openpyxl
from pathlib import Path
from django.conf import settings
from accounts.models import Niveau_cathegorie, Niveau

class Command(BaseCommand):
    help = 'Importe des niveaux depuis un fichier Excel'

    def handle(self, *args, **kwargs):
        # Chemin du fichier Excel
        file_path = Path(settings.STATIC_ROOT) / 'France.xlsx'

        # Charger le fichier Excel
        try:
            workbook = openpyxl.load_workbook(file_path)
            sheet = workbook['Feuil10']  # Feuille spécifique
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erreur lors du chargement du fichier Excel: {e}"))
            return
        
        # Ignorer la première ligne (en-tête)
        rows = list(sheet.iter_rows(min_row=2, values_only=True))

        for index, row in enumerate(rows, start=2):
            if row and len(row) >= 3:  # Vérifier que la ligne a au moins 3 colonnes
                niv_cathegorie_name, niveau_name, niv_ordre = row[0], row[1], row[2]
                
                if niv_cathegorie_name and niveau_name and niv_ordre is not None:  # Vérifier que les colonnes ne sont pas vides
                    try:
                        # Rechercher ou créer la catégorie de niveau
                        niv_cathegorie, created = Niveau_cathegorie.objects.get_or_create(
                            niv_cathegorie=niv_cathegorie_name
                        )
                        if created:
                            self.stdout.write(self.style.SUCCESS(f"Niveau catégorie '{niv_cathegorie_name}' ajoutée avec succès."))

                        # Vérifier si le niveau existe déjà
                        niveau, created = Niveau.objects.get_or_create(
                            niv_cathegorie=niv_cathegorie,
                            niveau=niveau_name,
                            defaults={'niv_ordre': niv_ordre}
                        )

                        if created:
                            self.stdout.write(self.style.SUCCESS(f"Ligne {index}: Niveau '{niveau_name}' ajouté avec succès."))
                        else:
                            self.stdout.write(self.style.WARNING(f"Ligne {index}: Niveau '{niveau_name}' existe déjà."))

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Ligne {index}: Erreur lors de l'importation: {e}"))
                else:
                    self.stdout.write(self.style.ERROR(f"Ligne {index}: Colonnes vides trouvées."))
            else:
                self.stdout.write(self.style.ERROR(f"Ligne {index}: Ligne vide ou format incorrect."))

        self.stdout.write(self.style.SUCCESS("Importation des niveaux terminée."))
