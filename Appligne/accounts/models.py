# Dans le fichier models.py de votre application "professeur"

####################################################
# Remarque: l'ordre des class est très important
####################################################

from django import forms
from django.db import models
from datetime import date

class Compte(models.Model):
    user = models.CharField(max_length=100, unique=True, blank=False, null=False)
    mot_de_passe = models.CharField(max_length=100, unique=True, blank=False, null=False)

    def __str__(self):
        return f"{self.user}"
    
    class Meta:
        ordering = ['user']
        constraints = [
            models.UniqueConstraint(fields=['user', 'mot_de_passe'], name='unique_user_pass_prof')
        ]


class Professeur(models.Model):
    CIVILITE_CHOICES = [
        ('Homme', 'Homme'),
        ('Femme', 'Femme'),
        ('Autre', 'Autre'),
    ]

    compte = models.OneToOneField(Compte, on_delete=models.CASCADE)
    nom = models.CharField(max_length=100, null=False)
    prenom = models.CharField(max_length=100, null=False)
    civilite = models.CharField(max_length=10, choices=CIVILITE_CHOICES, null=True)
    email = models.EmailField(unique=True, null=False)
    numero_telephone = models.CharField(max_length=15, blank=True, null=True)
    date_naissance = models.DateField(null=True)
    adresse = models.CharField(max_length=255, null=False)
    photo = models.ImageField(upload_to='photos/%y/%m/%d/', null=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.prenom} {self.nom}"
    
    class Meta:
        ordering = ['nom', 'prenom']
    
    class Meta:
        ordering = ['nom']
        constraints = [
            models.UniqueConstraint(fields=['nom', 'prenom'], name='unique_nom_prenom')
        ]

class Diplome_cathegorie(models.Model):
    dip_cathegorie  = models.CharField(max_length=100, unique=True)
    dip_ordre = models.IntegerField()

    def __str__(self):
        return f"{self.dip_cathegorie}"
    
    class Meta:
        ordering = ['dip_ordre']

class Diplome(models.Model):
    professeur = models.ForeignKey(Professeur, on_delete=models.CASCADE)
    diplome = models.CharField(max_length=100, null=True, blank=True)
    obtenu = models.DateField()
    intitule = models.CharField(max_length=255, null=True, blank=True)
    principal = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.professeur.prenom} - {self.diplome}"

    class Meta:
        ordering = ['-principal', '-obtenu']
    
    class Meta:
        ordering = ['professeur']
        constraints = [
            models.UniqueConstraint(fields=['professeur', 'diplome'], name='unique_prof_diplome')
        ]



# n'est pas apparament nécessaire pour le buckofice
# car la liste déroulante est par défaut
class DiplomeForm(forms.ModelForm):
    class Meta:
        model = Diplome
        fields = ['professeur', 'diplome', 'obtenu', 'intitule', 'principal']

    diplome = forms.CharField(widget=forms.Select(attrs={'class': 'select2'}))

class Experience_cathegorie(models.Model):
    exp_cathegorie  = models.CharField(max_length=100, unique=True)
    exp_ordre = models.IntegerField()

    def __str__(self):
        return f"{self.exp_cathegorie}"
    
    class Meta:
        ordering = ['exp_ordre']

class Experience(models.Model):
    professeur = models.ForeignKey(Professeur, on_delete=models.CASCADE)
    type = models.CharField(max_length=100, null=True, blank=True)
    debut = models.DateField()
    fin = models.DateField(null=True, blank=True)
    actuellement = models.BooleanField(default=False)
    commentaire = models.CharField(max_length=255, null=True, blank=True)
    principal = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.professeur.prenom} - {self.type}"

    class Meta:
        ordering = ['professeur','-principal', '-debut']
    
    class Meta:
        ordering = ['professeur']
        constraints = [
            models.UniqueConstraint(fields=['professeur', 'type'], name='unique_prof_type')
        ]




class Format_cour(models.Model):
    professeur = models.OneToOneField(Professeur, on_delete=models.CASCADE)
    a_domicile = models.BooleanField(default=False)
    webcam = models.BooleanField(default=False)
    stage = models.BooleanField(default=False)
    stage_webcam = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.professeur.prenom} {self.professeur.nom} "

    class Meta:
        ordering = ['professeur','-a_domicile', '-webcam']

class Pays(models.Model):
    nom_pays = models.CharField(max_length=100, unique=True)
    drapeau = models.ImageField(upload_to='photos/%y/%m/%d/')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nom_pays}"
    
    class Meta:
        ordering = ['nom_pays']

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
    commune = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"{self.commune}"
    
    class Meta:
        ordering = ['commune']
    
    class Meta:
        ordering = ['departement']
        constraints = [
            models.UniqueConstraint(fields=['departement', 'commune'], name='unique_departement_commune')
        ]


class Prof_zone(models.Model):
    professeur = models.ForeignKey(Professeur, on_delete=models.CASCADE)
    commune = models.ForeignKey(Commune, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.professeur.prenom} {self.professeur.nom} - {self.commune.commune}"
    
    class Meta:
        ordering = ['professeur']
        constraints = [
            models.UniqueConstraint(fields=['professeur', 'commune'], name='unique_prof_commune')
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
    niv_ordre = models.IntegerField()

    def __str__(self):
        return f"{self.niv_cathegorie}"
    
    class Meta:
        ordering = ['niv_ordre']
    
class Niveau(models.Model):
    niv_cathegorie = models.ForeignKey(Niveau_cathegorie, on_delete=models.CASCADE)
    niveau = models.CharField(max_length=100, unique=True)
    niv_ordre = models.IntegerField()

    def __str__(self):
        return f"{self.niv_cathegorie.niv_cathegorie} - {self.niveau}"
    
    class Meta:
        ordering = ['niv_cathegorie', 'niv_ordre']
    

    
class Prof_mat_niv(models.Model):
    professeur = models.ForeignKey(Professeur, on_delete=models.CASCADE)
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE)
    niveau = models.ForeignKey(Niveau, on_delete=models.CASCADE)
    principal = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.professeur.prenom} {self.professeur.nom} - {self.matiere.matiere} - {self.niveau.niveau}"

    # La meta de la contrinte doit etre à la fin
    class Meta:
        ordering = ['professeur', '-principal', 'matiere', 'niveau'] # à corriger le filtre
        constraints = [
            models.UniqueConstraint(fields=['professeur', 'matiere', 'niveau'], name='unique_prof_mat_niv')
            ]

class Pro_fichier(models.Model):
    professeur = models.OneToOneField(Professeur, on_delete=models.CASCADE)
    date_modif = models.DateField(default=date.today, null=True, blank=True)
    titre_fiche = models.CharField(max_length=255)
    description_cours = models.TextField(null=True, blank=True)
    pedagogie = models.TextField(null=True, blank=True)
    video_youtube_url = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.professeur.prenom} {self.professeur.nom} - {self.date_modif}"

    class Meta:
        ordering = ['-date_modif']

class Prof_doc_telecharge(models.Model):
    professeur = models.ForeignKey(Professeur, on_delete=models.CASCADE)
    date_telechargement = models.DateField(default=date.today)
    doc_telecharge = models.ImageField(upload_to='photos/%y/%m/%d/')

    def __str__(self):
        return f"{self.professeur.prenom} {self.professeur.nom} - {self.date_telechargement}"

    class Meta:
        ordering = ['-date_telechargement']

