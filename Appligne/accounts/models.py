# Dans le fichier models.py de votre application "professeur"

####################################################
# Remarque: l'ordre des class est très important
####################################################

from django.db import models
from django.contrib.auth.models import User
from django.db.models import UniqueConstraint
from django.core.validators import MinValueValidator
from decimal import Decimal
from eleves.models import Eleve
from datetime import date, datetime
# from datetime import timedelta


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

    civilite = models.CharField(max_length=10, choices=CIVILITE_CHOICES, null=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
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



class Email_telecharge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True) # ID de l'expéditeur 
    date_telechargement = models.DateTimeField(default=date.today)
    email_telecharge = models.CharField(max_length=255, null=True, blank=True)  # l'adresse email de l'expéditeur
    sujet = models.CharField(max_length=255, null=True, blank=True)
    text_email = models.TextField(null=True, blank=True)
    user_destinataire = models.IntegerField()  # champ obligatoire du destinataire de l'email 
    SUIVI_CHOICES = [
        ('Mis à côté', 'Mis à côté'),
        ('Réception confirmée', 'Réception confirmée'),
        ('Répondu', 'Répondu'),
    ]
    suivi = models.CharField(max_length=25, choices=SUIVI_CHOICES, null=True)
    date_suivi = models.DateTimeField(default=date.today)
    reponse_email_id = models.IntegerField(null=True) # id de email reçu par le user et au quel il a répondu par défaut = null
    

    def __str__(self):
        return f"{self.user.first_name if self.user else 'No User'} {self.user.last_name if self.user else ''} - {self.date_telechargement}"

    class Meta:
        ordering = ['-date_telechargement']

class Prof_doc_telecharge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date_telechargement = models.DateField(default=date.today)
    doc_telecharge = models.ImageField(upload_to='photos/%y/%m/')
    email_telecharge = models.ForeignKey(Email_telecharge, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.date_telechargement}"

    class Meta:
        ordering = ['-date_telechargement']

class Email_detaille(models.Model):
    email = models.OneToOneField(Email_telecharge, on_delete=models.CASCADE)
    user_nom = models.CharField(max_length=255, null=True, blank=True) 
    matiere = models.CharField(max_length=255, null=True, blank=True) 
    niveau = models.CharField(max_length=255, null=True, blank=True) 
    format_cours =models.CharField(max_length=255, null=True, blank=True) 



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


class Mes_eleves(models.Model):  # Mes élèves 
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # ID user professeur
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE)  # Relation un à plusieurs avec les élèves
    is_active = models.BooleanField(default=True)  # Prise en charge en cours
    remarque = models.CharField(max_length=255, null=True, blank=True)  # Remarque
    date_creation = models.DateTimeField(auto_now_add=True)  # Date de création de l'enregistrement
    date_modification = models.DateTimeField(auto_now=True)  # Date de mise à jour

    def date_modification_formatee(self):
        return self.date_modification.strftime('%d%m%y')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'eleve'], name='unique_user_eleve')
        ]




class Cours(models.Model):  # Les cours planifiés par le prof pour l'élève
    user = models.ForeignKey(User, on_delete=models.CASCADE) # ID user professeur
    mon_eleve = models.ForeignKey(Mes_eleves, on_delete=models.CASCADE)  # ID de l'élève inscrit dans la table Mes_eleve
    format_cours = models.CharField(max_length=255, null=True, blank=True)  # Format du cours selon les valeurs près définies ou personalisées
    matiere = models.CharField(max_length=255, null=True, blank=True)  # matière dans la table matiere ou personalisé
    niveau = models.CharField(max_length=255, null=True, blank=True)  # niveau dans la table niveau ou personalisé
    prix_heure = models.FloatField()  # Prix par heure du cours
    is_active = models.BooleanField(default=True) #  en cours / achevé
    date_creation = models.DateTimeField(auto_now_add=True)  # Date de création du cours planifié
    date_modification = models.DateTimeField(auto_now=True)  # Date de mise à jour
    def date_modification_formatee(self):
        return self.date_modification.strftime('%d%m%y')



class Horaire(models.Model):  # Les horaires des séances du cours planifié par le prof pour l'élève
    # Définition des différents statuts de la séance du cours
    EN_ATTENTE = 'en_attente'
    REALISER = 'realiser'
    ANNULER = 'annuler'

    # Choix de statuts de la séance
    STATUS_CHOICES = [
        (EN_ATTENTE, 'En attente'),
        (REALISER, 'Réaliser'),
        (ANNULER, 'Annuler'),
    ]
    cours = models.ForeignKey(Cours, on_delete=models.CASCADE)  # ID du modèle Cours
    date_cours = models.DateField(null=True)  # Date du cours
    heure_debut = models.TimeField(null=True)  # Heure de début du cours
    heure_fin = models.TimeField(null=True)  # Heure de fin du cours
    duree = models.FloatField(null=True, default=1)  # Durée de la séance
    contenu = models.CharField(max_length=255)  # Contenu du cours
    statut_cours = models.CharField(max_length=10, choices=STATUS_CHOICES, default=EN_ATTENTE)  # Statut de la séance
    payment_id = models.IntegerField(null=True)  # ID du modèle Payment, si null pas de paiement
    demande_paiement_id = models.IntegerField(null=True)  # ID du modèle Demande_paiement, si null pas de demande de paiement en cours
    date_creation = models.DateTimeField(auto_now_add=True)  # Date de création de l'horaire de la séance
    date_modification = models.DateTimeField(auto_now=True)  # Date de mise à jour

    def set_date_obtenu_from_str(self, date_obtenu_str):
        if date_obtenu_str:
            self.date_cours = datetime.strptime(date_obtenu_str, '%d/%m/%Y').date()
    def set_heure_debut_from_str(self, heure_debut_str):
        if heure_debut_str:
            self.heure_debut = datetime.strptime(heure_debut_str, '%H:%M').time()

    def set_heure_fin_from_str(self, heure_fin_str):
        if heure_fin_str:
            self.heure_fin = datetime.strptime(heure_fin_str, '%H:%M').time()
    def __str__(self): # Cette méthode __str__ garantit que, chaque fois que l'objet Horaire est converti en chaîne de caractères, seul l'ID est renvoyé.
        return str(self.id)
    def calculer_duree(self):
        if self.heure_debut and self.heure_fin:
            # Convertir les heures en datetime pour pouvoir les soustraire
            datetime_debut = datetime.combine(datetime.today(), self.heure_debut)
            datetime_fin = datetime.combine(datetime.today(), self.heure_fin)
            duree = datetime_fin - datetime_debut
            # Convertir la durée en heures et arrondir à 2 décimales
            self.duree = round(duree.total_seconds() / 3600, 2)
        else:
            self.duree = 1  # valeur par défaut si les heures ne sont pas définies



class Historique_prof(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_premier_cours = models.DateField(null=True, blank=True)  # Date de règlement du premier cours
    date_dernier_cours = models.DateField(null=True, blank=True)  # Date de règlement du dernier cours
    nb_eleve_inscrit = models.IntegerField(default=0)  # Nombre d'élèves qui ont payé leur cours
    nb_heure_declare = models.IntegerField(default=0)  # Nombre d'heures de cours payées
    nb_evaluation = models.IntegerField(default=0)  # Nombre d'évaluations des élèves inscrits
    total_point_cumule = models.IntegerField(default=0)  # Cumul des points d'évaluation [1, 5]
    moyenne_point_cumule = models.IntegerField(default=0)  # Moyenne des cumuls des points d'évaluation
    nb_reponse_demande_cours = models.IntegerField(default=0)  # Cumul des réponses aux demandes de cours (seule les demande de cours aux quelles le prof à répondu son prises en compte)
    total_cumul_temps_reponse = models.IntegerField(default=0)  # Cumul du temps en secondes écoulé entre la demande de cours et sa réponse
    moyenne_temps_reponse = models.IntegerField(null=True, blank=True)  # Moyenne des cumuls des points d'évaluation

class Payment(models.Model):
    # Statuts de paiement
    PENDING = 'pending'
    APPROVED = 'approved'
    CANCELED = 'canceled'
    INVALID = 'invalid'

    STATUS_CHOICES = [
        (PENDING, 'En attente'),
        (APPROVED, 'Approuvé'),
        (CANCELED, 'Annulé'),
        (INVALID, 'Invalide'),
    ]

    model = models.CharField(max_length=255)  # Model liée au paiement (ex: Demande_paiement)
    model_id = models.IntegerField()  # ID de l'objet dans le modèle lié
    slug = models.CharField(max_length=255)  # Identifiant unique
    reference = models.CharField(max_length=255)  # Référence interne du paiement
    payment_attempts = models.PositiveIntegerField(default=1)  # Nombre de tentatives
    expiration_date = models.DateTimeField()  # Date d'expiration du paiement
    amount = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))], 
        null=True, 
        blank=True
    )  # Montant du paiement
    currency = models.CharField(max_length=10)  # Devise
    source = models.CharField(max_length=255, default='desktop')  # Source (web/mobile)
    language = models.CharField(max_length=10)  # Langue utilisée
    membership_number = models.CharField(max_length=255, null=True, blank=True)  # Numéro d'adhésion
    payment_register_data = models.JSONField(null=True, blank=True)  # Données de la passerelle
    order_id = models.CharField(max_length=255, null=True, blank=True)  # ID de commande
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)  # Statut
    payment_date = models.DateTimeField(null=True, blank=True)  # Date de paiement
    payment_body = models.JSONField(null=True, blank=True)  # Détails supplémentaires
    approved = models.BooleanField(default=True) # Approuvé par l'élève, Pas de réclamation 
    accord = models.BooleanField(default=False) # Accord de paiement par l'administrateur 
    date_creation = models.DateTimeField(auto_now_add=True)  # Date de création de l'horaire de la séance
    date_modification = models.DateTimeField(auto_now=True)  # Date de mise à jour

    def __str__(self):
        return f"Payment {self.reference} - {self.status}"

class Reglement(models.Model):
    # Statuts de règlement
    PENDING = 'pending'
    APPROVED = 'approved'
    CANCELED = 'canceled'
    INVALID = 'invalid'

    STATUS_CHOICES = [
        (PENDING, 'En attente'),
        (APPROVED, 'Approuvé'),
        (CANCELED, 'Annulé'),
        (INVALID, 'Invalide'),
    ]

    model = models.CharField(max_length=255)  # Table liée (Accord_reglement/Accord_remboursement)
    model_id = models.IntegerField()  # ID dans le modèle lié
    debitor_account = models.CharField(max_length=255)  # Compte débiteur (-)
    creditor_account = models.CharField(max_length=255)  # Compte créditeur (+)
    amount = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))], 
        null=True, 
        blank=True
    )  # Montant
    currency = models.CharField(max_length=10)  # Devise
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)  # Statut
    transaction_date = models.DateTimeField(null=True, blank=True)  # Date de règlement
    description = models.TextField()  # Libellé du règlement

    def __str__(self):
        return f"Règlement {self.id} - {self.status}"

class Demande_paiement(models.Model):  # Demande de paiement par le prof
    # Définition des différents statuts de la séance du cours
    EN_ATTENTE = 'En attente'
    EN_COURS = 'En cours'
    REALISER = 'Réaliser'
    CONTESTER = 'Contester'
    ANNULER = 'Annuler'

    # Choix de statuts de la demande de paiement
    STATUS_CHOICES = [
        (EN_ATTENTE, 'En attente'),
        (EN_COURS, 'En cours'),
        (REALISER, 'Réaliser'),
        (CONTESTER, 'Contester'),
        (ANNULER, 'Annuler'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE) # ID user professeur
    mon_eleve = models.ForeignKey(Mes_eleves, on_delete=models.PROTECT)  # ID de l'élève inscrit dans la table Mes_eleve
    eleve = models.ForeignKey(Eleve, on_delete=models.PROTECT)  # ID de l'élève inscrit dans la table Eleve
    montant = models.FloatField()  # Montant à régler
    email = models.IntegerField(null=True)  # ID de l'email lié à la demande de paiement
    vue_le = models.DateTimeField(null=True, blank=True)  # Date à laquelle la demande a été vue par l'élève
    email_eleve = models.IntegerField(null=True)  # ID de l'email en réponse à la demande de règlement
    statut_demande = models.CharField(max_length=10, choices=STATUS_CHOICES, default=EN_ATTENTE)  # Statut de la demande de paiement
    payment_id = models.IntegerField(null=True)  # ID du modèle Payment, si null pas de paiement
    reglement = models.ForeignKey(Reglement, on_delete=models.SET_NULL, null=True, blank=True)  # Lien avec le règlement
    date_creation = models.DateTimeField(auto_now_add=True)  # Date de création de l'horaire de la séance
    date_modification = models.DateTimeField(auto_now=True)  # Date de mise à jour


class Detail_demande_paiement(models.Model):  # Demande de paiement
    demande_paiement = models.ForeignKey(Demande_paiement, on_delete=models.CASCADE)  # ID du modèle Demande_paiement
    cours = models.ForeignKey(Cours, on_delete=models.CASCADE)  # ID du modèle Cours
    prix_heure = models.FloatField()  # Prix par heure du cours défini à la date de création de la demende de règlement qui peut etre différent du prix_heure du cours actuel
    horaire = models.ForeignKey(Horaire, on_delete=models.CASCADE)  # ID du modèle Horaire


class AccordReglement(models.Model):
    # Statuts de l'accord
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    INVALID = 'invalid'
    CANCELED = 'canceled'

    STATUS_CHOICES = [
        (PENDING, 'En attente'),
        (IN_PROGRESS, 'En cours'),
        (COMPLETED, 'Réalisé'),
        (INVALID, 'Invalide'),
        (CANCELED, 'Annulé'),
    ]

    admin_user = models.ForeignKey(User, on_delete=models.CASCADE)  # Administrateur
    professeur = models.ForeignKey(Professeur, on_delete=models.PROTECT)  # Professeur lié
    total_amount = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))], 
        null=True, 
        blank=True
    )  # Montant total
    email_id = models.IntegerField(null=True, blank=True)  # Email lié
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=PENDING)  # Statut
    reglement = models.ForeignKey(Reglement, on_delete=models.SET_NULL, null=True, blank=True)  # Lien avec le règlement
    created_at = models.DateTimeField(auto_now_add=True)  # Date de création
    updated_at = models.DateTimeField(auto_now=True)  # Dernière modification
    due_date = models.DateTimeField(null=True, blank=True)  # Date d'échéanse

    def __str__(self):
        return f"Accord Règlement - Prof: {self.professeur.id}, Statut: {self.status}"

class DetailAccordReglement(models.Model):
    accord = models.ForeignKey(AccordReglement, on_delete=models.CASCADE)  # Accord lié
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)  # Paiement lié
    professor_share = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))], 
        null=True, 
        blank=True
    )  # Part du professeur
    description = models.TextField()  # Libellé

    def __str__(self):
        return f"Détail Accord Règlement - Accord ID: {self.accord.id}"


class AccordRemboursement(models.Model):
    # Statuts de l'accord
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    INVALID = 'invalid'
    CANCELED = 'canceled'

    STATUS_CHOICES = [
        (PENDING, 'En attente'),
        (IN_PROGRESS, 'En cours'),
        (COMPLETED, 'Réalisé'),
        (INVALID, 'Invalide'),
        (CANCELED, 'Annulé'),
    ]

    admin_user = models.ForeignKey(User, on_delete=models.CASCADE)  # Administrateur
    eleve = models.ForeignKey(Eleve, on_delete=models.PROTECT)  # Élève concerné
    total_amount = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))], 
        null=True, 
        blank=True
    )  # Montant total remboursé
    email_id = models.IntegerField(null=True, blank=True)  # Email lié
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=PENDING)  # Statut
    reglement = models.ForeignKey(Reglement, on_delete=models.SET_NULL, null=True, blank=True)  # Lien avec le règlement
    created_at = models.DateTimeField(auto_now_add=True)  # Date de création
    updated_at = models.DateTimeField(auto_now=True)  # Dernière modification

    def __str__(self):
        return f"Accord Remboursement - Élève: {self.eleve.id}, Statut: {self.status}"

class DetailAccordRemboursement(models.Model):
    accord = models.ForeignKey(AccordRemboursement, on_delete=models.CASCADE)  # Accord lié
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)  # Paiement lié
    refunded_amount = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))], 
        null=True, 
        blank=True
    )  # Montant remboursé
    description = models.TextField()  # Libellé

    def __str__(self):
        return f"Détail Accord Remboursement - Accord ID: {self.accord.id}"
