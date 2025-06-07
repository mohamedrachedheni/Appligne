# ackups/admin.py

"""
Interface complète pour créer, télécharger, restaurer et 
supprimer des sauvegardes depuis l’interface Django Admin.
Champs personnalisés, actions de masse, boutons d'action,
et intégration des vues dans l’admin.
Utilisation des fonctions utilitaires create_backup et                       
restore_backup pour la logique métier.
"""

from django.contrib import admin
from django.urls import path, reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseRedirect, FileResponse, Http404
from django.utils.html import format_html
from django.conf import settings
from .models import DatabaseBackup
from .utils.backup_utils import create_backup, restore_backup
import os
from django.utils.timezone import now


@admin.register(DatabaseBackup)
class DatabaseBackupAdmin(admin.ModelAdmin):
    list_display = ('name', 'backup_type', 'encrypted', 'size', 'created_at', 'successful', 'download_link')
    list_filter = ('backup_type', 'created_at', 'successful', 'encrypted')
    search_fields = ('name', 'notes', 'error_message')
    readonly_fields = ('size', 'created_at', 'successful', 'error_message', 'backup_file')
    actions = ['delete_selected_backups']

    fieldsets = (
        (None, {
            'fields': ('name', 'backup_type', 'encrypted', 'notes')
        }),
        ('Informations', {
            'fields': ('backup_file', 'size', 'created_at', 'successful', 'error_message'),
            'classes': ('collapse',),
        }),
    )
    """
    Cela garantira que le clic sur "Télécharger" appelle 
    la vue personnalisée download_backup, qui gère la réponse via FileResponse.
    """
    def download_link(self, obj):
        if obj.backup_file:
            return format_html(
                '<a href="{}">Télécharger</a> | '
                '<a href="{}">Restaurer</a>',
                reverse('admin:backups_databasebackup_download', args=[obj.pk]),
                reverse('admin:backups_databasebackup_restore', args=[obj.pk])
            )
        return "-"


    download_link.short_description = "Actions"

    def delete_selected_backups(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"{count} sauvegardes ont été supprimées avec succès.")
    delete_selected_backups.short_description = "Supprimer les sauvegardes sélectionnées"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:backup_id>/download/',
                self.admin_site.admin_view(self.download_backup),
                name='backups_databasebackup_download'
            ),
            path(
                '<int:backup_id>/restore/',
                self.admin_site.admin_view(self.restore_backup_view),
                name='backups_databasebackup_restore'
            ),
            path(
                'create-backup/',
                self.admin_site.admin_view(self.create_backup_view),
                name='create_backup'
            ),
        ]
        return custom_urls + urls


    def download_backup(self, request, backup_id):
        backup = get_object_or_404(DatabaseBackup, pk=backup_id)
        if backup.backup_file and os.path.exists(backup.backup_file.path):
            response = FileResponse(backup.backup_file.open('rb'), as_attachment=True)
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(backup.backup_file.name)}"'
            return response
        messages.error(request, "Fichier de sauvegarde introuvable.")
        return HttpResponseRedirect(reverse('admin:backups_databasebackup_changelist'))

    def restore_backup_view(self, request, backup_id):
        backup = get_object_or_404(DatabaseBackup, pk=backup_id)
        
        if request.method == 'POST':
            if 'confirm' in request.POST:
                success, message = restore_backup(backup, request)
                if success:
                    messages.success(request, message)
                else:
                    messages.error(request, f"Erreur lors de la restauration: {message}")
                return HttpResponseRedirect(reverse('admin:backups_databasebackup_changelist'))
            else:
                messages.error(request, "Vous devez confirmer la restauration")
                return HttpResponseRedirect(reverse('admin:backups_databasebackup_restore', args=[backup_id]))

        # Afficher la page de confirmation
        return render(request, 'backups/confirm_restore.html', {
            'backup': backup,
            'opts': self.model._meta,
            'title': 'Confirmer la restauration'
        })

    def create_backup_view(self, request):
        if request.method == 'POST':
            backup_type = request.POST.get('backup_type', 'full')
            encrypted = request.POST.get('encrypted', 'off') == 'on'
            notes = request.POST.get('notes', '')

            backup = create_backup(backup_type, encrypted, notes)

            if backup.successful:
                messages.success(request, "Sauvegarde créée avec succès!")
            else:
                messages.error(request, f"Erreur lors de la sauvegarde: {backup.error_message}")

            return HttpResponseRedirect(reverse('admin:backups_databasebackup_changelist'))

        return render(request, 'admin/backups/create_backup.html', {
            'opts': self.model._meta,
            'title': 'Créer une nouvelle sauvegarde'
        })

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_create_button'] = True
        return super().changelist_view(request, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        if obj.auto_generated:
            super().save_model(request, obj, form, change)
            return

        today_str = now().strftime('%Y-%m-%d')
        if DatabaseBackup.objects.filter(name__icontains=today_str).exists():
            messages.error(request, f"Une sauvegarde pour le {today_str} existe déjà.")
            return

        backup = create_backup(
            backup_type=obj.backup_type,
            encrypted=obj.encrypted,
            notes=obj.notes
        )

        if backup.successful:
            messages.success(request, f"Sauvegarde '{backup.name}' créée avec succès.")
        else:
            messages.error(request, f"Erreur lors de la sauvegarde : {backup.error_message}")
