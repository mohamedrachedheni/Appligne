# backups/ models.py

# Create your models here.
import os
from django.db import models
from django.conf import settings
from django.core.files.storage import FileSystemStorage

# Configuration unique du stockage
# backup_storage = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'backups'))
backup_storage = FileSystemStorage(
    location=os.path.join(settings.MEDIA_ROOT, 'backups'),
    file_permissions_mode=0o640,
    base_url='/media/backups/'  # Ajoutez cette ligne
)


class DatabaseBackup(models.Model):
    # Constantes représentant les types de sauvegarde possibles
    BACKUP_TYPE_FULL = 'full'
    BACKUP_TYPE_PARTIAL = 'partial'
    
    # Liste des choix possibles pour le type de sauvegarde
    BACKUP_TYPE_CHOICES = [
        (BACKUP_TYPE_FULL, 'Sauvegarde complète'),
        (BACKUP_TYPE_PARTIAL, 'Sauvegarde partielle'),
    ]

    # Nom de la sauvegarde
    name = models.CharField(max_length=255, verbose_name="Nom de la sauvegarde")

    # Type de sauvegarde (complète ou partielle)
    backup_type = models.CharField(
        max_length=10,
        choices=BACKUP_TYPE_CHOICES,
        default=BACKUP_TYPE_FULL,
        verbose_name="Type de sauvegarde"
    )

    # Indique si la sauvegarde est chiffrée
    encrypted = models.BooleanField(default=False, verbose_name="Chiffré")

    # Fichier de sauvegarde, stocké dans le dossier défini par backup_storage
    backup_file = models.FileField(
        storage=backup_storage,
        upload_to='', # Plus de sous-dossier
        verbose_name="Fichier de sauvegarde"
    )

    # Taille du fichier de sauvegarde (en B, KB, MB, etc.)
    size = models.CharField(max_length=20, blank=True, verbose_name="Taille")

    # Notes facultatives associées à la sauvegarde
    notes = models.TextField(blank=True, verbose_name="Notes")

    # Ajoute ce champ pour distinguer une sauvegarde générée manuellement via admin
    auto_generated = models.BooleanField(default=False)

    # Date de création de la sauvegarde (remplie automatiquement à la création)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")

    # Statut indiquant si la sauvegarde a réussi
    successful = models.BooleanField(default=False, verbose_name="Réussie")

    # Message d'erreur si la sauvegarde a échoué
    error_message = models.TextField(blank=True, verbose_name="Message d'erreur")

    class Meta:
        verbose_name = "Sauvegarde de base de données"
        verbose_name_plural = "Sauvegardes de base de données"
        ordering = ['-created_at']  # Trie les sauvegardes par date décroissante

    def __str__(self):
        # Représentation lisible de l'objet dans l'interface admin
        return f"{self.name} ({self.get_backup_type_display()})"

    def save(self, *args, **kwargs):
        # Lors de la sauvegarde de l'objet, met à jour la taille du fichier si présente
        if self.backup_file:
            self.size = self.get_file_size()
        super().save(*args, **kwargs)

    def get_file_size(self):
        # Calcule la taille lisible du fichier (en B, KB ou MB)
        try:
            size_bytes = self.backup_file.size
            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.2f} KB"
            else:
                return f"{size_bytes / (1024 * 1024):.2f} MB"
        except (ValueError, OSError):
            # En cas d'erreur de lecture du fichier
            return "N/A"

    def delete(self, *args, **kwargs):
        # Supprime d'abord le fichier de sauvegarde du système de fichiers,
        # puis supprime l'objet de la base de données
        if self.backup_file:
            self.backup_file.delete()
        super().delete(*args, **kwargs)
