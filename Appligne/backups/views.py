# backups/views.py

from django.shortcuts import render

# Create your views here.
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from .utils.backup_utils import create_backup
import os
from django.core.exceptions import PermissionDenied

@staff_member_required
def create_backup_view(request):
    # Vérification des permissions spécifiques
    # if not request.user.has_perm('backups.add_databasebackup'):
    #     raise PermissionDenied

    # Vérifie que le répertoire de sauvegarde existe
    backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # Vérification de l'espace disque disponible
    def check_disk_space():
        stat = os.statvfs(settings.MEDIA_ROOT) if hasattr(os, 'statvfs') else None
        if stat:
            free_space = stat.f_frsize * stat.f_bavail
            return free_space > 1024 * 1024 * 500  # 500MB minimum
        return True  # Si on ne peut pas vérifier, on continue
    
    if not check_disk_space():
        messages.error(
            request,
            "Espace disque insuffisant pour créer une sauvegarde (500MB requis)"
        )
        return redirect(reverse('admin:backups_databasebackup_changelist'))
    
    context = {
        'title': 'Créer une nouvelle sauvegarde',
        'opts': {'app_label': 'backups'},  # Pour la navigation admin
        'media_url': settings.MEDIA_URL,
    }

    if request.method == 'POST':
        # Récupération des données du formulaire
        backup_type = request.POST.get('backup_type', 'full')
        encrypted = request.POST.get('encrypted', 'off') == 'on'
        notes = request.POST.get('notes', '')
        
        # Validation simple
        if backup_type not in ['full', 'partial']:
            messages.error(request, "Type de sauvegarde invalide")
            return render(request, 'backups/create_backup_view.html', context)
        
        try:
            # Création de la sauvegarde
            backup = create_backup(
                backup_type=backup_type,
                encrypted=encrypted,
                notes=notes
            )
            
            if backup.successful:
                messages.success(
                    request,
                    f"Sauvegarde {backup_type} créée avec succès! Taille: {backup.size}"
                )
                # Journalisation
                if hasattr(settings, 'LOGGING'):
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(
                        f"Backup created by {request.user.username}: "
                        f"{backup.name} (Type: {backup_type}, Encrypted: {encrypted})"
                    )
            else:
                messages.error(
                    request,
                    f"Erreur lors de la création de la sauvegarde: {backup.error_message}"
                )
            
            return redirect(reverse('admin:backups_databasebackup_changelist'))
        
        except Exception as e:
            messages.error(
                request,
                f"Erreur critique lors de la sauvegarde: {str(e)}"
            )
            # Journalisation de l'erreur
            if hasattr(settings, 'LOGGING'):
                import logging
                logger = logging.getLogger(__name__)
                logger.error(
                    f"Backup failed for {request.user.username}: {str(e)}",
                    exc_info=True
                )
    
    # GET request - afficher le formulaire
    return render(request, 'backups/create_backup_view.html', context)

from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from .models import DatabaseBackup
from django.utils.encoding import smart_str

@staff_member_required
def download_backup(request, backup_id):
    backup = get_object_or_404(DatabaseBackup, id=backup_id)
    
    file_path = backup.backup_file.path
    if not os.path.exists(file_path):
        raise Http404("Fichier non trouvé")

    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{smart_str(os.path.basename(file_path))}"'
        return response