from accounts.models import WebhookEvent, Email_telecharge
from django.utils import timezone
from datetime import date
from django.conf import settings
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.models import User
import math
import logging

logger = logging.getLogger(__name__)


def verifier_coherence_montants(texte1, texte2, montant1, montant2, abs_tol=5, user_admin=None):
    """
    Vérifie la cohérence entre deux montants (exprimés en centimes).
    En cas d'incohérence, log un avertissement et envoie un email à l'administrateur.
    
    Args:
        texte1 (str): Libellé du premier montant (ex: 'facture').
        texte2 (str): Libellé du second montant (ex: 'payment_intent', 'webhook', etc.).
        montant1 (int | float): Premier montant (en centimes).
        montant2 (int | float): Second montant (en centimes).
        abs_tol (int | float): Tolérance absolue en centimes (par défaut = 5 = 0.05 €).
        user_admin (User | None): Utilisateur administrateur à notifier par email.
        event_id (event_id| None): s'il s'agit d'un évènement webhook
    """
    
    if not math.isclose(montant1, montant2, abs_tol=abs_tol):
        message = (
            f"⚠️ Incohérence de montant - {texte1} / {texte2} : "
            f"{texte1.capitalize()} = {montant1 / 100:.2f} €, "
            f"{texte2.capitalize()} = {montant2 / 100:.2f} € "
            f"(tolérance ±{abs_tol / 100:.2f} €)"
        )

        logger.warning(message)

        
        # Envoi d’un email admin si disponible
        if user_admin is not None:
            envoie_email_multiple(
                user_admin.id,
                [user_admin.id],
                sujet_email=f"Incohérence de montant - {texte1} / {texte2}",
                texte_email=message
            )

        return False  # incohérent

    return True  # cohérent

def add_webhook_log(event_id: str, message: str) -> None:
    """
    🔹 Ajoute un message au champ handle_log du WebhookEvent correspondant.
    Si l'événement n'existe pas encore, il est ignoré proprement.
    """
    try:
        # Récupère ou crée l'événement
        webhook_event, _ = WebhookEvent.objects.get_or_create(event_id=event_id)

        # Crée la ligne de log
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}\n"

        # Concatène au log existant
        if webhook_event.handle_log:
            webhook_event.handle_log += line
        else:
            webhook_event.handle_log = line

        # Sauvegarde uniquement le champ modifié
        webhook_event.save(update_fields=["handle_log"])

        logger.debug(f"📝 Log ajouté à WebhookEvent {event_id} : {message}")

    except Exception as e:
        logger.error(f"❌ Erreur dans add_webhook_log pour {event_id}: {e}")



def _update_webhook_status(event_id: str, is_fully_completed: bool, message: str) -> None:
    """
    🔄 Met à jour le statut d'un événement webhook Stripe et journalise son avancement.

    Objectifs :
    - Garantir la cohérence des mises à jour
    - Assurer une traçabilité complète des traitements
    - Faciliter le monitoring et le debug

    Args:
        event_id (str): Identifiant unique de l'événement Stripe.
        is_fully_completed (bool): True si le traitement est terminé avec succès.
        message (str): Message descriptif pour les logs.
    """
    if not event_id:
        logger.warning("⚠️ Impossible de mettre à jour le webhook : event_id manquant.")
        return

    try:
        # Récupère ou crée l'événement (assure la cohérence des traces)
        webhook_event, _ = WebhookEvent.objects.get_or_create(event_id=event_id)

        # Met à jour les statuts principaux
        webhook_event.is_processed = True
        webhook_event.is_fully_completed = is_fully_completed
        webhook_event.save(update_fields=["is_processed", "is_fully_completed"])

        # Ajoute un log clair et structuré
        status_icon = "✅" if is_fully_completed else "⚠️"
        status_text = "Terminé avec succès" if is_fully_completed else "Traitement partiel / "
        log_message = f"{status_icon} {status_text} – {message}"
        add_webhook_log(event_id, log_message)

        # Log technique pour le debug
        logger.debug(f"📝 [Webhook {event_id}] Statut mis à jour → traité={True}, complété={is_fully_completed}")

    except Exception as e:
        error_msg = f"💥 Erreur lors de la mise à jour du statut webhook {event_id} : {e}"
        logger.error(error_msg)
        add_webhook_log(event_id, f"⚠️ Échec de mise à jour du statut : {str(e)}")



def envoie_email_multiple(user_id_envoi, liste_user_id_receveurs, sujet_email, texte_email, reponse_email_id=None):
    """
    📧 Envoie un e-mail à plusieurs destinataires et enregistre chaque envoi dans Email_telecharge.

    Args:
        user_id_envoi (int): ID de l'expéditeur.
        liste_user_id_receveurs (list[int]): Liste des IDs des destinataires.
        sujet_email (str): Sujet de l'e-mail.
        texte_email (str): Contenu du message.
        reponse_email_id (int | None): ID d'un e-mail auquel celui-ci répond (facultatif).

    Returns:
        dict: Résultat global avec le nombre d'e-mails envoyés et enregistrés.
    """
    resultat = {
        "emails_envoyes": 0,
        "emails_enregistres": 0,
        "erreurs": []
    }

    # ✅ Vérifier l'expéditeur
    try:
        user_envoi = User.objects.get(id=user_id_envoi)
    except User.DoesNotExist:
        logger.error("❌ Utilisateur expéditeur introuvable.")
        return resultat

    email_expediteur = user_envoi.email

    # ✅ Valider l'email expéditeur
    try:
        validate_email(email_expediteur)
    except ValidationError:
        logger.error(f"❌ Adresse e-mail expéditeur invalide : {email_expediteur}")
        return resultat

    # ✅ Boucle sur chaque destinataire
    for user_id in liste_user_id_receveurs:
        try:
            user_receveur = User.objects.get(id=user_id)
        except User.DoesNotExist:
            erreur = f"❌ Utilisateur destinataire ID {user_id} introuvable."
            logger.error(erreur)
            resultat["erreurs"].append(erreur)
            continue

        email_destinataire = user_receveur.email

        # ✅ Valider email destinataire
        try:
            validate_email(email_destinataire)
        except ValidationError:
            erreur = f"❌ E-mail destinataire invalide : {email_destinataire}"
            logger.error(erreur)
            resultat["erreurs"].append(erreur)
            continue

        # ✅ Envoi de l'e-mail
        try:
            send_mail(
                subject=sujet_email,
                message=texte_email,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email_destinataire],
                fail_silently=False,
            )
            logger.info(f"✅ E-mail envoyé à {email_destinataire}")
            resultat["emails_envoyes"] += 1
        except Exception as e:
            erreur = f"❌ Échec d'envoi vers {email_destinataire} : {e}"
            logger.error(erreur)
            resultat["erreurs"].append(erreur)
            continue

        # ✅ Enregistrement en base
        try:
            Email_telecharge.objects.create(
                user=user_envoi,
                email_telecharge=email_expediteur,
                sujet=sujet_email,
                text_email=texte_email,
                user_destinataire=user_receveur.id,
                suivi='Mis à côté',
                date_suivi=date.today(),
                reponse_email_id=reponse_email_id if reponse_email_id else None
            )
            logger.info(f"📩 E-mail enregistré pour {email_destinataire}")
            resultat["emails_enregistres"] += 1
        except Exception as e:
            erreur = f"❌ Échec d'enregistrement pour {email_destinataire} : {e}"
            logger.error(erreur)
            resultat["erreurs"].append(erreur)
            continue

    return resultat


def log_webhook_error(webhook_event, message):
    timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    webhook_event.handle_log += f"\n[{timestamp}] 💥 {message}"
    webhook_event.save(update_fields=['handle_log'])

def append_webhook_log(webhook_event, message):
    timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}\n"

    # Concatène au log existant
    if webhook_event.handle_log:
        webhook_event.handle_log += line
    else:
        webhook_event.handle_log = line

    # Sauvegarde uniquement le champ modifié
    webhook_event.save(update_fields=["handle_log"])



def _webhook_status_update(webhook_event, is_fully_completed: bool, message: str) -> None:
    """
    🔄 Met à jour le statut d'un événement webhook Stripe et journalise son avancement.

    Objectifs :
    - Garantir la cohérence des mises à jour
    - Assurer une traçabilité complète des traitements
    - Faciliter le monitoring et le debug

    Args:
        event_id (str): Identifiant unique de l'événement Stripe.
        is_fully_completed (bool): True si le traitement est terminé avec succès.
        message (str): Message descriptif pour les logs.
    """

    try:
        # Met à jour les statuts principaux
        webhook_event.is_processed = True
        webhook_event.is_fully_completed = is_fully_completed
        webhook_event.save(update_fields=["is_processed", "is_fully_completed"])

        # Ajoute un log clair et structuré
        status_icon = "✅" if is_fully_completed else "⚠️"
        status_text = "Terminé avec succès" if is_fully_completed else "Traitement partiel / "
        log_message = f"{status_icon} {status_text} – {message}"
        append_webhook_log(webhook_event, log_message)

        # Log technique pour le debug
        logger.debug(f"📝 [Webhook {webhook_event.event_id}] Statut mis à jour → traité={True}, complété={is_fully_completed}")

    except Exception as e:
        error_msg = f"💥 Erreur lors de la mise à jour du statut webhook {webhook_event.event_id} : {e}"
        logger.error(error_msg)
        append_webhook_log(webhook_event, f"⚠️ Échec de mise à jour du statut : {str(e)}")