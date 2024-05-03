# Importation de la classe AppConfig depuis le module django.apps
from django.apps import AppConfig

# Définition d'une classe AccountsConfig qui hérite de AppConfig
class AccountsConfig(AppConfig):
    # Définition du champ default_auto_field qui spécifie le type de champ automatique utilisé pour les modèles
    default_auto_field = 'django.db.models.BigAutoField'
    # Définition du nom de l'application
    name = 'accounts'

    # Définition d'une méthode ready qui sera appelée lorsque l'application est prête à être utilisée
    def ready(self):
        # Importation du fichier signals.py depuis le répertoire actuel pour activer les signaux
        # Les signaux sont utilisés pour effectuer des actions en réponse à certaines opérations du framework Django
        from . import signals
    #  Les signaux sont utilisés pour exécuter des actions en réponse à certaines opérations du 
    # framework Django, tels que la création, la mise à jour ou la suppression d'objets dans la base de données.
