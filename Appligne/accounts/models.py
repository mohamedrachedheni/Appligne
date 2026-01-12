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
from django.utils import timezone  
from pages.models import Reclamation



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
    date_naissance = models.DateField(null=True, blank=True)
    adresse = models.CharField(max_length=255, blank=True, null=True)
    photo = models.ImageField(upload_to='photos/%y/%m/%d/', blank=True, null=True)
    # --- Champs pour Stripe Connect ---
    stripe_account_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        help_text="ID du compte Stripe Connect Express (ex: acct_1234ABCD)"
    )
    stripe_onboarding_complete = models.BooleanField(
        default=False,
        help_text="Indique si le professeur a terminé l'onboarding Stripe Express"
    )

    

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
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True) # ID de l'expéditeur (eleve, professeur, admin, [visiteur si null ou blank])
    date_telechargement = models.DateTimeField(default=date.today)
    email_telecharge = models.CharField(max_length=255, null=True, blank=True)  # l'adresse email de l'expéditeur
    sujet = models.CharField(max_length=255, null=True, blank=True)
    text_email = models.TextField(
        null=True, 
        blank=True,
        db_collation="utf8mb4_unicode_ci",
        )
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
    prix_heure_prof = models.DecimalField(
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
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE)  # Relation un à plusieurs avec les élèves ( de plus à enlever)
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

    # Choix de statuts de la séance
    STATUS_CHOICES = [
        (EN_ATTENTE, 'En attente'),
        (REALISER, 'Réaliser'),
    ]
    cours = models.ForeignKey(Cours, on_delete=models.CASCADE)  # ID du modèle Cours
    date_cours = models.DateField(null=True)  # Date du cours
    heure_debut = models.TimeField(null=True)  # Heure de début du cours
    heure_fin = models.TimeField(null=True)  # Heure de fin du cours
    duree = models.FloatField(null=True, default=1)  # Durée de la séance
    contenu = models.CharField(max_length=255)  # Contenu du cours
    statut_cours = models.CharField(max_length=10, choices=STATUS_CHOICES, default=EN_ATTENTE)  # Statut de la séance
    payment_id = models.IntegerField(null=True, blank=True)  # ID du modèle Payment, si null pas de paiement réalisé
    demande_paiement_id = models.IntegerField(null=True, blank=True)  # ID du modèle Demande_paiement, si null pas de demande de paiementnon annulée
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


    

class Demande_paiement(models.Model):  # Demande de paiement par le prof
    # Définition des différents statuts de la demande de paiement
    EN_ATTENTE = 'En attente'
    EN_COURS = 'En cours'
    REALISER = 'Réaliser'
    ANNULER = 'Annuler'

    # Choix de statuts de la demande de paiement
    STATUS_CHOICES = [
        (EN_ATTENTE, 'En attente'), # Enregistré par le prof et en attente de la confirmation de l'élève
        (EN_COURS, 'En cours'), # L'élève a confgirmé la demande par un paiement mais la passerelle de paiement est en cours de confirmation(c'est le temps nécessaire pour que la passerelle confirme le paiement)
        (REALISER, 'Réaliser'), # la passerelle a confirmé le paiement
        (ANNULER, 'Annuler'), # Le professeur a annulé la demande
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE) # ID user professeur
    mon_eleve = models.ForeignKey(Mes_eleves, on_delete=models.PROTECT)  # ID de l'élève inscrit dans la table Mes_eleve
    eleve = models.ForeignKey(Eleve, on_delete=models.PROTECT)  # ID de l'élève inscrit dans la table Eleve (en plus à enlever)
    montant = models.FloatField()  # Montant à régler
    email = models.IntegerField(null=True)  # ID de l'email lié à la demande de paiement
    vue_le = models.DateTimeField(null=True, blank=True)  # Date à laquelle la demande a été vue par l'élève
    email_eleve = models.IntegerField(null=True)  # ID de l'email en réponse à la demande de règlement (à enlever car la réponse de l'élève est liée à l'émail du professeur dans Email_telecharge)
    statut_demande = models.CharField(max_length=10, choices=STATUS_CHOICES, default=EN_ATTENTE)  # Statut de la demande de paiement
    date_creation = models.DateTimeField(auto_now_add=True)  # Date de création de l'horaire de la séance
    date_modification = models.DateTimeField(auto_now=True)  # Date de mise à jour

    # champs ásupprimer
    # reclamation = models.ForeignKey(Reclamation, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Réclamation") # (a supprimer)
    accord_reglement_id = models.IntegerField(null=True)  # ID de l'objet dans le modèle AccordReglement (sans tenir compte du statut) pas obligatoire car pour chaque demande de paiement correspond un seul paiement(a supprimer)
    reglement_realise = models.BooleanField(default=False)  # AccordReglement statut Réalisé ou non pas obligatoire car pour chaque demande de paiement correspond un seul paiement (a supprimer)
    url_paiement = models.CharField(max_length=255, null=True, blank=True)  # lien fourni par la passerelle de paiement (a supprimer)
    date_expiration = models.DateTimeField(null=True)  # Date d'expiration du lien de paiement (a supprimer)

class Detail_demande_paiement(models.Model):  # Demande de paiement
    demande_paiement = models.ForeignKey(Demande_paiement, on_delete=models.CASCADE)  # ID du modèle Demande_paiement
    cours = models.ForeignKey(Cours, on_delete=models.CASCADE)  # ID du modèle Cours
    prix_heure = models.FloatField()  # Prix par heure du cours pour le prof à la date de création du cours
    horaire = models.ForeignKey(Horaire, on_delete=models.CASCADE)  # ID du modèle Horaire (à modifier one to one)

class Payment(models.Model):
    # Statuts de paiement
    PENDING = 'En attente' # "pending"
    APPROVED = 'Approuvé' # "succeeded"
    CANCELED = 'Annulé' # 'canceled'
    INVALID = 'Invalide' ####### "failed" à supprimer########
    REFUNDED = 'Remboursé' # "refunded" 

    STATUS_CHOICES = [
        (PENDING, 'En attente'), # ('created', 'Créé'),
        (APPROVED, 'Approuvé'), # ('succeeded', 'Réussi'),
        (CANCELED, 'Annulé'), # ('canceled', 'Annulé'), à SUPPRIMER
        (INVALID, 'Invalide'), # (FAILED, 'Échoué'),
        (REFUNDED, "Remboursé"),
    ]

    # 🔗 Relations
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name="payments", null=True, blank=True)
    professeur = models.ForeignKey(Professeur, on_delete=models.CASCADE, related_name="payments", null=True, blank=True)
    
    invoice = models.OneToOneField(
        'cart.Invoice',   # ✅ Référence par chaîne — évite l’import circulaire
        on_delete=models.CASCADE,
        related_name="payments",
        null=True,
        blank=True
    )

    amount = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))], # 
        help_text="Montant total payé par l'élève (€)",
        null=True, 
        blank=True
    )  # Montant du paiement (round(session.amount_total/100,2))
    currency = models.CharField(max_length=10, null=True, blank=True)  # Devise (session.currency)

    # 🕐 Suivi et statut
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)  # Statut
    reference = models.CharField(max_length=255, blank=True, null=True)  # stripe_payment_intent_id: ID 'PaymentIntent' que Stripe crée automatiquement lorsqu’un paiement est initié via une session de Checkout (session.payment_intent)
    date_creation = models.DateTimeField(auto_now_add=True)  # Date de disponibilité
    date_modification = models.DateTimeField(auto_now=True)  # Date de mise à jour 

    # propre à la logique d'enregistrement
    reclamation = models.ForeignKey(Reclamation, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Réclamation")
    accord_reglement_id = models.IntegerField(null=True, blank=True)  # ID de l'objet dans le modèle AccordReglement
    reglement_realise = models.BooleanField(default=False)  # pour différencier les paiements dont l'accord de règlement est réalisé ou non 
    accord_remboursement_id = models.IntegerField(null=True, blank=True)  # ID de l'objet dans le modèle AccordReglement
    remboursement_realise = models.BooleanField(default=False)  # pour différencier les paiements dont l'accord de règlement est réalisé ou non 
    
    # champs à supprimer
    demande_paiement = models.OneToOneField(Demande_paiement, on_delete=models.CASCADE, related_name="payments", null=True, blank=True) # à supprimer
    model = models.CharField(max_length=255, blank=True, null=True)  # Model liée au paiement (ex: Demande_paiement/Règlement / Rembourcement) (à supprimer)
    model_id = models.IntegerField( blank=True, null=True)  # ID de l'objet dans le modèle lié (à supprimer)
    # 📎 Informations Stripe
    slug = models.CharField(max_length=255, blank=True, null=True)  # à garder pour simplifier certain recherche à améliorer(Pro114;Ele325;)(à supprimer)
    payment_body = models.JSONField(null=True, blank=True) #  (les données JSON envoyées par l'API Stripe et non pas par le Webhook) ( à supprimer)
    stripe_charge_id = models.CharField(max_length=255, blank=True, null=True) # (à supprimer ça existe déjà dans Invoice)
    language = models.CharField(max_length=10, null=True, blank=True)  # Langue utilisée (à supprimer non utilisé)
    payment_date = models.DateTimeField(null=True, blank=True)  # Date de paiement de l'élève ( à supprimer / existe dans invoice.paid_at)
    
    def mark_succeeded(self):
        """✅ Marque ce paiement comme réussi."""
        self.status = "succeeded"
        self.payment_date = timezone.now()
        self.save()

    def mark_failed(self, reason=None):
        """❌ Marque ce paiement comme échoué."""
        self.status = "failed"
        self.description = reason or self.description
        self.save()

    def mark_refunded(self):
        """↩️ Marque ce paiement comme remboursé."""
        self.status = "refunded"
        self.save()

    def __str__(self):
        return f"Paiement {self.id} - {self.eleve} -> {self.professeur} ({self.status})"
    

class Transfer(models.Model):
    """
    📤 Transfert de la part du professeur depuis la plateforme vers son compte connecté.
    """
    # Statuts de transfer
    PENDING = 'pending'
    APPROVED = 'succeeded'
    FAILED = 'failed'
    REVERSED = 'reversed'

    STATUS_CHOICES = [
        (PENDING, "En attente"),
        (APPROVED, "Réussi"),
        (FAILED, "Échoué"),
        (REVERSED, "Annulé / Remboursé"),
    ]

    # Facture
    invoice_transfert = models.OneToOneField(
        'cart.InvoiceTransfert',   # ✅ Référence par chaîne — évite l’import circulaire
        on_delete=models.CASCADE,
        related_name="transfer",
        help_text="Invoice associé à ce transfert",
        null=True, 
        blank=True,
    )

    # destinataire du transfert
    user_transfer_to = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True) # à réviser les view liées

    # Informations Stripe
    stripe_transfer_id = models.CharField(
        max_length=255, unique=True,null=True, 
        blank=True, help_text="ID du transfert Stripe"
    )

    # Statut
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=PENDING, help_text="État du transfert"
    )

    # Montants
    amount = models.DecimalField(
        max_digits=10, decimal_places=2,null=True, 
        blank=True, help_text="Montant transféré global"
    )
    currency = models.CharField(max_length=10, default="eur")

    # montant net
    montant_net = models.DecimalField(
        max_digits=10, decimal_places=2,null=True, 
        blank=True, help_text="Montant net transféré au professeur"
    )

    # Frais Stripe
    frais = models.DecimalField(
        max_digits=10, decimal_places=2,null=True, 
        blank=True, help_text="Montant transféré au professeur"
    )

    # Relation vers Payment à (à supprimer)
    # payment = models.OneToOneField(Payment,
    #     on_delete=models.CASCADE,
    #     related_name="transfer",
    #     help_text="Paiement associé à ce transfert",
    # ) 

    def __str__(self):
        return f"📤 Transfer #{self.id} - {self.amount} {self.currency} - {self.status}"


class AccordReglement(models.Model):
    # Statuts de l'accord à changer dans le cas de plusieur payment liés
    PENDING = 'En attente'# l'admin n'a pas encore initialié le transfert
    IN_PROGRESS = 'En cours' # si le transfert est en cours
    COMPLETED = 'Réalisé' # si le transfert est encaisser
    INVALID = 'Invalide' # transfert échouer
    CANCELED = 'Annulé' # si l'admin à décider d'annuler l'accord de règlement

    STATUS_CHOICES = [
        (PENDING, 'En attente'), # état initial à la création de l'accord sans initialiser le transfert
        (IN_PROGRESS, 'En cours'), # transfert déclancher
        (COMPLETED, 'Réalisé'), # transfert encaisser
        (INVALID, 'Invalide'), # transfert echouer
        (CANCELED, 'Annulé'), # annulation par l'admin
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
    
    created_at = models.DateTimeField(auto_now_add=True)  # Date de création
    updated_at = models.DateTimeField(auto_now=True)  # Dernière modification
    due_date = models.DateTimeField(null=True, blank=True)  # Date d'échéanse pour passer au règlement effectif
    # payment_id = models.IntegerField(null=True, blank=True)  # erreur de structure BD à supprimer
    transfere_id = models.CharField(max_length=255, null=True, blank=True) # ID de l'opération fourni par la banque (à supprimer)
    transfer = models.OneToOneField(Transfer,
        on_delete=models.SET_NULL,
        help_text="AccordReglement associé à ce transfert",
        null=True, 
        blank=True,
    )
    date_trensfere = models.DateTimeField(null=True, blank=True)  # Date du transfert de l'argent (à supprimer)

    def __str__(self):
        return f"Accord Règlement - Prof: {self.professeur.id}, Statut: {self.status}"

class DetailAccordReglement(models.Model):
    accord = models.ForeignKey(AccordReglement, on_delete=models.CASCADE)  # Accord lié
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)  # Paiement lié à changer un à un (models.OneToOneField)
    professor_share = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))], 
        null=True, 
        blank=True
    )  # Part du professeur
    stripe_transfer_id = models.IntegerField(null=True, blank=True) # lié au Transfer ( à supprimer)
    description = models.TextField(null=True, blank=True)  # Libellé

    def __str__(self):
        return f"Détail Accord Règlement - Accord ID: {self.accord.id}"

class AccordRemboursement(models.Model):
    # Statuts de l'accord
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    INVALID = 'invalid' # à supprimer
    CANCELED = 'canceled'

    STATUS_CHOICES = [
        (PENDING, 'En attente'),
        (IN_PROGRESS, 'En cours'),
        (COMPLETED, 'Réalisé'),
        (INVALID, 'Invalide'), # à supprimer
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
    transfere_id = models.CharField(max_length=255, null=True, blank=True) # ID de l'opération fourni par la banque (à supprimer)
    date_trensfere = models.DateTimeField(null=True, blank=True)  # Date du transfert de l'argent (à supprimer)
    created_at = models.DateTimeField(auto_now_add=True)  # Date de création
    updated_at = models.DateTimeField(auto_now=True)  # Dernière modification
    due_date = models.DateTimeField(null=True, blank=True)  # Date d'échéanse pour passer au règlement effectif

    def __str__(self):
        return f"Accord Remboursement - Élève: {self.eleve.id}, Statut: {self.status}"

class DetailAccordRemboursement(models.Model):
    accord = models.ForeignKey(AccordRemboursement, on_delete=models.CASCADE,  related_name="details")  # Accord lié
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)  # Paiement lié
    refunded_amount = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))], 
        null=True, 
        blank=True
    )  # Montant remboursé
    description = models.TextField(null=True, blank=True)  # Libellé

    def __str__(self):
        return f"Détail Accord Remboursement - Accord ID: {self.accord.id}"


class RefundPayment(models.Model):
    """
    🔄 Remboursement (total ou partiel) d'un paiement vers l'élève.
    Peut être déclenché automatiquement (litige) ou manuellement.
    """
    # Statuts de RefundPayment
    PENDING = 'pending'
    APPROVED = 'succeeded'
    FAILED = 'failed'

    STATUS_CHOICES = [
        (PENDING, 'En attente'),
        (APPROVED, 'Réussi'),
        (FAILED, 'Échoué'),
    ]

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255, null=True, blank=True)
    stripe_refund_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Refund #{self.id} - Payment {self.payment.id} ({self.status})"

class WebhookEvent(models.Model):
    event_id = models.CharField(max_length=255, unique=True)
    type = models.CharField(max_length=100, blank=True, null=True)
    payload = models.JSONField(blank=True, null=True)
    received_at = models.DateTimeField(auto_now_add=True)

    handle_log = models.TextField(
        blank=True,
        null=True,
        db_collation="utf8mb4_unicode_ci",
        help_text="Logs détaillés du traitement du webhook (succès, erreurs, actions réalisées)."
    )

    # 🆕 Nouveau champ : traitement achevé ou interrompu
    is_processed = models.BooleanField(default=False, help_text="Indique si l’événement a été reçu et traité.")
    is_fully_completed = models.BooleanField(default=False, help_text="Indique si le traitement du webhook est totalement achevé sans interruption.")

    def __str__(self):
        return f"{self.type} ({self.event_id})"



class StripePayout(models.Model):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    PAID = "paid"
    FAILED = "failed"

    STATUS_CHOICES = [
        (PENDING, "En attente"),
        (IN_TRANSIT, "En transit"),
        (PAID, "Payé"),
        (FAILED, "Échoué"),
    ]

    stripe_id = models.CharField(max_length=100, unique=True)
    amount = models.IntegerField()  
    currency = models.CharField(max_length=10)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    arrival_date = models.DateTimeField(null=True, blank=True)
    destination = models.CharField(max_length=100, null=True, blank=True)

    # Facture
    invoice_transfert = models.OneToOneField(
        'cart.InvoiceTransfert',   # ✅ Référence par chaîne — évite l’import circulaire
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payout {self.stripe_id} - {self.status}"
