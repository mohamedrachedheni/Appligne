from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator
from django.utils.deconstruct import deconstructible
from django.core.exceptions import ValidationError

User = get_user_model()

class ReclamationCategorie(models.Model):
    nom = models.CharField(max_length=255, unique=True, verbose_name="Nom de la catégorie")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    ordre = models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage")

    class Meta:
        verbose_name = "Catégorie de réclamation"
        verbose_name_plural = "Catégories de réclamations"
        ordering = ['ordre', 'nom']

    def __str__(self):
        return self.nom

class Reclamation(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('en_cours', 'En cours'),
        ('resolue', 'Résolue'),
        ('fermee', 'Fermée'),
    ]

    PRIORITE_CHOICES = [
        ('priorite_1', 'Basse'),
        ('priorite_2', 'Moyenne'),
        ('priorite_3', 'Haute'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reclamations", verbose_name="Utilisateur"
    )
    categorie = models.ForeignKey(
        ReclamationCategorie, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Catégorie"
    )
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default='en_attente', verbose_name="Statut"
    )
    priorite = models.CharField(
        max_length=10, choices=PRIORITE_CHOICES, default='priorite_2', verbose_name="Priorité"
    )
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_mise_a_jour = models.DateTimeField(auto_now=True, verbose_name="Date de mise à jour")

    class Meta:
        verbose_name = "Réclamation"
        verbose_name_plural = "Réclamations"

    def __str__(self):
        categorie_nom = self.categorie.nom if self.categorie else "Sans catégorie"
        return f"{categorie_nom} - {self.get_statut_display()}"



class MessageReclamation(models.Model):
    reclamation = models.ForeignKey(
        Reclamation, on_delete=models.SET_NULL, null=True, blank=True, related_name="messages", verbose_name="Réclamation"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name="Utilisateur"
    )
    titre = models.CharField(max_length=255, verbose_name="Titre")
    message = models.TextField(verbose_name="Message")
    lu = models.BooleanField(default=False, verbose_name="Message lu")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    class Meta:
        verbose_name = "Message de réclamation"
        verbose_name_plural = "Messages de réclamations"

    def __str__(self):
        return f"{self.titre} - {self.reclamation}"

@deconstructible
class FileSizeValidator:
    def __init__(self, max_size_mb):
        self.max_size_mb = max_size_mb
        self.max_size = max_size_mb * 1024 * 1024  # Conversion en bytes

    def __call__(self, value):
        if value.size > self.max_size:
            raise ValidationError(
                f"La taille du fichier ne doit pas dépasser {self.max_size_mb} Mo"
            )

class PieceJointeReclamation(models.Model):
    VALID_EXTENSIONS = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'bmp', 'webp', 'raw', 'psd', 'ai', 'exif', 'jfif', 'jpe', 'heif', 'heic']
    MAX_FILE_SIZE = 5  # En MB

    message_reclamation = models.ForeignKey(
        MessageReclamation,
        on_delete=models.SET_NULL,  # Modification pour éviter la suppression en cascade
        null=True, blank=True,
        related_name="pieces_jointes",
        verbose_name="Message réclamation"
    )
    fichier = models.FileField(
        upload_to="reclamations/pieces_jointes/%Y/%m/%d/",
        verbose_name="Fichier",
        validators=[
            FileExtensionValidator(allowed_extensions=VALID_EXTENSIONS),
            FileSizeValidator(MAX_FILE_SIZE)
        ]
    )
    date_ajout = models.DateTimeField(auto_now_add=True, verbose_name="Date d'ajout")

    class Meta:
        verbose_name = "Pièce jointe"
        verbose_name_plural = "Pièces jointes"
        ordering = ['-date_ajout']

    def __str__(self):
        return f"{self.fichier.name}"



class FAQ(models.Model):
    class Role(models.TextChoices):
        VISITEUR = 'visiteur', 'Visiteur'
        ELEVE = 'eleve', 'Élève'
        PROF = 'prof', 'Professeur'
        STAFF = 'staff', 'Staff'
        TOUS = 'tous', 'Tous'  # Affiché pour tous

    question = models.CharField(
        max_length=300,
        verbose_name="Question"
    )
    reponse = models.TextField(
        verbose_name="Réponse"
    )
    public_cible = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.TOUS,
        verbose_name="Public cible"
    )
    ordre = models.PositiveIntegerField(
        default=0,
        help_text="Définit l'ordre d'affichage"
    )
    actif = models.BooleanField(
        default=True,
        verbose_name="Est actif",
        help_text="Détermine si cette FAQ est visible"
    )

    class Meta:
        ordering = ['ordre']
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return f"[{self.get_public_cible_display()}] {self.question}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    email_confirmed = models.BooleanField(default=False)
    email_confirmation_token = models.CharField(max_length=100, blank=True, null=True)
    password_reset_token = models.CharField(max_length=100, blank=True, null=True)


