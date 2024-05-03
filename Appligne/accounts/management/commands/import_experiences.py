from django.conf import settings
from pathlib import Path
import openpyxl
from django.core.management.base import BaseCommand
from accounts.models import Pays, Experience_cathegorie

class Command(BaseCommand):
    help = 'Import Experience_cathegorie from Excel file'

    def handle(self, *args, **kwargs):
        file_path = Path(settings.BASE_DIR) / 'static' / 'France.xlsx'
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook['Feuil5']
        
        for row in sheet.iter_rows(min_row=2, values_only=True):
            nom_pays, exp_cathegorie = row
            
            try:
                # Vérifier si le pays existe déjà dans la base de données, sinon le créer
                pays, created = Pays.objects.get_or_create(nom_pays=nom_pays)
                
                # Créer l'expérience pour ce pays
                experience_obj, exp_created = Experience_cathegorie.objects.get_or_create(
                    nom_pays=pays,
                    exp_cathegorie=exp_cathegorie
                )
                
                if exp_created:
                    self.stdout.write(self.style.SUCCESS(f'L\'expérience "{exp_cathegorie}" pour le pays "{nom_pays}" a été ajoutée avec succès.'))
                else:
                    self.stdout.write(self.style.WARNING(f'L\'expérience "{exp_cathegorie}" pour le pays "{nom_pays}" existe déjà.'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Une erreur s\'est produite lors de l\'importation pour la ligne : {row}. Erreur : {str(e)}'))

