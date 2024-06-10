# Dans le fichier models.py de votre application "professeur"

####################################################
# Remarque: l'ordre des class est très important
####################################################

from django import forms
from django.db import models
from datetime import date, datetime
from django.contrib.auth.models import User
from django.db.models import UniqueConstraint
from django.core.validators import MinValueValidator
from decimal import Decimal




class Pays(models.Model):
    nom_pays = models.CharField(max_length=100, unique=True)
    drapeau = models.ImageField(upload_to='photos/%y/%m/%d/')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nom_pays}"
    
    class Meta:
        ordering = ['nom_pays']

class Professeur(models.Model):
    CIVILITE_CHOICES = [
        ('Homme', 'Homme'),
        ('Femme', 'Femme'),
        ('Autre', 'Autre'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    civilite = models.CharField(max_length=10, choices=CIVILITE_CHOICES, null=True)
    numero_telephone = models.CharField(max_length=15, blank=True, null=True)
    date_naissance = models.DateField(null=True)
    adresse = models.CharField(max_length=255, null=False)
    photo = models.ImageField(upload_to='photos/%y/%m/%d/', blank=True, null=True)
    

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"
    
    def set_date_naissance_from_str(self, date_naissance_str):
        if date_naissance_str:
            self.date_naissance = datetime.strptime(date_naissance_str, '%d/%m/%Y').date()




class Diplome_cathegorie(models.Model):
    nom_pays = models.ForeignKey(Pays, on_delete=models.CASCADE)
    dip_cathegorie  = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.dip_cathegorie}"
    
    class Meta:
        ordering = ['dip_cathegorie']
    
    class Meta:
        ordering = ['nom_pays']
        constraints = [
            models.UniqueConstraint(fields=['nom_pays', 'dip_cathegorie'], name='unique_pays_diplome')
        ]

class Diplome(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    diplome_cathegorie = models.ForeignKey(Diplome_cathegorie, on_delete=models.CASCADE)  # Ajout de la clé étrangère vers Diplome_cathegorie
    obtenu = models.DateField()
    intitule = models.CharField(max_length=255, null=True, blank=True)
    principal = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.first_name} - {self.intitule}"  # Mise à jour de la méthode __str__

    def set_date_obtenu_from_str(self, date_obtenu_str):
        if date_obtenu_str:
            self.obtenu = datetime.strptime(date_obtenu_str, '%d/%m/%Y').date()

    class Meta:
        ordering = ['-principal', '-obtenu']
        constraints = [
            models.UniqueConstraint(fields=['user', 'diplome_cathegorie','intitule'], name='unique_user_diplome_intitule')  # Mise à jour de la contrainte d'unicité
        ]
    





class Experience_cathegorie(models.Model):
    nom_pays = models.ForeignKey(Pays, on_delete=models.CASCADE)
    exp_cathegorie  = models.CharField(max_length=100)


    def __str__(self):
        return f"{self.exp_cathegorie}"
    
    class Meta:
        ordering = ['nom_pays','exp_cathegorie']
    
    class Meta:
        ordering = ['nom_pays']
        constraints = [
            models.UniqueConstraint(fields=['nom_pays', 'exp_cathegorie'], name='unique_pays_experience')
        ]

class Experience(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=100, null=True, blank=True)
    debut = models.DateField()
    fin = models.DateField(null=True, blank=True)
    actuellement = models.BooleanField(default=False)
    commentaire = models.CharField(max_length=255, null=True, blank=True)
    principal = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.first_name} - {self.type}"
    
    def set_date_debut_from_str(self, date_debut_str):
        if date_debut_str:
            self.debut = datetime.strptime(date_debut_str, '%d/%m/%Y').date()
    
    def set_date_fin_from_str(self, date_fin_str):
        if date_fin_str:
            self.fin = datetime.strptime(date_fin_str, '%d/%m/%Y').date()

    class Meta:
        ordering = ['user','-principal', '-debut']
    
    class Meta:
        ordering = ['user']
        constraints = [
            models.UniqueConstraint(fields=['user', 'type', 'commentaire'], name='unique_user_type_commentaire')
        ]




class Format_cour(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    a_domicile = models.BooleanField(default=False)
    webcam = models.BooleanField(default=False)
    stage = models.BooleanField(default=False)
    stage_webcam = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} "

    class Meta:
        ordering = ['user','-a_domicile', '-webcam']



class Region(models.Model):
    nom_pays = models.ForeignKey(Pays, on_delete=models.CASCADE)
    region = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"{self.region}"
    
    class Meta:
        ordering = ['region']
    
    class Meta:
        ordering = ['nom_pays']
        constraints = [
            models.UniqueConstraint(fields=['nom_pays', 'region'], name='unique_pays_region')
        ]


class Departement(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    departement = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"{self.departement}"
    
    class Meta:
        ordering = ['departement']

    class Meta:
        ordering = ['region']
        constraints = [
            models.UniqueConstraint(fields=['region', 'departement'], name='unique_region_departement')
        ]

class Commune(models.Model):
    departement = models.ForeignKey(Departement, on_delete=models.CASCADE)
    commune = models.CharField(max_length=100)
    code_postal = models.CharField(max_length=100,null=True, blank=True)

    def __str__(self):
        return f"{self.commune}"
    
    class Meta:
        ordering = ['commune']
    
    class Meta:
        ordering = ['departement']
        constraints = [
            models.UniqueConstraint(fields=['departement', 'commune', 'code_postal'], name='unique_departement_commune_postal)')
        ]


class Prof_zone(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    commune = models.ForeignKey(Commune, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.commune.commune}"
    
    class Meta:
        ordering = ['user']
        constraints = [
            models.UniqueConstraint(fields=['user', 'commune'], name='unique_user_commune')
        ]

    
class Matiere_cathegorie(models.Model):
    mat_cathegorie = models.CharField(max_length=100, unique=True)
    mat_cat_ordre = models.IntegerField()

    def __str__(self):
        return f"{self.mat_cathegorie}"
    
    class Meta:
        ordering = ['mat_cat_ordre']

class Matiere(models.Model):
    mat_cathegorie = models.ForeignKey(Matiere_cathegorie, on_delete=models.CASCADE)
    matiere = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"{self.mat_cathegorie.mat_cathegorie} - {self.matiere}"
    
    class Meta:
        ordering = ['mat_cathegorie', 'matiere']

class Niveau_cathegorie(models.Model):
    niv_cathegorie  = models.CharField(max_length=100, unique=True)
    niv_cat_ordre = models.IntegerField()

    def __str__(self):
        return f"{self.niv_cathegorie}"
    
    class Meta:
        ordering = ['niv_cat_ordre']
    
class Niveau(models.Model):
    niv_cathegorie = models.ForeignKey(Niveau_cathegorie, on_delete=models.CASCADE)
    niveau = models.CharField(max_length=100, unique=True)
    niv_ordre = models.IntegerField()

    def __str__(self):
        return f"{self.niv_cathegorie.niv_cathegorie} - {self.niveau}"
    
    class Meta:
        ordering = ['niv_cathegorie', 'niv_ordre']
    

    
class Prof_mat_niv(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE)
    niveau = models.ForeignKey(Niveau, on_delete=models.CASCADE)
    principal = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.matiere.matiere} - {self.niveau.niveau}"

    # La meta de la contrinte doit etre à la fin
    class Meta:
        ordering = ['user', '-principal', 'matiere', 'niveau'] # à corriger le filtre
        constraints = [
            models.UniqueConstraint(fields=['user', 'matiere', 'niveau'], name='unique_user_mat_niv')
            ]

class Pro_fichier(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_modif = models.DateField(default=date.today, null=True, blank=True)
    titre_fiche = models.CharField(max_length=255)
    parcours = models.TextField(null=True, blank=True)
    pedagogie = models.TextField(null=True, blank=True)
    video_youtube_url = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.date_modif}"

    class Meta:
        ordering = ['-date_modif']

class Prof_doc_telecharge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date_telechargement = models.DateField(default=date.today)
    doc_telecharge = models.ImageField(upload_to='photos/%y/%m/')

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.date_telechargement}"

    class Meta:
        ordering = ['-date_telechargement']

class Email_telecharge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    date_telechargement = models.DateField(default=date.today)
    email_telecharge = models.CharField(max_length=255, null=True, blank=True)  # l'adresse email de l'envoyeur
    sujet = models.CharField(max_length=255, null=True, blank=True)
    text_email = models.TextField(null=True, blank=True)
    user_destinataire = models.IntegerField()  # champ obligatoire du destinataire de l'email

    def __str__(self):
        return f"{self.user.first_name if self.user else 'No User'} {self.user.last_name if self.user else ''} - {self.date_telechargement}"

    class Meta:
        ordering = ['-date_telechargement']

class Email_detaille(models.Model):
    email = models.OneToOneField(Email_telecharge, on_delete=models.CASCADE)
    user_nom = models.CharField(max_length=255, null=True, blank=True) 
    matiere = models.CharField(max_length=255, null=True, blank=True) 
    niveau = models.CharField(max_length=255, null=True, blank=True) 
    format_cours =models.CharField(max_length=255, null=True, blank=True) 


class Email_suivi(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email = models.ForeignKey(Email_telecharge, on_delete=models.CASCADE)  # id de l'email envoyé par le user
    SUIVI_CHOICES = [
        ('Ignorer', 'Ignorer'),
        ('Réception confirmée', 'Réception confirmée'),
        ('Répondre', 'Répondre'),
    ]
    suivi = models.CharField(max_length=25, choices=SUIVI_CHOICES, null=True)
    date_suivi = models.DateField(default=date.today)
    reponse_email_id = models.IntegerField(null=True) # id de email reçu par le user et au quel il a répondu par défaut = null

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.date_suivi}"


class Prix_heure(models.Model):
    FORMAT_COUR = [
        ('a_domicile', 'Cours à domicile'),
        ('webcam', 'Cours par webcam'),
        ('stage', 'Stage pendant les vacances'),
        ('stage_webcam', 'Stage par webcam'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    prof_mat_niv = models.ForeignKey(Prof_mat_niv, on_delete=models.CASCADE)
    format = models.CharField(max_length=30, choices=FORMAT_COUR, null=True)
    prix_heure = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))], 
        null=True, 
        blank=True
    )
    class Meta:
        ordering = ['user', 'prof_mat_niv']
        constraints = [
            models.UniqueConstraint(fields=['user', 'prof_mat_niv', 'format'], name='prof_mat_niv_format')
        ]

