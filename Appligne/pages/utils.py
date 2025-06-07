import jwt  # Importation de la bibliothèque JWT pour la création et la gestion des tokens
from datetime import datetime, timedelta, timezone  # Importation des modules nécessaires pour gérer le temps
from django.conf import settings  # Importation des paramètres de configuration de Django
import logging
import requests

# Configuration du logger avec le nom du module actuel
logger = logging.getLogger(__name__)

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


def verify_recaptcha(captcha_response, client_ip=None):
    """
    Vérification améliorée de reCAPTCHA v3 avec gestion des erreurs.

    Args:
        captcha_response (str): Jeton reCAPTCHA envoyé par le client (souvent depuis un formulaire).
        client_ip (str, optional): Adresse IP du client, utile pour la journalisation et parfois exigée par Google.

    Returns:
        tuple: 
            - success (bool): True si la vérification a réussi, False sinon.
            - score (float): Score reCAPTCHA retourné par l’API (entre 0.0 et 1.0).
    """

    # Vérifie si le jeton reCAPTCHA est présent
    if not captcha_response:
        logger.warning(f"Aucune réponse CAPTCHA reçue - IP: {client_ip or 'inconnue'}")
        return False, 0.0

    try:
        # Préparation des données à envoyer à l’API reCAPTCHA de Google
        data = {
            'secret': settings.RECAPTCHA_PRIVATE_KEY,  # Clé privée fournie par Google
            'response': captcha_response               # Jeton reCAPTCHA envoyé par le client
        }

        # Ajout de l’adresse IP du client (optionnel mais recommandé par Google)
        if client_ip:
            data['remoteip'] = client_ip

        # Envoi de la requête POST vers l’API de vérification de Google
        response = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data=data,
            timeout=5   # Timeout de sécurité ( 5 secondes que votre application attendra la réponse 
                        #de Google après avoir envoyé la requête POST à l’API de vérification reCAPTCHA.) 
                        # pour éviter les appels bloquants
        )

        # Conversion de la réponse JSON en dictionnaire Python
        result = response.json()

        # Extraction des résultats : succès et score du reCAPTCHA
        success = result.get('success', False)
        score = result.get('score', 0.0)

        # Journalisation complète pour audit et débogage
        logger.debug(
            f"CAPTCHA verify - IP: {client_ip or 'inconnue'} | "
            f"Hostname: {result.get('hostname', 'inconnu')} | "      # Domaine validé (utile contre les abus)
            f"Score: {score:.2f} | "                                 # Score entre 0.0 (bot) et 1.0 (humain)
            f"Action: {result.get('action', 'inconnue')} | "         # Action précisée lors de l'exécution du reCAPTCHA
            f"Timestamp: {result.get('challenge_ts', 'N/A')} | "     # Timestamp de l’événement
            f"Success: {success}"                                    # Succès ou non
        )

        # Si échec, journalise les erreurs retournées par l’API (ex: clé invalide, réponse expirée, etc.)
        if not success:
            error_codes = result.get('error-codes', [])
            logger.warning(
                f"Échec CAPTCHA - IP: {client_ip or 'inconnue'} | "
                f"Erreurs: {', '.join(error_codes) or 'aucune'}"
            )

        # Retourne les résultats de la vérification
        return success, score

    # Gestion des erreurs de connexion réseau (API inaccessible, délai dépassé, etc.)
    except requests.exceptions.RequestException as e:
        logger.error(
            f"Erreur réseau CAPTCHA - IP: {client_ip or 'inconnue'} | "
            f"Erreur: {str(e)}"
        )
        return False, 0.0

    # Gestion d’erreurs imprévues pour éviter les crashs silencieux
    except Exception as e:
        logger.error(
            f"Erreur inattendue CAPTCHA - IP: {client_ip or 'inconnue'} | "
            f"Erreur: {str(e)}"
        )
        return False, 0.0


def get_client_ip(request):
    """
    Récupère l'adresse IP réelle du client, même s'il passe par un ou plusieurs proxies.

    La logique suivante est appliquée :
    - Si la requête provient d’un proxy de confiance (ex: un reverse proxy NGINX local),
      on extrait l’IP client depuis le header `X-Forwarded-For`.
    - Sinon, on se contente de l’IP vue directement par Django (`REMOTE_ADDR`).

    Cela permet de limiter les risques d'usurpation d'IP via un faux header X-Forwarded-For.
    """

    # ✅ Récupère la valeur brute du header HTTP_X_FORWARDED_FOR s’il est présent
    # Ce header peut contenir plusieurs IP séparées par des virgules, dans l’ordre :
    # IP client, IP proxy1, IP proxy2, ..., IP du proxy final
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    # ✅ Récupère l’adresse IP directement visible par le serveur (souvent celle du dernier proxy ou du client)
    remote_addr = request.META.get('REMOTE_ADDR')

    # ✅ Déclare les adresses IP des reverse proxies considérés comme fiables (à adapter selon votre config)
    # Exemples courants : localhost (127.0.0.1) ou ::1 (IPv6 localhost)
    trusted_proxies = ['127.0.0.1', '::1']

    # 🔍 Log des valeurs initiales pour analyse en cas de problème
    logger.debug(f"REMOTE_ADDR détectée : {remote_addr}")
    logger.debug(f"X-Forwarded-For brut : {x_forwarded_for}")

    if x_forwarded_for:
        # ✅ Nettoie et sépare les différentes IPs dans le header X-Forwarded-For
        ip_list = [ip.strip() for ip in x_forwarded_for.split(',')]
        logger.debug(f"Liste des IPs extraites du X-Forwarded-For : {ip_list}")

        # ✅ Vérifie si la requête a été reçue via un proxy de confiance
        if remote_addr in trusted_proxies:
            # 🟢 On fait confiance au header et on prend la première IP (celle du client réel)
            client_ip = ip_list[0]
            logger.debug(f"Client IP déterminée depuis X-Forwarded-For : {client_ip}")
            return client_ip
        else:
            # 🔴 Requête venant d’un proxy non approuvé : on ignore X-Forwarded-For pour éviter les spoofing
            logger.warning(f"REMOTE_ADDR non reconnu comme proxy de confiance : {remote_addr} — refus de faire confiance à X-Forwarded-For")

    # ✅ Cas par défaut : on retourne l'adresse IP directe vue par Django
    logger.debug(f"Client IP déterminée depuis REMOTE_ADDR : {remote_addr}")
    return remote_addr


import logging
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render


logger = logging.getLogger(__name__)

def check_captcha_verification(request, captcha_response, user_ip, user_agent, context_data, is_ajax):
    """
    Vérifie le CAPTCHA et retourne une réponse Http en cas d'échec.
    
    Args :
        request: HttpRequest courant
        captcha_response (str): Jeton reCAPTCHA v3 envoyé par le frontend
        user_ip (str): Adresse IP du client
        user_agent (str): Navigateur ou agent utilisateur
        context_data (dict): Données de contexte pour le template
        is_ajax (bool): Indique si la requête est AJAX

    Returns :
        None si succès, sinon HttpResponse (erreur ou message)
    """
    captcha_valid, captcha_score = verify_recaptcha(captcha_response, client_ip=user_ip)

    # CAPTCHA invalide
    if not captcha_valid:
        error_msg = "Validation CAPTCHA échouée. Veuillez réessayer."
        logger.warning(f"CAPTCHA invalide - IP: {user_ip} - Agent: {user_agent} - Score: {captcha_score}")
        if is_ajax:
            return JsonResponse({'error': error_msg}, status=400)
        messages.error(request, error_msg)
        return render(request, 'pages/seconnecter.html', context_data)

    # CAPTCHA valide mais score trop faible
    if captcha_score < getattr(settings, 'RECAPTCHA_MIN_SCORE', 0.5):
        error_msg = "Activité suspecte détectée. Veuillez réessayer."
        logger.warning(f"Score CAPTCHA trop bas - IP: {user_ip} - Agent: {user_agent} - Score: {captcha_score}")
        if is_ajax:
            return JsonResponse({'error': error_msg}, status=400)
        messages.error(request, error_msg)
        return render(request, 'pages/seconnecter.html', context_data)

    return None  # Succès

def handle_recaptcha_validation(captcha_response, user_ip, user_agent, request=None, context_data=None, is_ajax=False):
    """
    Appelle check_captcha_verification et retourne une réponse HTTP si erreur,
    sinon retourne None si tout est ok.
    """
    result = check_captcha_verification(
        request=request,
        captcha_response=captcha_response,
        user_ip=user_ip,
        user_agent=user_agent,
        context_data=context_data or {},
        is_ajax=is_ajax
    )
    return result  # soit None, soit JsonResponse ou render()
