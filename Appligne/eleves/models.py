from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, date
from django.contrib.auth.hashers import make_password # pour crypter des champs

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

from django.db import models
from django.contrib.auth.hashers import make_password

class Parent(models.Model):
    CIVILITE_CHOICES = [
        ('Homme', 'Homme'),
        ('Femme', 'Femme'),
        ('Autre', 'Autre'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
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
