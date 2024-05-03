# Importation des classes nécessaires pour les signaux Django
from django.db.models.signals import post_migrate
from django.dispatch import receiver

# Importation des modèles nécessaires pour créer les catégories et les matières
from accounts.models import Matiere_cathegorie, Matiere

# Définition d'une fonction pour créer les catégories et les matières associées lors de la migration
@receiver(post_migrate)
def create_matiere_cathegories(sender, **kwargs):
    # Vérification si la migration provient de l'application 'accounts'
    if sender.name == 'accounts':
        # Définition des catégories et de leurs matières associées
        categories = [
            {"category": "Enseignements scientifiques", "subjects": ["Chimie",
                                                                    "Dessin industriel",
                                                                    "Electronique",
                                                                    "Informatique",
                                                                    "Logique maths",
                                                                    "Maths",
                                                                    "NSI",
                                                                    "Physique",
                                                                    "Physique-chimie",
                                                                    "Sciences de l'ingénieurs",
                                                                    "Statistique"
                                                                    ]},
            {"category": "Lettres", "subjects": ["Français",
                                                "Grec",
                                                "Latin",
                                                "Orthographe",
                                                "Synthèse de document"
                                                ]},
            {"category": "Langues vivantes", "subjects": ["Allemand",
                                                           "Anglais",
                                                           "Arabe",
                                                           "Chinois",
                                                           "Coréen",
                                                           "Espagnol",
                                                           "FLE",
                                                           "Italien",
                                                           "Japonais",
                                                           "Portugais",
                                                           "Russe"
                                                           ]},
            {"category": "Sciences humaines", "subjects": ["Culture générale",
                                                           "Education civique",
                                                           "ESH",
                                                           "Géopolitique",
                                                           "Histoire - Géographie",
                                                           "Humanites litérature philosophie",
                                                           "Management",
                                                           "Philosophie",
                                                           "Sciences politiques",
                                                           ]},
            {"category": "Economie", "subjects": ["Comptabilité",
                                                           "Control de gestion",
                                                           "Droit",
                                                           "Economie",
                                                           "Fiscalité",
                                                           "Gestion financière",
                                                           "Macroéconomie",
                                                           "Marketing",
                                                           "Microéconomie",
                                                           "SES",
                                                           ]},
            {"category": "Sciences naturelles", "subjects": ["Anatomie",
                                                           "Biologie",
                                                           "Biologie - Ecologie",
                                                           "Biochimie",
                                                           "Biophysique",
                                                           "Biostatique",
                                                           "SVT",
                                                           ]},
            {"category": "Préparation orale", "subjects": ["Coaching scolaire",
                                                           "Entretien de motivation",
                                                           "Grand oral du bac",
                                                           "Orientation scolaire",
                                                           "TIPE",
                                                           "TPE",
                                                           ]},
            {"category": "Enseignements artistiques", "subjects": ["Art du cirque",
                                                           "Arts plastiques",
                                                           "Cinéma audiovisuel",
                                                           "Danse",
                                                           "Histoire des arts",
                                                           "Musique",
                                                           "Théatre",
                                                           ]},
            # Ajoutez d'autres catégories et sujets au besoin
        ]
        # Parcours des catégories avec un indice de départ à 1
        for idx, cat_data in enumerate(categories, start=1):
            # Création de la catégorie si elle n'existe pas déjà
            category, created = Matiere_cathegorie.objects.get_or_create(
                mat_cathegorie=cat_data["category"],
                defaults={"mat_cat_ordre": idx}  # Utilisation de l'index pour définir l'ordre
            )
            # Sauvegarde de la catégorie si elle a été créée
            if created:
                category.save()  # Assurez-vous de sauvegarder la catégorie avant d'ajouter les matières

            # Ajout des matières associées à la catégorie
            for subject in cat_data["subjects"]:
                # Création de la matière si elle n'existe pas déjà
                Matiere.objects.get_or_create(
                    mat_cathegorie=category,
                    matiere=subject
                )




# Importation des modèles nécessaires pour créer les catégories et les niveaux
from accounts.models import Niveau_cathegorie, Niveau

# Définition d'une fonction pour créer les catégories et les niveaux associés lors de la migration
@receiver(post_migrate)
def create_niveau_cathegories(sender, **kwargs):
    # Vérification si la migration provient de l'application 'accounts'
    if sender.name == 'accounts':
        # Définition des catégories de niveau et de leurs niveaux associés
        categories = [
            {"category": "Collège", "levels": ["6ème", 
                                               "5ème", 
                                               "4ème", 
                                               "3ème"]},
            {"category": "Lycée", "levels": ["Seconde", 
                                             "Première STMGL", 
                                             "Première STL", 
                                             "Première Générale", 
                                             "Première STI2D", 
                                             "Terminale STMG", 
                                             "Terminale STI2D", 
                                             "Terminale Générale", 
                                             "Terminale STL"]},
            {"category": "Concours et prépa", "levels": ["Prépa Concours Geipi Polytech", 
                                                         "Avenir-Puissance Alpha-Advance-Geipi", 
                                                         "Acces-Sésame", 
                                                         "Prépa Concours Avenir", 
                                                         "Prépa Sciences Po", 
                                                         "Prépa Concours ESA", 
                                                         "Prépa Concours Advance", 
                                                         "Prépa Concours Acces", 
                                                         "Prépa Concours CRPE",
                                                         "Pass BBA", 
                                                         "Prépa Concours Puissance Alpha", 
                                                         "Prépa Concours Sésame", 
                                                         "Prépa intégrée 1ère année"]},
            {"category": "Autres", "levels": ["MP2I", 
                                              "MPSI", 
                                              "TSI", 
                                              "TB", 
                                              "TBC", 
                                              "ATS", 
                                              "PTSI", 
                                              "BBPST", 
                                              "PCSI", 
                                              "Math Sup", 
                                              "MP", 
                                              "PSI", 
                                              "PC", 
                                              "Prépa intégré 2ème année", 
                                              "TSI 2", 
                                              "MPI", 
                                              "PT", 
                                              "BCPST 2", 
                                              "Maths Spé", 
                                              "ECG 1", 
                                              "D1 ENS Cachan", 
                                              "Hypokhâgne ALL", 
                                              "Khâgne AL", 
                                              "Khâgne BL", 
                                              "Gei Univ", 
                                              "CAST Ing", 
                                              "TOEIC", 
                                              "Tage Mage", 
                                              "GMAT", 
                                              "Score IAE Message", 
                                              "TOEFL", 
                                              "Architechture", 
                                              "Infirmier", 
                                              "Capes", 
                                              "Tage 2", 
                                              "IELTS", 
                                              "DCG", 
                                              "DSCG", 
                                              "Agrégation", 
                                              "BUT", 
                                              "BTS", 
                                              "Licence 1", 
                                              "Licence 2", 
                                              "Licence 3", 
                                              "Master 1", 
                                              "Master 2", 
                                              "Adultes"]},

            # Ajoutez d'autres catégories et niveaux au besoin
        ]
        # Parcours des catégories de niveau avec un indice de départ à 1
        for idx, cat_data in enumerate(categories, start=1):
            # Création de la catégorie de niveau si elle n'existe pas déjà
            category, created = Niveau_cathegorie.objects.get_or_create(
                niv_cathegorie=cat_data["category"],
                defaults={"niv_cat_ordre": idx}  # Utilisation de l'index pour définir l'ordre
            )
            # Sauvegarde de la catégorie de niveau si elle a été créée
            if created:
                category.save()  # Assurez-vous de sauvegarder la catégorie de niveau avant d'ajouter les niveaux

            # Ajout des niveaux associés à la catégorie de niveau
            for level_idx, level in enumerate(cat_data["levels"], start=1):
                # Création du niveau avec un ordre incrémenté
                Niveau.objects.get_or_create(
                    niv_cathegorie=category,
                    niveau=level,
                    niv_ordre=level_idx  # Utilisation de l'index pour définir l'ordre
                )
