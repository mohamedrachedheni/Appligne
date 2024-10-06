from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, date
from django.contrib.auth.hashers import make_password # pour crypter des champs
from django.core.exceptions import ValidationError


# Create your models here.

class Eleve(models.Model):
    CIVILITE_CHOICES = [
        ('Homme', 'Homme'),
        ('Femme', 'Femme'),
        ('Autre', 'Autre'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    civilite = models.CharField(max_length=10, choices=CIVILITE_CHOICES, null=True)
    numero_telephone = models.CharField(max_length=15, blank=True, null=True)
    date_naissance = models.DateField(null=True)
    adresse = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"
    
    def set_date_naissance_from_str(self, date_naissance_str):
        if date_naissance_str:
            self.date_naissance = datetime.strptime(date_naissance_str, '%d/%m/%Y').date()



class Parent(models.Model):
    CIVILITE_CHOICES = [
        ('Homme', 'Homme'),
        ('Femme', 'Femme'),
        ('Autre', 'Autre'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE) # C'est le user de l'eleve dont le parent est lié
    prenom_parent = models.CharField(max_length=255, null=False, blank=False)
    nom_parent = models.CharField(max_length=255, null=False, blank=False)
    civilite = models.CharField(max_length=10, choices=CIVILITE_CHOICES, null=True)
    telephone_parent = models.CharField(max_length=15, blank=True, null=True)
    email_parent = models.CharField(max_length=255, null=True, blank=True)
    code_carte = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"
    
    def set_date_naissance_from_str(self, date_naissance_str):
        if date_naissance_str:
            self.date_naissance = datetime.strptime(date_naissance_str, '%d/%m/%Y').date()
    
    def set_encrypted_code_carte(self, code_carte_plain):
        if code_carte_plain:
            self.code_carte = make_password(code_carte_plain)
            

from django.db import models
from django.contrib.auth.models import User

class Temoignage(models.Model):
    # Définition des différentes évaluations
    MAUVAIS = 1
    MOYEN = 2
    BIEN = 3
    TRES_BIEN = 4
    EXCELLENT = 5

    # Choix de statuts de la séance
    STATUS_CHOICES = [
        (MAUVAIS, 'Mauvais'),
        (MOYEN, 'Moyen'),
        (BIEN, 'Bien'),
        (TRES_BIEN, 'Très bien'),
        (EXCELLENT, 'Excellent'),
    ]

    # Champs du modèle
    user_eleve = models.ForeignKey(User, related_name='temoignages_eleve', on_delete=models.CASCADE)  # Élève
    text_eleve = models.TextField(null=True, blank=True)
    evaluation_eleve = models.PositiveSmallIntegerField(choices=STATUS_CHOICES, default=BIEN)  # Évaluation de l'élève (entier entre 1 et 5)
    user_prof = models.ForeignKey(User, related_name='temoignages_prof', on_delete=models.CASCADE)  # Professeur
    text_prof = models.TextField(null=True, blank=True)
    date_creation = models.DateField(auto_now_add=True)  # Date de création 
    date_modification = models.DateField(auto_now=True)  # Date de mise à jour

    def __str__(self):
        return f"Témoignage de {self.user_eleve.username} pour {self.user_prof.username}"




