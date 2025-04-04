from django import forms
from .models import PieceJointeReclamation

class PieceJointeReclamationForm(forms.ModelForm):
    class Meta:
        model = PieceJointeReclamation
        fields = ['fichier']  # Inclure uniquement le champ fichier
    
    def clean_fichier(self):
        fichier = self.cleaned_data.get('fichier')

        # Vérifier si un fichier a été fourni
        if not fichier:
            raise forms.ValidationError("Aucun fichier sélectionné.")

        # Lancer la validation du modèle (y compris FileSizeValidator)
        # fichier.full_clean()

        return fichier
