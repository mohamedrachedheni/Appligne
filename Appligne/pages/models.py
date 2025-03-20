from django.db import models
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
        ('en_cours', 'En cours de traitement'),
        ('resolue', 'Résolue'),
        ('fermee', 'Fermée'),
    ]

    PRIORITE_CHOICES = [
        ('basse', 'Basse'),
        ('moyenne', 'Moyenne'),
        ('haute', 'Haute'),
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
        max_length=10, choices=PRIORITE_CHOICES, default='moyenne', verbose_name="Priorité"
    )
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_mise_a_jour = models.DateTimeField(auto_now=True, verbose_name="Date de mise à jour")

    class Meta:
        verbose_name = "Réclamation"
        verbose_name_plural = "Réclamations"

    def __str__(self):
        categorie_nom = self.categorie.nom if self.categorie else "Sans catégorie"
        return f"{categorie_nom} - {self.get_statut_display()}"

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
    VALID_EXTENSIONS = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png']
    MAX_FILE_SIZE = 5  # En MB

    reclamation = models.ForeignKey(
        Reclamation,
        on_delete=models.SET_NULL,  # Modification pour éviter la suppression en cascade
        null=True, blank=True,
        related_name="pieces_jointes",
        verbose_name="Réclamation"
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


