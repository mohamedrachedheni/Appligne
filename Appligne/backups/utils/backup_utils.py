# backups/utils/back_utils.py

import os
import subprocess
import tempfile
from datetime import datetime
from django.conf import settings # adapter la config MYSQL_PATHS selon l’OS (Windows, PythonAnywhere (Linux))
from django.db import connection
# from django.core.files import File
from cryptography.fernet import Fernet
from backups.models import DatabaseBackup
import logging
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


def generate_backup_filename(backup_type):
    """Génère un nom de fichier unique pour la sauvegarde"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"backup_{backup_type}_{timestamp}.sql"

def get_db_credentials():
    """Récupère les credentials de la base de données"""
    return connection.settings_dict


def create_backup(backup_type, encrypted=False, notes=""):
    """Crée une sauvegarde de la base de données sans duplication sur disque"""
    try:
        logger.info(f"Starting backup creation - type: {backup_type}, encrypted: {encrypted}")
        credentials = get_db_credentials()
        logger.debug(f"DB credentials: {credentials}")

        backup_filename = generate_backup_filename(backup_type)
        if encrypted:
            backup_filename += '.enc'

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

        # Exécution de la commande avec sortie capturée en mémoire
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False
        )
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
            raise subprocess.CalledProcessError(
                process.returncode,
                cmd,
                error_msg
            )

        if not stdout:
            raise Exception("Backup content is empty")

        # Chiffrement si demandé
        if encrypted:
            key = Fernet.generate_key()
            cipher = Fernet(key)
            encrypted_data = cipher.encrypt(stdout)
            final_data = encrypted_data + b'\nKEY:' + key
        else:
            final_data = stdout

        # Création de l'objet de sauvegarde
        backup = DatabaseBackup(
            name=backup_filename.replace('.sql', '').replace('.enc', ''),
            backup_type=backup_type,
            encrypted=encrypted,
            notes=notes,
            successful=True
        )

        # Sauvegarde en mémoire via ContentFile
        backup.backup_file.save(backup_filename, ContentFile(final_data), save=False)
        backup.save()

        return backup

    except Exception as e:
        logger.error(f"Backup failed completely: {str(e)}", exc_info=True)
        raise


# def restore_backup(backup, request):
#     """Restaure une sauvegarde de la base de données"""
#     credentials = get_db_credentials()
#     backup_path = backup.backup_file.path
#     temp_path = None
    
#     try:
#         # Décryptage si nécessaire
#         if backup.encrypted:
#             with open(backup_path, 'rb') as f:
#                 file_content = f.read()
            
#             # Séparation des données chiffrées et de la clé
#             if b'KEY:' not in file_content:
#                 raise ValueError("Format de fichier chiffré invalide - marqueur KEY: manquant")
            
#             encrypted_data, key = file_content.split(b'KEY:')
#             cipher = Fernet(key.strip())
            
#             try:
#                 decrypted_data = cipher.decrypt(encrypted_data)
#             except Exception as e:
#                 raise ValueError(f"Échec du déchiffrement: {str(e)}")
            
#             # Création d'un fichier temporaire
#             temp_path = tempfile.mktemp(suffix='.sql')
#             with open(temp_path, 'wb') as f:
#                 f.write(decrypted_data)
            
#             backup_path = temp_path
        
#         # Vérification que le fichier de restauration existe
#         if not os.path.exists(backup_path):
#             raise FileNotFoundError(f"Fichier de restauration {backup_path} introuvable")
        
#         # Construction de la commande mysql
#         cmd = [
#             settings.MYSQL_PATHS['mysql'],
#             f"--user={credentials['USER']}",
#             f"--password={credentials['PASSWORD']}",
#             f"--host={credentials['HOST']}",
#             f"--port={credentials['PORT']}",
#             credentials['NAME']
#         ]
        
#         logger.info(f"Restoring backup with command: {' '.join(cmd)}")
        
#         # Exécution de la commande
#         with open(backup_path, 'rb') as f:  # Lecture en mode binaire pour compatibilité
#             process = subprocess.Popen(
#                 cmd,
#                 stdin=f,
#                 stderr=subprocess.PIPE,
#                 universal_newlines=True,
#                 shell=True
#             )
#             _, stderr = process.communicate()
            
#             if process.returncode != 0:
#                 raise subprocess.CalledProcessError(
#                     process.returncode,
#                     cmd,
#                     stderr
#                 )
        
#         return True, "Restauration réussie"
    
#     except Exception as e:
#         logger.error(f"Restore failed: {str(e)}", exc_info=True)
#         return False, str(e)
    
#     finally:
#         # Nettoyage du fichier temporaire dans tous les cas
#         if temp_path and os.path.exists(temp_path):
#             try:
#                 os.remove(temp_path)
#             except Exception as e:
#                 logger.warning(f"Échec de la suppression du fichier temporaire: {str(e)}")




def restore_backup(backup, request):
    credentials = get_db_credentials()
    backup_path = backup.backup_file.path
    temp_path = None

    try:
        if backup.encrypted:
            with open(backup_path, 'rb') as f:
                file_content = f.read()

            if b'KEY:' not in file_content:
                raise ValueError("Format de fichier chiffré invalide - marqueur KEY: manquant")

            encrypted_data, key = file_content.split(b'KEY:')
            cipher = Fernet(key.strip())
            decrypted_data = cipher.decrypt(encrypted_data)

            with tempfile.NamedTemporaryFile(suffix='.sql', delete=False) as tmp_file:
                tmp_file.write(decrypted_data)
                temp_path = tmp_file.name

            backup_path = temp_path

        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Fichier de restauration {backup_path} introuvable")

        cmd = [
            settings.MYSQL_PATHS['mysql'],
            f"--user={credentials['USER']}",
            f"--host={credentials['HOST']}",
            f"--port={credentials['PORT']}",
            credentials['NAME']
        ]

        env = os.environ.copy()
        env['MYSQL_PWD'] = credentials['PASSWORD']

        logger.info(f"Restoring backup with command: {' '.join(cmd)}")

        with open(backup_path, 'rb') as f:
            process = subprocess.Popen(
                cmd,
                stdin=f,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                shell=False,
                env=env
            )
            _, stderr = process.communicate(timeout=300)  # timeout 5min

            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, cmd, stderr)

        return True, "Restauration réussie"

    except Exception as e:
        logger.error(f"Restore failed: {str(e)}", exc_info=True)
        return False, str(e)

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                logger.warning(f"Échec de la suppression du fichier temporaire: {str(e)}")
