from django.core.management.base import BaseCommand
import openpyxl
from pathlib import Path
from django.conf import settings
from pages.models import FAQ

class Command(BaseCommand):
    help = "Importe des données de Faqs depuis un fichier Excel."

    def handle(self, *args, **kwargs):
        # Définition du chemin du fichier Excel
        file_path = Path(settings.STATIC_ROOT) / 'France.xlsx'

        # Vérifier si le fichier existe
        if not file_path.exists():
            self.stdout.write(self.style.ERROR(f"Le fichier '{file_path}' est introuvable."))
            return

        # Chargement du fichier Excel
        try:
            workbook = openpyxl.load_workbook(file_path, data_only=True)
            sheet = workbook['Feuil12']  # Vérifie bien que ce nom de feuille est correct
        except KeyError:
            self.stdout.write(self.style.ERROR("Feuille 'Feuil12' introuvable dans le fichier Excel."))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erreur lors du chargement du fichier Excel : {e}"))
            return

        # Lecture des lignes (en ignorant l'en-tête)
        rows = list(sheet.iter_rows(min_row=2, values_only=True))

        if not rows:
            self.stdout.write(self.style.WARNING("Aucune donnée trouvée dans le fichier."))
            return

        for index, row in enumerate(rows, start=2):
            if row and len(row) >= 3:
                question, reponse, public_cible, ordre, actif = row[0], row[1], row[2], row[3], row[4]

                if not all([question, reponse, public_cible, ordre, actif]):
                    self.stdout.write(self.style.ERROR(f"Ligne {index}: Une ou plusieurs colonnes sont vides."))
                    continue

                try:
                    ordre = int(ordre)  # Assurer que `ordre` est bien un entier
                except ValueError:
                    self.stdout.write(self.style.ERROR(f"Ligne {index}: Valeur 'ordre' invalide (doit être un entier)."))
                    continue

                try:
                    actif = int(actif)  # Assurer que `ordre` est bien un entier
                except ValueError:
                    self.stdout.write(self.style.ERROR(f"Ligne {actif}: Valeur 'ordre' invalide (doit être un entier)."))
                    continue

                # Ajout ou récupération de la catégorie
                obj, created = FAQ.objects.get_or_create(
                    question=question,
                    defaults={'reponse': reponse, 'public_cible': public_cible, 'ordre': ordre, 'actif': actif}
                )

                if created:
                    self.stdout.write(self.style.SUCCESS(f"Ligne {index}: Question '{question}' ajoutée."))
                else:
                    self.stdout.write(self.style.WARNING(f"Ligne {index}: Question '{question}' existe déjà."))

            else:
                self.stdout.write(self.style.ERROR(f"Ligne {index}: Ligne vide ou format incorrect."))

        self.stdout.write(self.style.SUCCESS("Importation terminée avec succès."))
