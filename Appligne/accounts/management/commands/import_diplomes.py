from django.conf import settings
from pathlib import Path
import openpyxl
from django.core.management.base import BaseCommand
from accounts.models import Pays, Diplome_cathegorie

class Command(BaseCommand):
    help = 'Import Diplome_cathegories from Excel file'

    def handle(self, *args, **kwargs):
        file_path = Path(settings.BASE_DIR) / 'static' / 'France.xlsx'
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook['Feuil4']
        
        for row in sheet.iter_rows(min_row=2, values_only=True):
            nom_pays, dip_cathegorie = row
            
            # Vérifier si le pays existe déjà dans la base de données, sinon le créer
            pays, created = Pays.objects.get_or_create(nom_pays=nom_pays)
            
            # Vérifier si le diplôme pour ce pays existe déjà, sinon le créer
            diplome_obj, created = Diplome_cathegorie.objects.get_or_create(
                nom_pays=pays,
                dip_cathegorie=dip_cathegorie
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Le diplôme "{dip_cathegorie}" pour le pays "{nom_pays}" a été ajouté avec succès.'))
            else:
                self.stdout.write(self.style.WARNING(f'Le diplôme "{dip_cathegorie}" pour le pays "{nom_pays}" existe déjà.'))
