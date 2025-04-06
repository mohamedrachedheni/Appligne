import jwt  # Importation de la bibliothèque JWT pour la création et la gestion des tokens
from datetime import datetime, timedelta, timezone  # Importation des modules nécessaires pour gérer le temps
from django.conf import settings  # Importation des paramètres de configuration de Django

def generate_jwt_token(user_id):
    """
    Génère un token JWT pour un utilisateur donné.
    
    Args:
    - user_id (int/str) : L'identifiant de l'utilisateur pour lequel le token est généré.
    
    Returns:
    - str : Le token JWT encodé.
    """
    
    # Création du payload du token avec l'identifiant de l'utilisateur et la date d'expiration
    payload = {
        'user_id': user_id,  # L'identifiant de l'utilisateur
        'exp': datetime.now(timezone.utc) + timedelta(seconds=settings.JWT_EXP_DELTA_SECONDS)  # La date d'expiration du token
    }
    
    # Encodage du token JWT en utilisant la clé secrète et l'algorithme spécifiés dans les paramètres de configuration
    token = jwt.encode(payload, settings.JWT_SECRET, settings.JWT_ALGORITHM)
    
    # Retourne le token JWT encodé
    return token


from cryptography.fernet import Fernet
from django.conf import settings

# Clé Fernet
fernet = Fernet(settings.SECRET_ENCRYPTION_KEY.encode())

def encrypt_id(value):
    """Chiffre un ID et retourne la chaîne sécurisée."""
    return fernet.encrypt(str(value).encode()).decode()

def decrypt_id(encrypted_value):
    """Déchiffre un ID sécurisé et retourne sa valeur d'origine."""
    try:
        return int(fernet.decrypt(encrypted_value.encode()).decode())
    except Exception:
        return None

