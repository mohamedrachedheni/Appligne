# backups/utils/back_utils.py

import os
import subprocess
import tempfile
from datetime import datetime
from django.conf import settings
from django.db import connection
from django.core.files import File
from cryptography.fernet import Fernet
from backups.models import DatabaseBackup
import logging

logger = logging.getLogger(__name__)

def generate_backup_filename(backup_type):
    """Génère un nom de fichier unique pour la sauvegarde"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"backup_{backup_type}_{timestamp}.sql"

def get_db_credentials():
    """Récupère les credentials de la base de données"""
    return connection.settings_dict



def create_backup(backup_type, encrypted=False, notes=""):
    """Crée une sauvegarde de la base de données sans duplication"""
    credentials = get_db_credentials()
    backup_filename = generate_backup_filename(backup_type)
    backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
    
    # Chemin final unique
    final_path = os.path.join(backup_dir, backup_filename)
    
    try:
        os.makedirs(backup_dir, exist_ok=True)
        
        # Construction de la commande mysqldump
        cmd = [
            settings.MYSQL_PATHS['mysqldump'],
            f"--user={credentials['USER']}",
            f"--password={credentials['PASSWORD']}",
            f"--host={credentials['HOST']}",
            f"--port={credentials['PORT']}",
            "--single-transaction",
            "--routines",
            "--triggers",
            credentials['NAME']
        ]
        
        if backup_type == 'partial':
            cmd.extend([
                f"--ignore-table={credentials['NAME']}.django_session",
                f"--ignore-table={credentials['NAME']}.django_admin_log"
            ])
        
        logger.info(f"Creating backup with command: {' '.join(cmd)}")
        
        # Écriture directe dans le fichier final
        with open(final_path, 'w') as f:
            process = subprocess.Popen(
                cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                shell=True
            )
            _, stderr = process.communicate()
            
            if process.returncode != 0:
                raise subprocess.CalledProcessError(
                    process.returncode,
                    cmd,
                    stderr
                )
        
        # Vérification du fichier
        if os.path.getsize(final_path) == 0:
            raise Exception("Backup file is empty - no data was dumped")
        
        # Gestion du chiffrement
        if encrypted:
            with open(final_path, 'rb') as f:
                data = f.read()
            
            key = Fernet.generate_key()
            cipher = Fernet(key)
            encrypted_data = cipher.encrypt(data)
            
            encrypted_path = final_path + '.enc'
            with open(encrypted_path, 'wb') as f:
                f.write(encrypted_data)
                f.write(b'\nKEY:' + key)
            
            os.remove(final_path)
            final_path = encrypted_path
        
        # Création de l'objet DatabaseBackup sans recréer le fichier
        backup = DatabaseBackup(
            name=backup_filename.replace('.sql', ''),
            backup_type=backup_type,
            encrypted=encrypted,
            notes=notes,
            successful=True
        )
        
        # Associe le fichier existant sans le recréer
        """
        backup.backup_file.save(...) enregistre le fichier dans le champ FileField correctement.
        File(f) donne accès à la méthode .size, qui sera utilisée par get_file_size() dans save().
        Le save=False permet de retarder la sauvegarde du modèle jusqu’au backup.save() final, ce qui est plus propre.
        """
        with open(final_path, 'rb') as f:
            backup.backup_file.save(os.path.basename(final_path), File(f), save=False)

        backup.save()
        
        return backup
        
    except Exception as e:
        logger.error(f"Backup creation failed: {str(e)}", exc_info=True)
        
        # Nettoyage en cas d'erreur
        if 'final_path' in locals() and os.path.exists(final_path):
            os.remove(final_path)
        
        # Création d'un objet d'erreur
        backup = DatabaseBackup(
            name=backup_filename.replace('.sql', ''),
            backup_type=backup_type,
            encrypted=encrypted,
            notes=notes,
            successful=False,
            error_message=str(e),
            auto_generated = True
        )
        backup.save()
        return backup




def restore_backup(backup, request):
    """Restaure une sauvegarde de la base de données"""
    credentials = get_db_credentials()
    backup_path = backup.backup_file.path
    temp_path = None
    
    try:
        # Décryptage si nécessaire
        if backup.encrypted:
            with open(backup_path, 'rb') as f:
                file_content = f.read()
            
            # Séparation des données chiffrées et de la clé
            if b'KEY:' not in file_content:
                raise ValueError("Format de fichier chiffré invalide - marqueur KEY: manquant")
            
            encrypted_data, key = file_content.split(b'KEY:')
            cipher = Fernet(key.strip())
            
            try:
                decrypted_data = cipher.decrypt(encrypted_data)
            except Exception as e:
                raise ValueError(f"Échec du déchiffrement: {str(e)}")
            
            # Création d'un fichier temporaire
            temp_path = tempfile.mktemp(suffix='.sql')
            with open(temp_path, 'wb') as f:
                f.write(decrypted_data)
            
            backup_path = temp_path
        
        # Vérification que le fichier de restauration existe
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Fichier de restauration {backup_path} introuvable")
        
        # Construction de la commande mysql
        cmd = [
            settings.MYSQL_PATHS['mysql'],
            f"--user={credentials['USER']}",
            f"--password={credentials['PASSWORD']}",
            f"--host={credentials['HOST']}",
            f"--port={credentials['PORT']}",
            credentials['NAME']
        ]
        
        logger.info(f"Restoring backup with command: {' '.join(cmd)}")
        
        # Exécution de la commande
        with open(backup_path, 'rb') as f:  # Lecture en mode binaire pour compatibilité
            process = subprocess.Popen(
                cmd,
                stdin=f,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                shell=True
            )
            _, stderr = process.communicate()
            
            if process.returncode != 0:
                raise subprocess.CalledProcessError(
                    process.returncode,
                    cmd,
                    stderr
                )
        
        return True, "Restauration réussie"
    
    except Exception as e:
        logger.error(f"Restore failed: {str(e)}", exc_info=True)
        return False, str(e)
    
    finally:
        # Nettoyage du fichier temporaire dans tous les cas
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                logger.warning(f"Échec de la suppression du fichier temporaire: {str(e)}")


