# payment>views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse, FileResponse
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.core.validators import validate_email, EmailValidator
from django.db import transaction
from django.db.models import Sum, F
from django.utils import timezone
from django.conf import settings
from django.views.decorators.http import require_http_methods, require_POST
from django.http import Http404
from payment.utils.notifications import verifier_coherence_montants, add_webhook_log, envoie_email_multiple, _update_webhook_status, log_webhook_error, append_webhook_log, _webhook_status_update


from functools import wraps
import json
import logging
import math
import os
import pprint
from datetime import date, datetime
from decimal import Decimal
import traceback

import stripe
from cart.models import Cart, CartItem, Invoice, CartTransfert, CartTransfertItem, InvoiceTransfert
from accounts.models import (
    Payment, Horaire, Historique_prof, Mes_eleves, Detail_demande_paiement, 
    Email_telecharge, Demande_paiement, Professeur, Transfer, DetailAccordReglement, 
    AccordReglement, WebhookEvent, DetailAccordRemboursement, AccordRemboursement, RefundPayment
)
from eleves.models import Eleve
from pages.utils import decrypt_id, encrypt_id, to_cents
from cart.models import  BalanceTransaction, PaymentIntentTransaction
# Pour les testes Webhook mode:  teste / live
import os
STRIPE_LIVE_MODE = os.getenv("STRIPE_LIVE_MODE", "false").lower() == "true"


# Configuration du logger
logger = logging.getLogger(__name__)
pp = pprint.PrettyPrinter(indent=2)

User = get_user_model()

# Create your views here.
# ... le reste de votre code ...

# ----------------------------------------------------------
# Enregistre la BalanceTransaction Stripe depuis charge.succeeded
# ----------------------------------------------------------

from datetime import datetime
from datetime import timezone as dt_timezone
from django.db import transaction

def save_balance_transaction_from_charge(
    *,
    bal: dict,
    data_object: dict,
    balance_txn_id: str,
    charge_succeeded_id: str,
    webhook_event,
    payment_intent_id: str
):
    """
    Enregistre la BalanceTransaction Stripe depuis charge.succeeded

    Retourne:
        (balance_txn_obj, created)
    """

    if not bal:
        append_webhook_log(
            webhook_event,
            "❌ Données balance manquantes"
        )
        return None, False

    with transaction.atomic():

        # --------------------------------------------------
        # 📅 Date de mise en valeur (available_on)
        # --------------------------------------------------
        timestamp = bal.get("available_on")
        date_mise_en_valeur = (
            datetime.fromtimestamp(timestamp, tz=dt_timezone.utc)
            if timestamp is not None
            else None
        )

        # --------------------------------------------------
        # 🔐 Sécurisation Stripe (NULL fréquents)
        # --------------------------------------------------
        source = data_object.get("source") or {}
        payment_method_details = data_object.get("payment_method_details") or {}
        card_details = payment_method_details.get("card") or {}
        fee_details = bal.get("fee_details") or []

        # --------------------------------------------------
        # 💳 Enregistrement BalanceTransaction
        # --------------------------------------------------
        balance_txn_obj, created = BalanceTransaction.objects.update_or_create(
            balance_txn_id=balance_txn_id,
            defaults={
                "amount": bal.get("amount"),
                "fee": bal.get("fee"),
                "net": bal.get("net"),
                "currency": bal.get("currency", "eur"),
                "status": bal.get("status"),

                # 📅 Disponibilité des fonds
                "is_available": True,
                "available_on": date_mise_en_valeur,
                "event_type": bal.get("type"), # pour ce cas on a"charge",pour d'autre cas: "refund", "payout", stripe_fee, transfer , dispute, ...

                # ---- Card details ----
                "payment_method_brand": card_details.get("brand"),
                "payment_method_last4": card_details.get("last4"),
                "payment_method_country": card_details.get("country"),
                "payment_method_type": payment_method_details.get("type"),

                # ---- Divers ----
                "ip_country": source.get("country"),
                "stripe_fee": sum(f.get("amount", 0) for f in fee_details),
                "tax_fee": sum(
                    f.get("amount", 0)
                    for f in fee_details
                    if f.get("type") == "tax"
                ),
                "description": data_object.get("description"),
            }
        )

        append_webhook_log(
            webhook_event,
            f"📌 BalanceTransaction {'créée' if created else 'mise à jour'} : {balance_txn_id}"
        )

        # --------------------------------------------------
        # 🔗 Lien PaymentIntentTransaction
        # --------------------------------------------------
        PaymentIntentTransaction.objects.update_or_create(
            charge_id=charge_succeeded_id,
            defaults={
                "payment_intent_id": payment_intent_id,
                "balance_txn": balance_txn_obj
            }
        )

        append_webhook_log(
            webhook_event,
            (
                "🔗 PaymentIntentTransaction lié : "
                f"PI={data_object.get('payment_intent')}, "
                f"Charge={charge_succeeded_id}"
            )
        )

        return balance_txn_obj, created


# ----------------------------------------------------------
# Début traitement de paiement par carte bancaire des élèves
# ----------------------------------------------------------

def is_admin(user):
    return user.is_authenticated and user.is_staff

# Parce que stripe.checkout.Session.create(...) (et toute autre requête Stripe) nécessite que la clé API soit configurée avant utilisation.
stripe.api_key = settings.STRIPE_SECRET_KEY # obligatoire si non Stripe ne communique pas


def secure_stripe_action(action_name):
    """
    Décorateur intelligent pour sécuriser les actions critiques (comme un remboursement).
    - Log automatique
    - Empêche double soumission
    - Capture StripeError + exceptions générales
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Empêche double soumission (refresh brut)
            if request.session.get(f"lock_{action_name}", False):
                messages.warning(request, "Action déjà en cours, merci de patienter.")
                return redirect('admin_remboursement_detaille')
            
            # Poser le verrou
            request.session[f"lock_{action_name}"] = True

            try:
                logger.info(f"[{action_name}] Lancement par {request.user}...")
                response = view_func(request, *args, **kwargs)
                logger.info(f"[{action_name}] Terminé avec succès.")
                return response

            except stripe.error.StripeError as e:
                logger.error(f"[{action_name}] ERREUR STRIPE : {str(e)}")
                messages.error(request, f"Erreur Stripe : {str(e)}")
                return redirect('admin_remboursement_detaille')

            except Exception as e:
                logger.exception(f"[{action_name}] ERREUR CRITIQUE")
                messages.error(request, "Une erreur interne est survenue.")
                return redirect('admin_remboursement_detaille')

            finally:
                # Libération du verrou en toute fin
                request.session[f"lock_{action_name}"] = False

        return wrapper

    return decorator


"""
✅ Sécurité assurée par :
Élément	Rôle
@login_required	Empêche l’accès aux utilisateurs non connectés
get_object_or_404(..., user=request.user)	Empêche d’accéder à une facture qui ne t’appartient pas
Vérification os.path.exists	Évite l’erreur si le fichier PDF n’existe plus
"""

@login_required
def download_invoice(request, invoice_id):
    """
    On cherche une facture (Invoice) qui correspond :
        à l’invoice_id donné dans l’URL,
        ET qui appartient à l'utilisateur actuellement connecté.
        Si rien n’est trouvé, cela renvoie une erreur 404 automatiquement.
    """
    invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)
    
    """
    invoice.pdf.name donne le chemin relatif du fichier stocké (ex : "invoices/invoice_INV-20250701-ABC123.pdf").
    settings.MEDIA_ROOT est la racine absolue des fichiers médias (souvent media/).
    Ce code donne le chemin complet vers le fichier PDF sur le disque.
    """
    file_path = os.path.join(settings.MEDIA_ROOT, invoice.pdf.name)
    
    if os.path.exists(file_path): # Vérification de l’existence du fichier et téléchargement
        """
        Si le fichier existe physiquement :
            On ouvre le fichier en mode binaire lecture ('rb').
            FileResponse renvoie ce fichier comme une réponse HTTP.
            L’en-tête HTTP Content-Disposition indique au navigateur :
                de télécharger le fichier (attachment)
                sous un nom de fichier personnalisé (ex. : facture_INV-20250701-ABC123.pdf).
        """
        response = FileResponse(open(file_path, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="facture_{invoice.invoice_number}.pdf"'
        response['Content-Type'] = 'application/pdf'  # 🔍 Type MIME explicitement défini, (plus sûr en plus)
        return response
    """
    Si le fichier n’existe pas physiquement, on renvoie une erreur 404 personnalisée.
    Cela peut arriver si le fichier a été supprimé manuellement ou mal généré.
    """
    raise Http404("La facture n'existe pas")




def update_historique_prof(prof, demande_paiement, user):
    # Il y a création si le prof n'a pas d'historique
    # c'est uncas trés rare, car normalement l'historique du prof commence à la réponse de la demande du cours
    historique_prof, created = Historique_prof.objects.get_or_create(
        user=prof,
        defaults={
            'date_premier_cours': timezone.now(),
            'date_dernier_cours': timezone.now(),
            'nb_eleve_inscrit': 1  # premier élève inscrit (dont la demande de paiement est réalisée)
        }
    )

    # MAJ date_dernier_cours et date_premier_cours
    if not created:  # Le prof a déjà un historique
        historique_prof.date_dernier_cours = timezone.now()  # Mise à jour de la date du dernier cours
        if not historique_prof.date_premier_cours:  # Si la date du premier cours est vide
            historique_prof.date_premier_cours = timezone.now()  # Mise à jour de la date du premier cours
    # récupérer l'élève par objet user
    eleve = Eleve.objects.get(user=user)
    # récupérer mon_eleve dans Mes_eleves par objet eleve
    mon_eleve = Mes_eleves.objects.get(eleve=eleve, user=prof)

    # historique_prof.nb_eleve_inscrit: désigne le nombre des élève qui ont au moins effectué un règlement
    nb_reglement_eleve = Demande_paiement.objects.filter(user=prof, mon_eleve=mon_eleve, statut_demande='Réaliser').count()
    if nb_reglement_eleve == 1 and not created:  # Si c'est le premier règlement réalisé pour cet élève et le prof à un historique
        historique_prof.nb_eleve_inscrit += 1  # Augmenter le nombre d'élèves inscrits

    # MAJ nb_heure_declare : Total des heures réglées pour cette demande de paiement
    # la somme de la durée de tous les horaires associés à la demande de paiement. si null alors c'est 0
    total_heure = Detail_demande_paiement.objects.filter(demande_paiement=demande_paiement).aggregate(total=Sum('horaire__duree'))['total'] or 0
    # cette formule ne tient pas le cas ou c'est null:  total_heure = sum(enr.horaire.duree for enr in Detail_demande_paiement.objects.filter(demande_paiement=demande_paiement))
    # Convertir total_heure en entier et l'ajouter au nombre d'heures déjà déclarées
    historique_prof.nb_heure_declare += int(total_heure)

    # Sauvegarder les modifications apportées à l'historique
    historique_prof.save()







########################
# STRIPE API PAYMENT
########################

@login_required
def create_checkout_session(request):
    """
    LOGIQUE DE TRAITEMENT
    ----------------------
    1. Vérifie que l'utilisateur est connecté
    2. Récupère le panier
    3. Vérifie que le panier contient des articles
    4. Expire les anciennes sessions Stripe actives
    5. Récupère ou crée une facture (Invoice) cohérente
    6. Construit les line_items pour Stripe
    7. Crée une session Stripe
    8. Met à jour la facture avec stripe_id
    9. Redirige l'utilisateur vers Stripe
    """

    user_admin = User.objects.filter(is_staff=True, is_active=True).first()
    logger.info(f"[{request.user}] ➤ Début de create_checkout_session")

    # ----------------------------------------------------------------------
    # 1. PANIER (Cart)
    # ----------------------------------------------------------------------
    cart = get_object_or_404(Cart, user=request.user)
    logger.info(f"[{request.user}] ➤ Cart récupéré ({cart.items.count()} item(s))")

    if not cart.items.exists():
        messages.error(request, "Votre panier est vide. Impossible de procéder au paiement.")
        logger.warning(f"[{request.user}] ➤ Panier vide")
        return redirect("eleve_demande_paiement")

    # ----------------------------------------------------------------------
    # 2. EXPIRATION DES ANCIENNES SESSIONS
    # ----------------------------------------------------------------------
    try:
        active_invoices = Invoice.objects.filter(
            user=request.user,
            demande_paiement=cart.demande_paiement,
            status=Invoice.DRAFT
        ).exclude(stripe_id__isnull=True).exclude(stripe_id="")

        for old in active_invoices:
            try:
                stripe.checkout.Session.expire(old.stripe_id)
                logger.info(f"[{request.user}] ➤ Session Stripe expirée : {old.stripe_id}")
            except stripe.error.InvalidRequestError as e:
                # Session déjà expirée ou introuvable → acceptable
                if "No such checkout session" in str(e) or "expired" in str(e):
                    logger.warning(f"[{request.user}] ➤ Session déjà expirée : {old.stripe_id}")
                else:
                    raise e
            except Exception as e:
                logger.error(f"[{request.user}] ❌ Erreur expiration ({old.stripe_id}) : {e}")

            old.status = Invoice.CANCELED
            old.save()

    except Exception as e:
        logger.error(f"[{request.user}] ❌ Erreur expiration sessions : {e}")
        messages.error(request, "Impossible de réinitialiser vos anciennes sessions.")
        return redirect("eleve_demande_paiement")

    # ----------------------------------------------------------------------
    # 3. CRÉATION / RÉCUPÉRATION FACTURE
    # ----------------------------------------------------------------------
    try:
        invoice = Invoice.objects.filter(
            user=request.user,
            demande_paiement=cart.demande_paiement,
            status__in = [Invoice.PAID, Invoice.DRAFT],
        ).first()
        if invoice:
            messages.error(request, "La demande de paiement est déjà règlée, ou en cours")
            return redirect("eleve_demande_paiement")
        invoice = Invoice.objects.filter(
            user=request.user,
            demande_paiement=cart.demande_paiement,
        ).first()
        logger.info(f"invoice = {invoice}, user_id {request.user.id} , demande_paiement_id = {cart.demande_paiement.id}")
        if not invoice:
            invoice = Invoice.objects.create(
                cart=cart,
                demande_paiement=cart.demande_paiement,
                user=request.user,
                total=cart.total,
                status=Invoice.DRAFT,
                invoice_number=Invoice().generate_invoice_number()
            )
            logger.info(f"[{request.user}] ➤ Nouvelle facture créée (ID={invoice.id})")

        else:
            # Réutilisation si cohérente
            if invoice.total == cart.total and invoice.status != Invoice.PAID:
                invoice.cart = cart
                invoice.stripe_id = None
                invoice.status = Invoice.DRAFT
                invoice.save()
                logger.info(f"[{request.user}] ➤ Facture réutilisée (ID={invoice.id})")
            else:
                # Incohérence → alerte admin
                logger.error(f"[{request.user}] ❌ Tentative de double paiement")
                envoie_email_multiple(
                    request.user.id,
                    [user_admin.id],
                    "Tentative de double paiement",
                    f"invoice_id={invoice.id}"
                )
                messages.error(request, "Une incohérence a été détectée. Contactez le support.")
                return redirect("eleve_demande_paiement")

    except Exception as e:
        logger.error(f"[{request.user}] ❌ Erreur préparation facture : {e}")
        messages.error(request, "Erreur lors de la préparation du paiement.")
        return redirect("eleve_demande_paiement")

    # ----------------------------------------------------------------------
    # 4. CONSTRUCTION DES LINE_ITEMS STRIPE
    # ----------------------------------------------------------------------
    line_items = []
    try:
        for item in cart.items.all():
            line_items.append({
                "price_data": {
                    "currency": "eur",
                    "product_data": {"name": item.cours},
                    "unit_amount": item.price,
                },
                "quantity": 1,
            })
    except Exception as e:
        logger.error(f"[{request.user}] ❌ Erreur line_items : {e}")
        messages.error(request, "Erreur lors de la préparation des articles.")
        return redirect("eleve_demande_paiement")

    # ----------------------------------------------------------------------
    # 5. CRÉATION SESSION STRIPE
    # ----------------------------------------------------------------------
    try:
        checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=line_items,
        mode="payment",
        success_url=request.build_absolute_uri(
            reverse("payment:success")
        ) + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=request.build_absolute_uri(
            reverse("payment:cancel")
        ),

        # Metadata sur la Checkout Session
        metadata={
            "invoice_id": str(invoice.id),
            "user_id": str(request.user.id),
        },

        # ⭐ Metadata sur le PaymentIntent (ESSENTIEL)
        payment_intent_data={
            "metadata": {
                "invoice_id": str(invoice.id),
                "user_id": str(request.user.id),
            }
        },

        expires_at=int(
            (timezone.now() + timezone.timedelta(hours=23, minutes=55)).timestamp()
        ),)


        logger.info(f"[{request.user}] ➤ Session Stripe créée ({checkout_session.id})")

        invoice.stripe_id = checkout_session.id
        invoice.save()

    except Exception as e:
        logger.error(f"[{request.user}] ❌ Erreur création session Stripe : {e}")
        messages.error(request, "Erreur lors de la création de la session Stripe.")
        return redirect("eleve_demande_paiement")

    # ----------------------------------------------------------------------
    # 7. REDIRECTION VERS STRIPE
    # ----------------------------------------------------------------------
    return redirect(checkout_session.url)




@login_required
def payment_success(request):
    """
    Vue exécutée après la redirection Stripe vers /payment/success/
    
    Rôle :
        ✔ Récupérer la session Stripe
        ✔ Vérifier qu’elle contient une facture valide
        ✔ Vérifier la cohérence utilisateur / metadata
        ✔ Vérifier que le paiement est confirmé
        ✔ Créer ou mettre à jour un Payment interne
        ✔ Nettoyer le panier
        ✔ Notifier admin, professeur, élève
        ✔ Afficher success.html

    ⚠️ IMPORTANT :
        La confirmation réelle (charge.succeeded) viendra du webhook.
        Ici on prépare uniquement les données internes.
    """

    user = request.user
    user_admin = User.objects.filter(is_staff=True, is_active=True).first()
    session_id = request.GET.get("session_id")

    if not session_id:
        logger.warning("Accès à /payment/success sans session_id")
        return render(request, "payment/success.html")

    try:
        # ─────────────────────────────────────────────
        # 1) Récupération session Stripe
        # ─────────────────────────────────────────────
        session = stripe.checkout.Session.retrieve(session_id)
        # logger.info(f"[{request.user}] ➤ Session Stripe créée ({session.id})") 
        # même si ce n#est pas un Webhook c#est intéressant de garderune trace
        stripe_event, _ = WebhookEvent.objects.get_or_create(event_id=session.get("id"),
                defaults={
                    "type": session.get("object"),
                    "payload": session,
                    "handle_log": f"[{request.user}] ➤ ** Session Stripe créée ({session.id})",
                    "is_processed": True,
                })

        # Session => metadata
        metadata = session.metadata or {}
        invoice_id = metadata.get("invoice_id")
        user_id = metadata.get("user_id")
        stripe_payment_intent_id = session.get("payment_intent") # id du pament de Stripe très important

        # ─────────────────────────────────────────────
        # 2) Contrôles préliminaires
        # ─────────────────────────────────────────────

        # Vérifier invoice_id dans metadata
        if not invoice_id:
            msg = "invoice_id absent dans metadata Stripe"
            logger.warning(f"❌ {msg}")
            append_webhook_log(stripe_event, f"❌ {msg}")
            messages.error(request, "Identifiant de facture introuvable.")
            envoie_email_multiple(user.id, [user_admin.id],
                "Tentative ou suspicion d'incohérence",
                msg)
            return render(request, "payment/success.html")

        # Vérifier cohérence user / metadata
        expected_user = User.objects.filter(id=user_id).first()
        if expected_user != user:
            msg = "user_id dans metadata Stripe différent du request.user"
            logger.warning(f"❌ {msg}")
            append_webhook_log(stripe_event, f"❌ {msg}")
            messages.error(request, msg)
            envoie_email_multiple(user.id, [user_admin.id],
                "Tentative ou suspicion d'incohérence",
                msg)
            return render(request, "payment/success.html")

        # ─────────────────────────────────────────────
        # 3) Récupération de la facture
        # ─────────────────────────────────────────────
        try:
            invoice = Invoice.objects.get(id=invoice_id, user=user)
        except Invoice.DoesNotExist:
            msg = f"Facture introuvable en base : id={invoice_id}"
            logger.error(f"❌ {msg}")
            append_webhook_log(stripe_event, f"❌ {msg}")
            messages.error(request, "Facture introuvable.")
            envoie_email_multiple(user.id, [user_admin.id],
                "Erreur facture introuvable", msg)
            return render(request, "payment/success.html")

        # logger.info(f"🔔 Traitement du paiement pour facture {invoice_id} / user {user.id}")
        append_webhook_log(stripe_event, f"🔔 Traitement du paiement pour facture {invoice_id} / user {user.id}")

        # ─────────────────────────────────────────────
        # 4) Vérification du statut Stripe
        # ─────────────────────────────────────────────
        if session.payment_status != "paid":
            # logger.warning(f"⚠ Paiement non confirmé : {session.payment_status}")
            append_webhook_log(stripe_event, f"⚠ Paiement non confirmé : {session.payment_status}")
            messages.warning(request, "Paiement non encore confirmé.")
            return render(request, "payment/success.html")

        # ─────────────────────────────────────────────
        # 4) Mis à jour invoice
        # ─────────────────────────────────────────────
        if stripe_payment_intent_id:
            invoice.stripe_payment_intent_id = stripe_payment_intent_id # très important pour le suivi du paiement
            invoice.save()
        else:
            msg = "ID du paiement n'est pas fourni par Stripe (On peut le rècupérer par les WebHook)"
            logger.warning(f"❌ {msg}")
            append_webhook_log(stripe_event, f"❌ {msg}")

        # ─────────────────────────────────────────────
        # 5) Vérification du montant payé
        # ─────────────────────────────────────────────
        amount_stripe = session.amount_total
        amount_invoice = invoice.total  # en centimes
        append_webhook_log(stripe_event,
            f"Montant Stripe = {amount_stripe} centimes | "
            f"Montant facture = {amount_invoice} centimes"
        )

        coherent = verifier_coherence_montants(
            texte1="Stripe Session",
            texte2="Demande de paiement",
            montant1=amount_stripe,
            montant2=amount_invoice,
            abs_tol=5,
            user_admin=user_admin,
        )

        if not coherent:
            msg = (
                f"Incohérence montants : Stripe={amount_stripe}c "
                f"vs Facture={amount_invoice}c"
            )
            # logger.info(msg)
            append_webhook_log(stripe_event, f"❌ {msg}")
            envoie_email_multiple(
                user.id, [user_admin.id],
                "Incohérence de montant",
                msg
            )

        # ─────────────────────────────────────────────
        # 6) Nettoyage du panier
        # ─────────────────────────────────────────────
        cart = Cart.objects.filter(user=user).first()
        if cart:
            cart.items.all().delete()
            cart.delete()
            logger.info("🧹 Panier vidé après paiement.")

        try:
            eleve_obj = Eleve.objects.get(user=user)
        except Eleve.DoesNotExist:
            msg = f"⚠ Aucun profil Eleve associé à user.id={user.id}"
            # logger.info(msg)
            append_webhook_log(stripe_event, msg)
            messages.error(request, "Profil élève introuvable. Contactez l'administration.")
            envoie_email_multiple(user.id, [user_admin.id],
                                "Erreur paiement : profil élève manquant",
                                msg)
            return render(request, "payment/success.html")
        
        try:
            user_prof = invoice.demande_paiement.user
            professeur_obj = Professeur.objects.get(user=user_prof)
        except Professeur.DoesNotExist:
            msg = f"⚠ Aucun profil Professeur associé à user_prof={user_prof.id}"
            # logger.info(msg)
            append_webhook_log(stripe_event, msg)
            messages.error(request, "Profil professeur introuvable. Contactez l'administration.")
            envoie_email_multiple(user.id, [user_admin.id],
                                "Erreur paiement : profil professeur manquant",
                                msg)
            return render(request, "payment/success.html")

        # ─────────────────────────────────────────────
        # 8) Création / mise à jour Payment interne
        # ─────────────────────────────────────────────
        payment = Payment.objects.filter(invoice=invoice).first()
        if payment: # pour ne pas écraser le status et garentir la mise à jour des champs important
            payment.eleve=eleve_obj
            payment.professeur=professeur_obj
            payment.reference=stripe_payment_intent_id if stripe_payment_intent_id else payment.reference
            payment.save()
            append_webhook_log(stripe_event, f"Mise à jour Payment payment.id = {payment.id} / payment.eleve={eleve_obj} / payment.professeur={professeur_obj} / payment.reference={stripe_payment_intent_id}.")
        else:
            payment, created = Payment.objects.update_or_create(
                invoice=invoice,
                defaults={
                    "eleve": eleve_obj,
                    "professeur": professeur_obj,
                    "status": Payment.PENDING,  # Webhook confirmera
                    "amount": round(amount_stripe / 100, 2),
                    "currency": session.currency  ,
                    "reference": stripe_payment_intent_id if stripe_payment_intent_id else None,
                }
            )

            if created:
                # logger.info(f"✅ Payment créé : {payment.id}")
                append_webhook_log(stripe_event, f"✅ Payment créé : {payment.id}")
            else:
                # logger.info(f"♻ Payment mis à jour : {payment.id}")
                append_webhook_log(stripe_event, f"♻ Payment mis à jour : {payment.id}")
        
            # ─────────────────────────────────────────────
            # 9) Mise à jour demande de paiement En cours
            # ─────────────────────────────────────────────
            demande_paiement = invoice.demande_paiement
            if demande_paiement:
                demande_paiement.statut_demande = Demande_paiement.EN_COURS
                demande_paiement.save()
                append_webhook_log(
                    stripe_event,
                    f"✅ Demande de paiement mise à jour : {demande_paiement.id}"
                )
            else:
                append_webhook_log(
                    stripe_event,
                    "❌ Invoice sans demande_paiement associée"
                )
            # ─────────────────────────────────────────────
            # 9) Email professeur + admin
            # ─────────────────────────────────────────────
            dp = invoice.demande_paiement

            sujet = (
                f"Paiement confirmé : {user.first_name} {user.last_name} "
                f"a réglé la demande du {dp.date_creation.strftime('%d/%m/%Y')}"
            )
            texte = (
                f"Bonjour {professeur_obj.user.first_name},\n\n"
                f"L'élève {user.first_name} {user.last_name} a réglé "
                f"la demande du {dp.date_creation.strftime('%d/%m/%Y')} "
                f"pour un montant de {dp.montant:.2f} €.\n\n"
                f"Nous vous informerons dès que le montant sera disponible dans nos comptes.\n\n"
                f"Cordialement,\nAdministration"
            )

            result = envoie_email_multiple(
                user.id, [professeur_obj.user.id, user_admin.id],
                sujet, texte
            )

            if result.get("erreurs"):
                # logger.error("⚠ Erreurs d'envoi email confirmation professeur.")
                append_webhook_log(stripe_event, "⚠ Erreurs d'envoi email confirmation professeur.")

        # ─────────────────────────────────────────────
        # 10) Nettoyage session locale
        # ─────────────────────────────────────────────
        for key in ("payment_id", "prof_id", "demande_paiement_id_decript"):
            request.session.pop(key, None)
        # logger.info(f"Affichage success avec facture {invoice.id}")
        append_webhook_log(stripe_event, f"Affichage success avec facture {invoice.id}")
        messages.info(request, f"Paiement enregistré pour la facture #{invoice.id}")
        return render(request, "payment/success.html", {
            "invoice": invoice,
            "total_euro": f"{invoice.total / 100:.2f}"
        })

    except stripe.error.StripeError as e:
        logger.exception(f"Erreur Stripe lors du paiement {str(e)} ")
        messages.error(request, f"Erreur de communication avec Stripe. {str(e)}")
    except Exception as e:
        logger.exception(f"Erreur inattendue dans payment_success {str(e)}")
        messages.error(request, f"Erreur inattendue. Merci de contacter l’administrateur. {str(e)}")

    # ─────────────────────────────────────────────
    # Affichage sans facture si erreur
    # ─────────────────────────────────────────────
    return render(request, "payment/success.html")




@login_required
def payment_cancel(request):
    """
    Vue appelée lorsque l'utilisateur annule ou quitte la page de paiement Stripe.

    Objectifs :
    - Vérifier l’intégrité et la cohérence de la session Stripe
    - Mettre à jour le statut de la facture (Invoice)
    - Remettre la demande de paiement associée en état cohérent
    - Informer l'utilisateur et notifier l'administration si anomalie
    - Enregistrer les traces dans WebhookEvent pour audit
    """
    #######################################################################
    # Option avec teste local
    invoice_id="266"
    id_teste="cs_test_a10gq4qXBiKBw17YmE3SnqgJ2mqXBV16wwFtvfkCIo8EyDFirvi88EajWd"
    metadata_user_id="84"
    cancellation_reason = "abandoned"
    payment_intent = {
            "id": "pi_3N0koZJsT1xl4ocx1oYeqgkT",
            "status": "requires_payment_method",
            "canceled_at": 1700932321,
            "cancellation_reason": cancellation_reason,
            "charges": {"data": []}
        }
    
    # juste pour les tests locaux
    from types import SimpleNamespace

    def dict_to_obj(d):
        if isinstance(d, dict):
            return SimpleNamespace(**{k: dict_to_obj(v) for k, v in d.items()})
        elif isinstance(d, list):
            return [dict_to_obj(x) for x in d]
        return d

    session_dict = {
        "id": id_teste,
        "object": "checkout.session",
        "metadata": {
            "invoice_id": invoice_id,
            "user_id": metadata_user_id,
            "slug": "PAI-12-75-2023"
        },
        "payment_status": "unpaid",
        "status": "open",
        "payment_intent": payment_intent
    }

    session = dict_to_obj(session_dict)
    session_id = session.id


    # Option sans teste local
    session_id = request.GET.get('session_id')
    payment_intent= None

    #######################################################################
    user = request.user
    user_admin = User.objects.filter(is_staff=True, is_active=True).first()
    logger.warning(f"request : {request}")

    # Le WebhookEvent est créé plus bas, mais on le déclare ici
    stripe_event = None

    # ─────────────────────────────────────────────
    # 0) Vérification de base : présence du session_id
    # ─────────────────────────────────────────────
    if not session_id:
        logger.warning("Accès à /payment/cancel sans session_id")
        messages.error(request, "Session Stripe introuvable.")
        return render(request, "payment/cancel.html")
    logger.debug(f"session_id= {session_id}")
    try:
        # ─────────────────────────────────────────────
        # 1) Récupération de la session Stripe
        # ─────────────────────────────────────────────
        ###############################################
        # Option sans teste local
        session = stripe.checkout.Session.retrieve(
            session_id,
            expand=['payment_intent'] # elle remplace: payment_intent = stripe.PaymentIntent.retrieve(session.payment_intent)
        )
        ###############################################
        
        # Journalisation sous forme d'événement interne
        stripe_event, _ = WebhookEvent.objects.get_or_create(
            event_id=session.id,
            defaults={
                "type": session.object,
                "payload": session, # à vérifier
                "handle_log": f"[{user}] ➤ Détection payment_cancel pour session {session.id}",
                "is_processed": True,
            }
        )

        # ─────────────────────────────────────────────
        # 2) Vérifier les metadata Stripe (cohérence)
        # ─────────────────────────────────────────────
        metadata = session.metadata or {}
        invoice_id = metadata.get("invoice_id")
        metadata_user_id = metadata.get("user_id")
        

        if not invoice_id:
            return _handle_error_cancel(
                request=request,
                stripe_event=stripe_event,
                msg="invoice_id absent dans metadata Stripe",
                user=user,
                user_admin=user_admin,
            )

        if str(metadata_user_id) != str(user.id):
            return _handle_error_cancel(
                request=request,
                stripe_event=stripe_event,
                msg="user_id dans metadata Stripe différent de request.user",
                user=user,
                user_admin=user_admin,
            )

        # ─────────────────────────────────────────────
        # 3) Récupération de la facture
        # ─────────────────────────────────────────────
        try:
            invoice = Invoice.objects.get(id=invoice_id, user=user)
        except Invoice.DoesNotExist:
            return _handle_error_cancel(
                request=request,
                stripe_event=stripe_event,
                msg=f"Facture introuvable pour id={invoice_id}",
                user=user,
                user_admin=user_admin,
            )

        # Log
        append_webhook_log(
            stripe_event,
            f"🔔 Annulation Stripe : status={session.status}, payment_status={session.payment_status}"
        )

        # ─────────────────────────────────────────────
        # 4) Analyse des cas de cancellation Stripe
        # ─────────────────────────────────────────────

        # 🟢 CAS 3 : webhook est arrivé AVANT (paiement déjà reçu)
        if invoice.status == "paid":
            msg = "🔔 Paiement déjà validé (webhook arrivé avant cancel)"
            messages.info(request, msg)
            logger.warning(msg)
            append_webhook_log(stripe_event, msg)
            envoie_email_multiple(
                user.id, [user_admin.id], "Webhook avant cancel",
                f"{msg}\nsession={session.id}\ninvoice={invoice.id}"
                "🔔 A vérifier absolument par l'admin"
            )
            return render(request, "payment/cancel.html")

        # 🟠 CAS 1 : l'utilisateur ferme ou quitte = session OPEN / unpaid
        if session.status == "open" and session.payment_status == "unpaid":
            _cancel_invoice(invoice, session, payment_intent)
            messages.warning(request, "Vous avez quitté la page de paiement avant de valider.")
            append_webhook_log(stripe_event, f"[{user}] ➤ Paiement abandonné.")
            return render(request, "payment/cancel.html")

        # 🔴 CAS 2 : session terminée sans paiement (expired ou complete+unpaid)
        if session.payment_status == "unpaid" and session.status in ["expired", "complete"]:
            _cancel_invoice(invoice, session, payment_intent)
            messages.error(request, "Votre paiement a échoué ou a été refusé.")
            append_webhook_log(stripe_event, f"[{user}] ⚠️ Paiement échoué.")
            return render(request, "payment/cancel.html")

        

        # ⚠ CAS INATTENDU
        msg = (
            f"Annulation inattendue : status={session.status}, "
            f"payment_status={session.payment_status}"
        )
        logger.warning(msg)
        messages.warning(request, "Annulation inattendue lors du paiement.")
        append_webhook_log(stripe_event, msg)

        envoie_email_multiple(
            user.id,
            [user_admin.id],
            "Annulation Stripe inattendue",
            msg
        )

    except stripe.error.StripeError as e:
        logger.error(f"❌ Erreur Stripe : {e.user_message}")
        messages.error(request, "Erreur Stripe pendant l'annulation du paiement.")
        if stripe_event:
            append_webhook_log(stripe_event, f"❌ {e.user_message}")

    except Exception as e:
        logger.error(f"❌ Exception payment_cancel : {e}")
        messages.error(request, "Erreur interne lors de l'annulation.")
        if stripe_event:
            append_webhook_log(stripe_event, f"❌ Exception : {e}")

    return render(request, "payment/cancel.html")

def _handle_error_cancel(request, stripe_event, msg, user, user_admin):
    logger.warning(f"❌ {msg}")
    append_webhook_log(stripe_event, f"❌ {msg}")
    messages.error(request, msg)

    envoie_email_multiple(
        user.id, [user_admin.id],
        "Erreur ou incohérence détectée via payment_cancel",
        msg
    )
    return render(request, "payment/cancel.html")

def _cancel_invoice(invoice, session, payment_intent=None):
    invoice.status = Invoice.CANCELED
    if not payment_intent: invoice.cancellation_reason = session.payment_intent["cancellation_reason"]
    if payment_intent: invoice.cancellation_reason = payment_intent["cancellation_reason"]
    invoice.save()

    if hasattr(invoice, "demande_paiement") and invoice.demande_paiement:
        invoice.demande_paiement.statut_demande = Demande_paiement.EN_ATTENTE
        invoice.demande_paiement.save()







##############################
# STRIPE API AccountLink
##############################


@login_required
def compte_stripe(request):
    # Par défaut, on considère que le compte Stripe n'est pas encore créé
    account_status = "not_created"

    try:
        # Récupération du professeur lié à l'utilisateur connecté
        professeur = Professeur.objects.get(user=request.user)

        # Cas 1 : compte créé ET onboarding terminé
        if professeur.stripe_account_id and professeur.stripe_onboarding_complete: 
            account_status = "completed_active"

        # Cas 2 : compte créé MAIS onboarding incomplet
        if professeur.stripe_account_id and not professeur.stripe_onboarding_complete: 
            account_status = "created_incomplete"

    except Professeur.DoesNotExist:
        # Si l'utilisateur n'est pas un professeur, accès refusé
        messages.error(request, "Vous devez être un professeur pour accéder à cette page.")
        return redirect("index")

    # Fonction utilitaire interne pour générer un lien Stripe (onboarding ou update)
    def _create_account_link(request, account_id, request_type):
        try:
            # URL de redirection si l'utilisateur interrompt le processus
            # on a ajouté "?account_status=created_incomplete" pour l'utiliser comme 
            # paramètre de test à partir de la reponse de Stripe
            refresh_url = request.build_absolute_uri(
                reverse("payment:compte_stripe") + "?account_status=created_incomplete"
            )
            # URL de redirection si l'utilisateur termine le processus avec succès
            return_url = request.build_absolute_uri(
                reverse("payment:compte_stripe") + f"?account_status=completed_active&{request_type}=success"
            )

            # Création d'un lien Stripe AccountLink pour l'onboarding ou l'update
            account_link = stripe.AccountLink.create(
                account=account_id,
                refresh_url=refresh_url,
                return_url=return_url,
                type=request_type,
            )

            logger.info(f"Lien Stripe créé avec succès: {account_link.url}")
            return account_link.url  # Retourne uniquement l'URL à rediriger

        except stripe.error.StripeError as e:
            # Gestion des erreurs Stripe (ex: problème API ou paramètres invalides)
            logger.error(f"Erreur création AccountLink: {str(e)}")
            logger.error(f"Détails - account_id: {account_id}, type: {request_type}")
            if hasattr(e, "json_body"):
                logger.error(f"Réponse Stripe: {e.json_body}")
            
            messages.error(request, f"Erreur lors de la création du lien Stripe: {str(e)}")
            return None
            
        except Exception as e:
            # Gestion de toute autre erreur imprévue
            logger.error(f"Erreur inattendue dans _create_account_link: {str(e)}")
            messages.error(request, "Une erreur inattendue s'est produite.")
            return None

    # -------------------------
    # Gestion des requêtes POST
    # -------------------------
    if request.method == "POST":

        # ✅ Création initiale d’un compte Stripe Express
        if "creation_compte" in request.POST:
            try:
                # Création du compte Stripe Express
                account = stripe.Account.create(
                    type="express",
                    country="FR",  # Pays du professeur
                    email=request.user.email,  # Email associé
                    capabilities={  # Permissions demandées
                        "card_payments": {"requested": True},
                        "transfers": {"requested": True},
                    },
                    business_type="individual",  # Compte individuel (pas société)
                    individual={
                        "first_name": request.user.first_name or "",
                        "last_name": request.user.last_name or "",
                        "email": request.user.email,
                    },
                )

                # Sauvegarde des informations du compte Stripe dans la base
                professeur.stripe_account_id = account.id
                professeur.stripe_onboarding_complete = False
                professeur.save()

                # Rafraîchir l'objet professeur depuis la base (sécurité)
                professeur.refresh_from_db()

                # Génération du lien d’onboarding Stripe
                account_link_url = _create_account_link(request, account.id, "account_onboarding")
                if account_link_url:
                    return redirect(account_link_url)
                else:
                    messages.error(request, "Erreur lors de la création du lien Stripe")
                    return redirect('payment:compte_stripe')

            except stripe.error.StripeError as e:
                # Gestion des erreurs Stripe à la création de compte
                logger.error(f"Erreur création compte Stripe: {str(e)}")
                messages.error(request, f"Erreur lors de la création du compte: {str(e)}")
                return redirect('payment:compte_stripe')
        
        # ✅ Finalisation du compte (si déjà créé mais incomplet)
        elif "finalize_compte" in request.POST and professeur.stripe_account_id:
            account_link_url = _create_account_link(request, professeur.stripe_account_id, "account_onboarding")
            if account_link_url:
                return redirect(account_link_url)
            messages.error(request, "Impossible de générer le lien Stripe.")
            return redirect('payment:compte_stripe')
        
        # ✅ Mise à jour du compte (modification d’infos ou ajout documents)
        elif "update_compte" in request.POST and professeur.stripe_account_id:
            try:
                # Récupération de l’état du compte Stripe actuel
                account = stripe.Account.retrieve(professeur.stripe_account_id)
                
                # Cas production : si le compte est actif et validé
                if account.details_submitted and account.charges_enabled:
                    # On utiliserait normalement "account_update"
                    # account_link_url = _create_account_link(request, professeur.stripe_account_id, "account_update")
                    
                    # Ici on garde "account_onboarding" car c’est un compte de test
                    account_link_url = _create_account_link(request, professeur.stripe_account_id, "account_onboarding")
                else:
                    # Si l’onboarding n’est pas terminé → rediriger vers onboarding
                    account_link_url = _create_account_link(request, professeur.stripe_account_id, "account_onboarding")
                
                if account_link_url:
                    return redirect(account_link_url)
                else:
                    messages.error(request, "Impossible de générer le lien Stripe.")
                    return redirect('payment:compte_stripe')
                    
            except stripe.error.StripeError as e:
                # En cas d’erreur lors de la récupération du compte
                logger.error(f"Erreur vérification compte Stripe: {str(e)}")
                # Fallback : on renvoie vers onboarding
                account_link_url = _create_account_link(request, professeur.stripe_account_id, "account_onboarding")
                if account_link_url:
                    return redirect(account_link_url)
                messages.error(request, "Erreur lors de la mise à jour du compte.")
                return redirect('payment:compte_stripe')

        # ✅ Désactivation du compte (supprimer le compte Stripe associé)
        elif "desactiver_compte" in request.POST and professeur.stripe_account_id:
            try:
                # Suppression du compte Stripe côté API
                stripe.Account.delete(professeur.stripe_account_id)

                # Réinitialisation des infos côté base
                professeur.stripe_account_id = None
                professeur.stripe_onboarding_complete = False
                professeur.save()
                
                # Rafraîchir les données
                professeur.refresh_from_db()
                
                messages.success(request, "Votre compte Stripe a été désactivé avec succès.")
                return redirect("payment:compte_stripe")

            except stripe.error.StripeError as e:
                logger.error(f"[Stripe] Erreur désactivation compte {professeur.stripe_account_id}: {str(e)}")
                messages.error(request, "Erreur lors de la désactivation du compte.")
                return redirect('payment:compte_stripe')

    # -------------------------
    # Gestion des paramètres GET (retour de Stripe après redirection)
    # -------------------------
    if 'account_status' in request.GET:
        account_status = request.GET.get('account_status')
        if account_status == "completed_active":
            # Mise à jour du statut en base (onboarding terminé avec succès)
            professeur.stripe_onboarding_complete = True
            professeur.save()

    # -------------------------
    # Contexte envoyé au template
    # -------------------------
    context = {
        "account_status": account_status,
    }

    return render(request, "payment/compte_stripe.html", context)










##########################################################
# STRIPE API PaymentIntent.retrieve (paiement récupérer)
##########################################################

@require_POST
@secure_stripe_action("refund_payment")  # 🔐 Sécurise l'action (anti double soumission / droits admin)
def refund_payment(request):
    """
    🔄 Lance les remboursements Stripe (totaux ou partiels) 
    à partir d'un AccordRemboursement validé par l'administrateur.
    """

    # 📌 Récupération de l'ID de l'accord depuis la session
    accord_id = request.session.get('accord_id')

    # 📌 Chargement de l'accord de remboursement
    accord = AccordRemboursement.objects.filter(id=accord_id).first()

    # ❌ Aucun accord trouvé → arrêt immédiat
    if not accord:
        messages.error(request, "Aucun accord de remboursement trouvé.")
        return redirect('admin_remboursement_detaille')

    # 📌 Récupération des détails de remboursement associés à l'accord
    details = DetailAccordRemboursement.objects.filter(accord=accord)

    # 📌 Récupération des paiements concernés par ces détails
    payments = Payment.objects.filter(id__in=details.values_list('payment', flat=True))

    # ❌ Aucun paiement associé → rien à rembourser
    if not payments.exists():
        messages.error(request, "Il n'y a pas de paiement à rembourser.")
        return redirect('admin_remboursement_detaille') 

    # 🔍 Vérification métier : seuls les paiements approuvés peuvent être remboursés
    for payment in payments:
        if payment.status != Payment.APPROVED:
            messages.error(request, "Paiement non remboursable (statut incorrect).")
            return redirect('admin_remboursement_detaille')

    # 📦 Liste tampon contenant toutes les informations nécessaires 
    # pour lancer les remboursements Stripe
    payment_amount_refunds = []

    # 🔄 Parcours de chaque détail de remboursement
    for detail in details:
        # 💶 Montant à rembourser en euros
        amount_eur = detail.refunded_amount or Decimal('0.00')

        # 🔢 Conversion en centimes (Stripe travaille uniquement en entiers)
        amount_cents = to_cents(amount_eur)

        # 💳 Paiement concerné
        payment = detail.payment

        # ❌ Sécurité : montant invalide
        if amount_cents <= 0:
            messages.error(request, "Montant invalide.")
            return redirect('admin_remboursement_detaille')

        try:
            charge = None  # Charge Stripe à retrouver

            # ===========================
            # CAS 1 : Paiement via PaymentIntent
            # ===========================
            if payment.invoice:
                charge_id = payment.invoice.stripe_charge_id
                # 🔍 Récupération du PaymentIntent Stripe
                charge = stripe.Charge.retrieve(charge_id)

            # ===========================
            # CAS 2 : Aucun identifiant Stripe connu
            # ===========================
            else:
                messages.error(request, "Pas d'identifiant Stripe trouvé.")
                return redirect('admin_remboursement_detaille')

            # ❌ Aucune charge récupérée → impossible de rembourser
            if not charge:
                messages.error(request, f"Aucune charge trouvée pour ce paiement ID = {payment.id}.")
                return redirect('admin_remboursement_detaille')

            # 💰 Calcul du montant encore remboursable sur la charge
            refundable = charge['amount'] - charge.get('amount_refunded', 0)

            # ❌ Tentative de remboursement supérieur au montant disponible
            if amount_cents > refundable:
                messages.error(request, "Montant supérieur au montant remboursable.")
                return redirect('admin_remboursement_detaille')

            # ✅ Stockage temporaire des données valides pour le remboursement final
            payment_amount_refunds.append({
                "payment": payment,
                "amount_eur": amount_eur,
                "charge_id": charge['id'],
                "amount_cents": amount_cents,
                "accord": detail.accord
            })

        # ❌ Erreur Stripe (API, réseau, permissions…)
        except stripe.error.StripeError as e:
            messages.error(request, f"Erreur Stripe: {str(e)}")
            return redirect('admin_remboursement_detaille')

    # ==================================================
    # 🎯 Lancement effectif des remboursements Stripe
    # ==================================================
    for enr in payment_amount_refunds:
        # 🗂 Création d'un enregistrement local de remboursement
        refund_record = RefundPayment.objects.create(
            payment=enr["payment"],
            montant=enr["amount_eur"],
            status=RefundPayment.PENDING,
            
        )

        # 🔐 Idempotency key : empêche les doublons Stripe ( ✔️ Garantie unique ✔️ Stable ✔️ Liée à la base de données ✔️ Compatible remboursements multiples )
        idempotency_key = f"refund_{payment.id}_{refund_record.id}"

        try:
            # 🔄 Création du remboursement Stripe
            stripe_refund = stripe.Refund.create(
                charge=enr["charge_id"],
                amount=enr["amount_cents"],
                reason='requested_by_customer',
                metadata={'local_refund_id': refund_record.id},
                idempotency_key = idempotency_key
            )

            # ✅ Mise à jour du remboursement local
            refund_record.stripe_refund_id = stripe_refund.id
            refund_record.save()

            # 📢 Message succès admin
            messages.success(
                request,
                f"✅ Remboursement de {enr['amount_eur']}€ initié — Stripe Refund ID : {stripe_refund.id}"
            )

            # 🔄 Mise à jour du statut de l'accord de remboursement
            accord = enr["accord"]
            accord.status = AccordReglement.IN_PROGRESS
            accord.save()

        # ❌ Échec Stripe sur un remboursement spécifique
        except stripe.error.StripeError as e:
            refund_record.status = RefundPayment.FAILED
            refund_record.save()
            messages.error(request, f"❌ Refund échoué : {str(e)}")

    # 🔁 Retour vers la page de détail admin
    return redirect('admin_remboursement_detaille')




#########################
# STRIPE API Transfer
#########################

@login_required
@user_passes_test(is_admin)
@secure_stripe_action("create_transfert_session")  # <<< sécurité globale
def create_transfert_session(request):
    """
    Lance un transfert Stripe (validation finale par Webhook)
    céation de InvoiceTransfert
    Céation  stripe.Transfer.create
    Création de WebhookEvent
    mise à jour InvoiceTrransfet
    Mise à jour Accord_reglement
    Pas de création de Transfer que après handle_transfer_created

    """
    try:
        # --- VALIDATIONS ---
        cart = CartTransfert.objects.filter(user_admin=request.user).first()
        if not cart or not cart.items.exists():
            return JsonResponse({'error': f"Panier vide ou inexistant: {str(e)}"}, status=404)

        prof = get_object_or_404(Professeur, user=cart.user_professeur)

        # --- FACTURE EN BROUILLON --- on peut la créer lorsque le Webhook confirme le transfert
        invoice = InvoiceTransfert.objects.create(
            user_admin=request.user,
            user_professeur=prof.user,
            status=InvoiceTransfert.DRAFT,
            total=cart.total / 100,
            accord_reglement=cart.accord_reglement,
        )

        # --- TRANSFERT STRIPE ---
        try:
            transfert = stripe.Transfer.create(
                amount=cart.total,
                currency="eur",
                destination=prof.stripe_account_id,
                description=f"Transfert Facture {invoice.invoice_number}",
                metadata={"invoice_id": invoice.id}
            )
            

        except stripe.error.InvalidRequestError as e:
            return handle_stripe_error(request, e, transfert_id) # on a enlever invoice pour empécher sa mise à jour en tant que FAILED

        except stripe.error.StripeError as e:
            return handle_stripe_error(request, e,transfert_id, invoice) # pour permettre la mise à jour de invoice FAILED

        #################################################
        # Webhoo
        #################################################
        # 3️⃣ Création ou récupération de l’événement Webhook
        transfert_id = transfert.get("id")
        stripe_event, _ = WebhookEvent.objects.get_or_create(event_id=transfert_id,
                defaults={
                    "type": transfert.get("object"),
                    "payload": transfert,
                    "handle_log": f"[{request.user}] ➤ Transfert Stripe créée ({transfert.id})",
                    "is_processed": True,
                })
        
        #################################################
        # 3️⃣ Vérifications des données Stripe
        #################################################

        stripe_amount = transfert.get("amount")
        stripe_destination = transfert.get("destination")
        stripe_metadata_invoice_id = transfert.get("metadata", {}).get("invoice_id")

        errors = []

        # Vérifier le montant envoyé à Stripe
        coherent = verifier_coherence_montants(
                    texte1="create_transfert_session",
                    texte2="Invoice BDD",
                    montant1=stripe_amount,
                    montant2=cart.total,
                    abs_tol=5,
                    user_admin=request.user
                )
        if not coherent:
            append_webhook_log(stripe_event,
                    f"💥 Incohérence critique invoice.toal={cart.total} centimes dans BDD\n"
                    f"data_object.get('amount')={stripe_amount} centime d'évènement charge.succeeded"
                    )
            logger.warning(
                f"💥 Incohérence critique invoice.toal={cart.total} centimes dans BDD\n"
                f"data_object.get('amount')={stripe_amount} centime d'évènement charge.succeeded"
                )
            errors.append(
                f"💥 Incohérence critique invoice.toal={cart.total} centimes dans BDD\n"
                f"data_object.get('amount')={stripe_amount} centime d'évènement charge.succeeded"
            )

        # Vérifier le compte Stripe du prof
        if stripe_destination != prof.stripe_account_id:
            errors.append(
                f"Compte Stripe du professeur non conforme: Stripe={stripe_destination} // DB={prof.stripe_account_id}"
            )

        # Vérifier invoice_id de metadata
        if str(stripe_metadata_invoice_id) != str(invoice.id):
            errors.append(
                f"Invoice ID metadata invalide: Stripe={stripe_metadata_invoice_id} // DB={invoice.id}"
            )

        if errors:
            # ⚠️ Marquer la facture comme failed
            invoice.status = InvoiceTransfert.FAILED
            invoice.save()

            # Logger les erreurs dans le WebhookEvent
            append_webhook_log(stripe_event, "⛔ " + " | ".join(errors))

            envoie_email_multiple(request.user.id,[request.user.id], "Non conformité des données Stripe", "⛔ " + " | ".join(errors))
            return JsonResponse({
                "error": "Transfert Stripe non conforme; à corriger immédiatement",
                "details": errors
            }, status=400)

        
        # --- MAJ (EN ATTENTE WEBHOOK) sans PDF---
        invoice.stripe_transfer_id = transfert_id
        invoice.frais = 0
        invoice.montant_net=cart.total / 100
        invoice.status = InvoiceTransfert.INPROGRESS
        invoice.save()
        append_webhook_log(stripe_event, f"🔔 .PENDING invoice_id:{invoice.id} ")

        #6. mise à jour AccordReglement 
        accord_reglement = cart.accord_reglement
        accord_reglement.status = AccordReglement.IN_PROGRESS 
        accord_reglement.save()
        append_webhook_log(stripe_event, f"🔔 AccordReglement.IN_PROGRESS ID:{accord_reglement.id} ")

        request.session['invoice_transfert_id'] = invoice.id
        return redirect('payment:transfert_success')

    except Exception as e:
        logger.exception("Erreur critique transfert")
        messages.info(request, f"Erreur critique transfert{str(e)} ")
        return handle_stripe_error(request,e, transfert_id)


def handle_stripe_error(request, e, transfert_id, invoice_transfert=None):
    """
    Gère proprement les erreurs Stripe et met à jour la facture si nécessaire.
    Capture automatiquement :
      - message utilisateur
      - message technique
      - code Stripe
      - paramètre concerné
      - type d’erreur
      - documentation Stripe
    """
    stripe_event = WebhookEvent.objects.get(event_id=transfert_id)
    msg=None
    # Récupération du JSON d’erreur complet si disponible
    error_data = getattr(e, "json_body", {}).get("error", {})

    error_message = error_data.get("message", str(e))
    error_code = error_data.get("code", "unknown_code")
    error_param = error_data.get("param", None)
    error_type = error_data.get("type", "unknown_type")
    doc_url = error_data.get("doc_url", None)

    # Journal technique pour support
    msg = (
        f"[STRIPE ERROR] {error_type}\n"
        f"code={error_code}\n"
        f"message={error_message}\n"
        f"param={error_param}\n"
        f"doc={doc_url}\n"
    )
    logger.error(
        f"[STRIPE ERROR] {error_type} | code={error_code} | message={error_message} "
        f"| param={error_param} | doc={doc_url}"
    )

    # Mettre la facture en état "FAILED"
    if invoice_transfert:
        invoice_transfert.status = invoice_transfert.FAILED
        invoice_transfert.save(update_fields=["status"])

        logger.info(
            f"[INVOICE UPDATE] InvoiceTransfert {invoice_transfert.id} "
            f"marquée comme 'FAILED' suite erreur Stripe."
        )

    # Message utilisateur propre
    messages.error(
        request,  # sera remplacé par ton message en vue
        message=f"Stripe a refusé le transfert : {error_message}"
    )

    # Redirection contrôlée → page d’échec
    if not msg: msg="Problème non défini"
    append_webhook_log(stripe_event, "⛔ " + " | ".join(msg))
    context={
        "error_type": error_type,
        "msg": msg,
    }
    return render(request, 'payment/transfert_cancel.html', context)


@login_required
@user_passes_test(is_admin)
def transfert_success(request):
    """
    Page de succès après transfert, juste pournl'affichage
    """
    invoice_transfert_id = request.session.get('invoice_transfert_id', None)
    if not invoice_transfert_id:
        logger.warning("ID de la facture ne figure pas dans la session")
        return JsonResponse({'error': f"ID de la facture ne figure pas dans la session"}, status=404) # oui car ce n'est pas un Webhook
    
    invoice_transfert = InvoiceTransfert.objects.filter(id=invoice_transfert_id).first()
    if not invoice_transfert or not invoice_transfert.stripe_transfer_id:
        logger.warning("ID du transfert Stripe ne figure pas dans la facture")
        return JsonResponse({'error': f"ID du transfert Stripe ne figure pas dans la facture"}, status=404)
    
    # ce n'est pas un webhook mais pour suivre la trace
    stripe_event, _ = WebhookEvent.objects.get_or_create(event_id=invoice_transfert.stripe_transfer_id)

    # ✅ 1. Récupérer les IDs depuis la session avec sécurité
    cart_transfert = CartTransfert.objects.filter(user_admin=request.user).first()
    if not cart_transfert or not cart_transfert.items.exists():
        append_webhook_log(stripe_event, f"💥 les données du cart ne figurent pas ")
        return JsonResponse({'error': f"💥 les données du cart ne figurent pas "}, status=404)

    # ✅ 3. Récupérer les items associés
    cart_items = CartTransfertItem.objects.filter(cart_transfert=cart_transfert)

    # ✅ 4. Préparer le contexte pour le template
    context = {
        'invoice': invoice_transfert,
        'items': cart_items,
    }

    return render(request, 'payment/transfert_success.html', context)




######################################
# STRIPE WEBHOOK EVENT
######################################

"""
Désactive la protection CSRF (Cross-Site Request Forgery).
Obligatoire ici car Stripe envoie la requête — ce n'est pas un utilisateur connecté à ton site.
Sinon, Django rejetterait la requête avec une erreur 403.

Cette vue est exempte de protection CSRF car Stripe n’envoie pas de token CSRF.
C’est obligatoire pour les webhooks externes.
"""


@csrf_exempt
def stripe_webhook(request):
    """
    📡 Webhook Stripe UNIFIÉ - Gère TOUS les événements Stripe :
    
    - Paiements (checkout, payment_intent, charge)
    - Transferts vers comptes connectés  
    - Payouts vers banques
    - Remboursements
    - Disputes
    - Balance et fonds disponibles
    """
    user_admin = User.objects.filter(is_staff=True, is_active=True).first()
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    logger.info("📩 Webhook Stripe UNIFIÉ reçu")
    timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S") # 🕒 Ajoute un log horodaté
    # 1️⃣ Vérification de la signature Stripe
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        event_id = event.get('id')
        event_type = event.get('type')
        data_object = event['data']['object']
        logger.info(f"✅ Signature Stripe vérifiée pour l'événement : {event_id} ({event_type})")
    except ValueError:
        logger.error("❌ Erreur : Payload JSON invalide")
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        logger.critical("🚨 Signature Stripe invalide - Requête rejetée")
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    except Exception as e:
        logger.exception(f"💥 Erreur inattendue lors de la vérification de signature : {e}")
        return JsonResponse({'error': 'Webhook verification failed'}, status=400)

    # 2️⃣ Vérifier si l'événement existe déjà
    try:
        payload_json = json.loads(payload.decode('utf-8'))
        webhook_event = WebhookEvent.objects.filter(event_id=event_id).first()

        if webhook_event:
            # 🟡 Événement déjà connu
            if webhook_event.is_fully_completed:
                logger.warning(f"⚠️ Événement {event_id} déjà traité — Ignoré")
                return HttpResponse(status=200)
            else:
                # 🔁 Événement déjà reçu mais pas encore traité → Reprise
                logger.info(f"🔄 Reprise du traitement de l'événement {event_id} ({event_type})")
                # 🔧 Met à jour le payload au cas où Stripe a renvoyé une version corrigée
                webhook_event.payload = payload_json
                # ✅ Ajoute une ligne au log sans écraser l’ancien contenu
                
                previous_log = webhook_event.handle_log or ""
                webhook_event.handle_log = (
                    previous_log
                    + f"\n[{timestamp}] 🔄 Reprise du traitement de l'événement {event_id} ({event_type})"
                )
                webhook_event.save(update_fields=['payload', 'handle_log'])
        else:
            # 🆕 Nouvel événement
            webhook_event = WebhookEvent.objects.create(
                event_id=event_id,
                type=event_type,
                payload=payload_json,
                handle_log="🕒 En attente de traitement",
            )
            logger.info(f"📬 Nouvel événement Stripe enregistré : {event_id} ({event_type})")

    except Exception as e:
        logger.exception(f"💥 Impossible d'enregistrer ou de vérifier l'événement Stripe : {e}")
        return JsonResponse({'error': 'Database error'}, status=500)

    # 3️⃣ Dispatcher vers le bon handler - MAP UNIFIÉE
    try:
        logger.info(f"📊 Traitement de l'événement : {event_type}")
        append_webhook_log(webhook_event, f"🚀 Début du traitement pour {event_type}" )

        handlers_map = {
            # ==================== FLUX DE PAIEMENT ====================

            'payment_intent.created': handle_payment_intent_created, # mise à jour Invoce.stripe_payment_intent_id et création ou mise à jour d'un enregistrement dans Payment (achevé)
            'checkout.session.expired': handle_checkout_session_expired, # mise à jour Invoice.status=CANCELED et Demande_paiement.EN_ATTENTE (achevé)
            'checkout.session.completed': handle_checkout_session_completed, # à suivre
            'payment_intent.canceled': handle_payment_intent_canceled, # Cet événement signifie que le PaymentIntent a été annulé avant tout débit réel. Exemple : l’élève abandonne le paiement avant de valider, ou le paiement expire.
            'payment_intent.payment_failed': handle_payment_intent_failed, # Ce cas se produit lorsque le paiement a été tenté mais refusé par la banque (fonds insuffisants, carte expirée, etc.).
            'payment_intent.succeeded': handle_payment_intent_succeeded, # Mettre à jour le statut 
            # ==========================================================
            'charge.succeeded': handle_charge_succeeded, # Enregistrer les détails financiers charge Stripe quelque seconde après payment_intent.succeeded, elle contient obligatoirement balance_txn_id
            'radar.early_fraud_warning.created': handle_radar_fraud_warning, # ← Alerte après quelque seconde de  payment_intent.succeeded 
            # ou avant coup: payment_intent.succeeded en le bloquant, les evennement qui suivent peuvent être payment_intent.canceled 
            # ou payment_intent.payment_failed ou même payment_intent.succeeded
            # ==================== BALANCE & COMPTE ====================
            'balance.available': handle_balance_available, # 2-7 jours après fonds (paiements reçus) montant devient disponible (ou indisponible) pour être versé, Mettre à jour solde interne
            # à revoire timing (entre payment_intent.succeeded et balance.available)
            # ==================== TRANSFERTS & PAYOUTS ====================
            'transfer.created': handle_transfer_created, # le seul webhook suite à API stripe.Transfer.create() du compte de la plateforme aux comptes connectés (achever)
            'transfer.reversed': handle_transfer_reversed, # Stripe annule un transfert, et retourne les fonds vers ton compte plateforme (en partie ou totalement).

            'payout.created': handle_payout_created, # pour les virement du compte de la plateforme au compte bancaire de l'admin (non achever)
            'payout.paid': handle_payout_paid,
            'payout.failed': handle_payout_failed,
            'transfer.updated': handle_transfer_updated,
            'transfer.failed': handle_transfer_failed, # apparament il n'existe pas
            # ==========================================================

            'charge.dispute.created': handle_charge_dispute_created, # Pas encore traiter
            'charge.failed': handle_charge_failed, # Pas encore traiter
            
            'charge.dispute.closed': handle_charge_dispute_closed, # Pas encore traiter
             

            # ==================== REMBOURSEMENTS =========================
            'refund.created': handle_refund_created, #  traiter, 1er Webhook suite à stripe.Refund.create() mais pour refund total seulement
            'charge.refunded': handle_charge_refunded_unified, # Pas encore traiter, ⚠️ il est OBSOLÈTE
            'refund.updated': handle_refund_updated, # Pas encore traiter
            'charge.refund.updated': handle_charge_refund_updated_unified, # Pas encore traiter , 3° suivie du refundpas important
            'charge.updated': handle_charge_updated, # Pas encore traiter, 2° pour tous les type de refund
            'refund.failed': handle_refund_failed, # Pas encore traiter
            # ==================== PAYOUTS COMPTE CONNECT ====================
        }

        handler = handlers_map.get(event_type)

        if handler:
            webhook_event.handle_log += f"\n[{timestamp}] ⚙️ Appel du handler: {handler.__name__}"
            handler(user_admin, data_object, webhook_event)
            webhook_event.is_processed = True
            webhook_event.save(update_fields=['is_processed', 'handle_log'])
            append_webhook_log(webhook_event, f"✅ Traitement avec succès de l'èvènement: {event_type}  avec succès." )
            logger.info(f"✅ Événement {event_type} traité avec succès")
        else:
            append_webhook_log(webhook_event, f"ℹ️ Aucun handler pour {event_type}." )
            logger.info(f"ℹ️ Événement non géré : {event_type}")
            envoie_email_multiple(user_admin.id,[user_admin.id], f"ℹ️ Aucun handler pour {event_type}.", f"[{timestamp}] ℹ️ Événement non géré : {event_type}")

    except Exception as e:
        logger.exception(f"💥 Erreur lors du traitement de {event_type} : {e}")
        log_webhook_error(webhook_event, f"Erreur pendant le traitement : {str(e)}")
        return JsonResponse({'error': 'Webhook processing failed'}, status=500)

    # 4️⃣ Réponse finale à Stripe
    logger.info("✅ Webhook Stripe UNIFIÉ traité avec succès ✅")
    return HttpResponse(status=200)



def handle_radar_fraud_warning(user_admin, data_object, webhook_event):
    """
    🚨 Early Fraud Warning (EFW)
    -----------------------------------------
    Stripe envoie cet événement :
        - Quelques secondes après 'payment_intent.succeeded'
        - Ou AVANT que le PaymentIntent ne réussisse
    C'est uniquement une alerte préliminaire.
    Aucune action automatique ne doit être prise sur la facture.
    
    ➤ Le flux réel pourra ensuite être :
        - payment_intent.succeeded
        - payment_intent.payment_failed
        - payment_intent.canceled
        - ou un remboursement manuel

    → Le système doit juste enregistrer l'alerte et attendre la suite.
    """

    efw_id = data_object["id"]
    charge_id = data_object["charge"]
    payment_intent = data_object["payment_intent"]
    fraud_type = data_object.get("fraud_type", "unknown")

    # 🔹 Log initial
    message = (
        f"⚠️ Early Fraud Warning détecté\n"
        f"- efw_id        : {efw_id}\n"
        f"- charge_id     : {charge_id}\n"
        f"- payment_intent: {payment_intent}\n"
        f"- type fraude   : {fraud_type}\n"
    )

    append_webhook_log(
        webhook_event,
        "📩 Données reçues pour early_fraud_warning.created\n" + message
    )

    # -----------------------------------------------------------
    # 🔎 Recherche invoice via payment_intent ou charge
    # -----------------------------------------------------------
    invoice = None
    search_method = None
    
    # Priorité 1 : Recherche par payment_intent
    if payment_intent:
        invoice = Invoice.objects.filter(stripe_payment_intent_id=payment_intent).first()
        if invoice:
            search_method = "payment_intent"
            append_webhook_log(
                webhook_event,
                f"✅ Facture trouvée via payment_intent '{payment_intent}' (invoice_id={invoice.id})"
            )

    # Priorité 2 : Recherche par charge_id si invoice non trouvée
    if not invoice and charge_id:
        invoice = Invoice.objects.filter(stripe_charge_id=charge_id).first()
        if invoice:
            search_method = "charge_id"
            append_webhook_log(
                webhook_event,
                f"✅ Facture trouvée via charge_id '{charge_id}' (invoice_id={invoice.id})"
            )

    # -----------------------------------------------------------
    # 📌 Gestion selon que la facture est trouvée ou non
    # -----------------------------------------------------------
    if not invoice:
        error_message = (
            f"❌ Aucune facture trouvée pour cet EFW\n"
            f"   - payment_intent: {payment_intent}\n"
            f"   - charge_id: {charge_id}"
        )
        
        _webhook_status_update(
            webhook_event,
            is_fully_completed=False,
            message=error_message
        )
        
        # Notification par email
        email_subject = "🚨 Early Fraud Warning - Facture introuvable"
        email_body = (
            f"{error_message}\n\n"
            f"Détails de l'alerte :\n{message}"
        )
        envoie_email_multiple(
            user_admin.id, 
            [user_admin.id], 
            email_subject, 
            email_body
        )
        return

    # -----------------------------------------------------------
    # ✅ Facture trouvée - Enregistrement de l'alerte
    # -----------------------------------------------------------
    success_message = (
        f"📘 Alerte EFW liée à la facture invoice_id={invoice.id}\n"
        f"- Méthode de recherche : {search_method}\n"
        f"- Type de fraude : {fraud_type}\n"
        f"- Aucun changement automatique effectué.\n"
        f"- En attente des autres événements Stripe.\n"
    )

    append_webhook_log(webhook_event, success_message)

    # -----------------------------------------------------------
    # 🟩 FERMETURE propre de l'événement webhook
    # -----------------------------------------------------------
    _webhook_status_update(
        webhook_event,
        is_fully_completed=True,
        message=(
            "ℹ️ Early Fraud Warning traité. "
            "Aucune action prise. "
            "Suivi continu avec les prochains webhooks."
        )
    )

    # Notification de succès (optionnelle - pour traçabilité)
    email_subject = f"🚨 Early Fraud Warning - Facture #{invoice.id}"
    email_body = (
        f"Alerte de fraude détectée et enregistrée.\n\n"
        f"{success_message}\n"
        f"Action : Surveillance renforcée - Aucune action automatique."
    )
    envoie_email_multiple(
        user_admin.id, 
        [user_admin.id], 
        email_subject, 
        email_body
    )

    # -----------------------------------------------------------
    # 📌 Facture trouvée → simple information
    # -----------------------------------------------------------
    
    append_webhook_log(
        webhook_event,

            f"📘 Alerte EFW liée à la facture invoice_id={invoice.id}\n"
            f"→ Aucun changement automatique effectué.\n"
            f"→ En attente des autres événements Stripe.\n"
    )

    # -----------------------------------------------------------
    # 🟩 FERMETURE propre de l’événement webhook
    # -----------------------------------------------------------
    _webhook_status_update(
        webhook_event,
        is_fully_completed=True,
        message=
            "ℹ️ Early Fraud Warning traité. "
            "Aucune action prise. "
            "Suivi continu avec les prochains webhooks."
    )
    envoie_email_multiple(user_admin.id, [user_admin.id], "🚨 Early Fraud Warning (EFW)", 
            "Aucune action prise.\n"
            "Suivi continu avec les prochains webhooks.\n" + message                                                                                         
                    )

#=================== ancien handlers =======================

def handle_checkout_session_completed(user_admin, data_object, webhook_event):
    """
    💳 Gère l'événement Stripe 'checkout.session.completed'
    --------------------------------------------------------
    ➤ Objectif :
        - Vérifie que la session correspond bien à une facture (invoice).
        - Enregistre les logs du traitement dans la table WebhookEvent.
        - Marque l'événement comme traité si tout est terminé.
    """

    append_webhook_log(webhook_event, "💳 [checkout.session.completed] Début du traitement de la session checkout")

    # 1️⃣ Récupération de la facture associée via metadata
    invoice_id = data_object.get("metadata", {}).get("invoice_id")
    if not invoice_id:
        append_webhook_log(webhook_event, "⚠️ Aucun `invoice_id` trouvé dans les métadonnées de la session.")
        _webhook_status_update(webhook_event, is_fully_completed=False, 
                message="❌ Données manquantes: invoice_id non trouvé dans les métadonnées")
        return JsonResponse({'error': 'Invoice_id non trouvé'}, status=500)

    try:
        invoice = Invoice.objects.select_related("demande_paiement").get(id=invoice_id)
        if not invoice:
            _webhook_status_update(webhook_event, is_fully_completed=False, 
                            message="❌ Données manquantes: invoice_id non trouvé dans Invoice")
            return

        if invoice.status=='paid': # cas très rare
            append_webhook_log(webhook_event, "✅ La facture est déjà marqué PAID.")
            _webhook_status_update(webhook_event, is_fully_completed=True, 
            message="🏁 Traitement de 'checkout.session.completed' complété avec succès ⚠️ La facture est déjà marqué PAID.")
            return HttpResponse(status=200)
        
        demande_paiement = invoice.demande_paiement
        append_webhook_log(webhook_event, f"🧾 Facture trouvée (ID={invoice.id}), associée à la demande {demande_paiement.id}.")

        # 2️⃣ Vérification du statut du paiement renvoyé par Stripe
        payment_status = data_object.get("payment_status") 
        if not payment_status:
            append_webhook_log(webhook_event, "⚠️ Aucun statut de paiement trouvé dans la session Stripe.")
            _webhook_status_update(webhook_event, is_fully_completed=True, 
            message="🏁 Traitement de 'checkout.session.completed' complété avec succès ⚠️ Aucun statut de paiement trouvé dans la session Stripe. pas de modification dans BDD")
            return HttpResponse(status=200)

        # 3️⃣ Traitement selon le statut de paiement
        if payment_status == "paid":
            append_webhook_log(webhook_event, "✅ Le paiement est réralisé.")
            _webhook_status_update(webhook_event, is_fully_completed=True, 
            message="🏁 Traitement de 'checkout.session.completed' complété avec succès ⚠️ Aucun statut de paiement trouvé dans la session Stripe. pas de modification dans BDD")
            return HttpResponse(status=200)
            
        elif payment_status == "unpaid": # ⚠️ Paiement échoué ou refusé, on ne fait rien en attend la suite des évènement pour s'assurer

            append_webhook_log(webhook_event, f"⚠️ Paiement non réussi : Demande de paiement {demande_paiement.id} en attente.")
            _webhook_status_update(webhook_event, is_fully_completed=True, 
            message="🏁 Traitement de 'checkout.session.completed' complété avec succès le ⚠️ Paiement non réussince, le status de la demande, Payment, Invoice ne change pas dans l'attente de la suite des évènement")
        else:
            # 📊 Cas inattendu
            append_webhook_log(webhook_event, f"📊 Statut de paiement inattendu : {payment_status} pour demande {demande_paiement.id}.")
            _webhook_status_update(webhook_event, is_fully_completed=True, 
            message=f"🏁 Traitement de 'checkout.session.completed' complété avec succès . 📊 Statut de paiement inattendu : {payment_status} pour demande {demande_paiement.id}.")
        
    except Exception as e:
        _webhook_status_update(webhook_event, is_fully_completed=False, 
                message=f"❌ Erreur inattendue lors du traitement : {str(e)}")


 
def handle_checkout_session_expired( user_admin, data_object, webhook_event):
    """
    🕒 Gestion de l'expiration d'une session de paiement Stripe
    
    Cette fonction est déclenchée lorsqu'un utilisateur ne complète pas son paiement
    dans le délai imparti (24h par défaut). Elle assure :
    - La mise à jour du statut de la facture
    - La mise à jour du statut de l'événement webhook

    Args:
        session (dict): Objet session Stripe contenant les métadonnées
    """
    
    session_id = data_object['id']
    
    append_webhook_log(webhook_event, f"⏰ [Session {session_id}] Début du traitement d'expiration")
    
    # 🔍 EXTRACTION DES MÉTADONNÉES
    invoice_id = data_object.get("metadata", {}).get("invoice_id")
    
    # 🛡️ VALIDATION DES DONNÉES D'ENTRÉE
    if not invoice_id:
        append_webhook_log(webhook_event, f"⚠️ [Session {session_id}] Aucun invoice_id dans les métadonnées")
        # 4️⃣ Marquer l'événement Webhook comme traité mais incomplet (données manquantes)
        _webhook_status_update(webhook_event, is_fully_completed=False, 
                              message="❌ Données manquantes: invoice_id non trouvé dans les métadonnées")
        return

    try:
        # 📦 RÉCUPÉRATION DE LA FACTURE AVEC VERROUILLAGE
        # Utilisation de select_for_update() pour éviter les races conditions
        # dans un environnement multi-threadé
        with transaction.atomic():
            # ❌ VOTRE CAS non nécessaire select_for_update:
            # - Faible concurrence
            # - Opération simple (changement de statut)
            # - Pas de calculs complexes dépendants de l'état
            # 📦 Récupération sécurisée de la facture
            invoice = Invoice.objects.select_for_update().filter(id=invoice_id).first()
            if not invoice:
                _webhook_status_update(webhook_event, is_fully_completed=False, 
                              message="❌ Données manquantes: invoice_id non trouvé dans Invoice")
                return
            # 🔒 VÉRIFICATIONS DE SÉCURITÉ
            # Une facture déjà payée ne doit pas être modifiée
            if invoice.status == Invoice.PAID:
                append_webhook_log(webhook_event,
                    f"🚨 [Session {session_id}] Tentative d'expiration sur facture déjà payée "
                    f"(Facture {invoice.id}, Statut: {invoice.status})"
                )
                # 4️⃣ Marquer l'événement Webhook comme traité mais non applicable
                _webhook_status_update(webhook_event, is_fully_completed=True, 
                                      message="⚠️ Session expirée pour facture déjà payée - Aucune action nécessaire")
                return
            
            # 💾 MISE À JOUR DU STATUT DE LA FACTURE
            invoice.status = Invoice.CANCELED
            invoice.save()

            if not invoice.demande_paiement:
                _webhook_status_update(webhook_event,
                    is_fully_completed=False,  # ✅ Le traitement est terminé même sans demande associée
                    message=f"ℹ️ [Session {session_id}] Aucune demande de paiement associée à la facture {invoice.id}"
                    "ℹ️ Facture annulée, mais aucune demande de paiement associée"
                )
                return

            demande_paiement = invoice.demande_paiement
            ancien_statut = demande_paiement.statut_demande
            demande_paiement.statut_demande = Demande_paiement.EN_ATTENTE
            demande_paiement.save()
            #  Marquer l'événement Webhook comme traité et complété
            append_webhook_log(webhook_event,
                f"📝 [Session {session_id}] Demande de paiement {demande_paiement.id} "
                f"mise à jour: {ancien_statut} → {Demande_paiement.EN_ATTENTE}"
            )

            #  Marquer l'événement Webhook comme traité et complété
            _webhook_status_update(webhook_event, is_fully_completed=True, 
                message="🏁 Traitement d'expiration de session complété avec succès")

    except Invoice.DoesNotExist:
        error_msg = f"❌ [Session {session_id}] Facture {invoice_id} introuvable en base de données"
        #  Marquer l'événement Webhook comme traité mais non complété (erreur métier)
        _webhook_status_update(webhook_event, is_fully_completed=False, 
                              message=f"❌ {error_msg}")
        
    except Exception as e:
        #  Marquer l'événement Webhook comme traité mais non complété (erreur technique)
        _webhook_status_update(webhook_event, is_fully_completed=False, 
                              message=f"❌ Erreur technique: {str(e)} ")



def _update_demande_paiement(invoice, session_id):
    """
    🔄 Met à jour le statut de la demande de paiement
    
    Lorsqu'une session expire, la demande de paiement retourne en statut "en attente"
    pour permettre à l'utilisateur de réessayer ultérieurement.
    """
    if not invoice.demande_paiement:
        logger.debug(f"ℹ️ [Session {session_id}] Aucune demande de paiement associée")
        return
        
    demande_paiement = invoice.demande_paiement
    ancien_statut = demande_paiement.statut_demande
    demande_paiement.statut_demande = Demande_paiement.EN_ATTENTE
    demande_paiement.save()
    
    logger.info(
        f"📝 [Session {session_id}] Demande de paiement {demande_paiement.id} "
        f"mise à jour: {ancien_statut} → {Demande_paiement.EN_ATTENTE}"
    )


def _cleanup_cart(invoice, session_id):
    """
    🗑️ Nettoie le panier et ses items associés
    
    Le panier est supprimé car :
    - Les items peuvent avoir changé de prix
    - L'utilisateur peut vouloir modifier sa sélection
    - Évite l'accumulation de paniers abandonnés
    """
    if not invoice.cart:
        logger.debug(f"ℹ️ [Session {session_id}] Aucun panier associé")
        return
    
    cart = invoice.cart
    cart_items_count = cart.items.count()
    
    # 📊 Log des détails avant suppression
    logger.debug(
        f"🛒 [Session {session_id}] Nettoyage du panier {cart.id} "
        f"contenant {cart_items_count} item(s)"
    )
    
    # 🗑️ SUPPRESSION EN CASCADE
    # Les CartItems sont supprimés automatiquement par CASCADE
    # grâce à la ForeignKey avec on_delete=models.CASCADE
    cart_id = cart.id
    cart.delete()
    
    logger.info(
        f"🗑️ [Session {session_id}] Panier {cart_id} et ses {cart_items_count} "
        f"item(s) supprimés avec succès"
    )


def _cleanup_cart_payment(invoice, payment_intent_id, payment_intent, event_id):
    """
    🗑️ Nettoie le panier et ses items associés
    
    Le panier est supprimé car :
    - Les items peuvent avoir changé de prix
    - L'utilisateur peut vouloir modifier sa sélection
    - Évite l'accumulation de paniers abandonnés
    """
    if not invoice.cart:
        add_webhook_log(event_id, f"ℹ️ [Payment {payment_intent_id}] Aucun panier associé")
        return
    
    cart = invoice.cart
    cart_items_count = cart.items.count()
    
    # 📊 Log des détails avant suppression
    add_webhook_log(event_id,
        f"🛒 [Payment {payment_intent_id}] Nettoyage du panier {cart.id} "
        f"contenant {cart_items_count} item(s)"
    )
    
    # 🗑️ SUPPRESSION EN CASCADE
    # Les CartItems sont supprimés automatiquement par CASCADE
    # grâce à la ForeignKey avec on_delete=models.CASCADE
    cart_id = cart.id
    cart.delete()
    
    add_webhook_log(event_id,
        f"🗑️ [Payment {payment_intent_id}] Panier {cart_id} et ses {cart_items_count} "
        f"item(s) supprimés avec succès"
    )


def handle_payment_intent_failed(user_admin, data_object, webhook_event):
    """
    ❌ Gestion de l'échec d'un PaymentIntent Stripe (payment_intent.payment_failed)

    Cet événement est déclenché lorsque Stripe indique que le paiement a échoué :
    - Carte refusée
    - Fonds insuffisants
    - Échec 3D Secure
    - Problème technique Stripe
    - Toute erreur de processing

    Contrairement à `payment_intent.canceled`, ce n’est PAS une annulation manuelle
    mais un ÉCHEC définitif du paiement. On doit :
        - Marquer la facture Invoice comme "FAILED"
        - Marquer la demande de paiement comme "EN_ATTENTE"
        - Enregistrer l’erreur Stripe dans cancellation_reason
    """

    payment_intent_id = data_object['id']
    append_webhook_log(webhook_event, 
        f"❌ [PaymentIntent {payment_intent_id}] Début du traitement d'échec du paiement")

    # 🔍 EXTRACTION METADATA
    invoice_id = data_object.get("metadata", {}).get("invoice_id")

    # 🛡️ VALIDATION DES MÉTADONNÉES
    if not invoice_id:
        append_webhook_log(webhook_event, 
            f"⚠️ [PaymentIntent {payment_intent_id}] Aucun invoice_id trouvé dans metadata")
        
        _webhook_status_update(
            webhook_event, 
            is_fully_completed=False,
            message="❌ Données manquantes : invoice_id absent"
        )

        return JsonResponse({'error': 'Invalid invoice_id'}, status=500)

    try:
        # 🔎 RÉCUPÉRATION DE LA FACTURE
        invoice = Invoice.objects.filter(id=invoice_id).first()
        if not invoice:
            append_webhook_log(webhook_event, 
                f"❌ [PaymentIntent {payment_intent_id}] Facture {invoice_id} introuvable en BDD")
            
            _webhook_status_update(
                webhook_event,
                is_fully_completed=False,
                message="❌ Facture introuvable en BDD"
            )
            return

        # 🚨 CAS CRITIQUE
        if invoice.status == Invoice.PAID:
            append_webhook_log(webhook_event,
                f"💥 [PaymentIntent {payment_intent_id}] Facture {invoice_id} est PAID alors que Stripe signale un échec !")
            
            envoie_email_multiple(
                user_admin.id,
                [user_admin.id],
                sujet_email="⚠️ ERREUR FATALE - Invoice incohérente (FAILED vs PAID)",
                texte_email=(
                    f"Erreur critique : La facture {invoice_id} est PAID alors que Stripe informe "
                    f"d'un échec de paiement.\n"
                    f"stripe_failure_message = {data_object.get('last_payment_error', {}).get('message')}\n"
                    f"stripe_failure_code = {data_object.get('last_payment_error', {}).get('decline_code')}\n"
                    f"payment_intent_id = {payment_intent_id}\n"
                    f"webhook_event_id = {webhook_event.event_id}\n"
                    f"amount = {data_object['amount']} centimes\n"
                    f"invoice_total = {invoice.total} centimes\n"
                )
            )

            logger.error(
                f"💥 Incohérence critique invoice={invoice_id} : Stripe=FAILED, BDD=PAID ; "
                f"payment_intent={payment_intent_id}"
            )

            _webhook_status_update(
                webhook_event, 
                False,
                "💥 Facture incohérente : intervention manuelle requise"
            )
            return

        # 🟡 MARQUER LA FACTURE COMME FAILED
        Invoice.objects.filter(id=invoice_id).update(
            status=Invoice.CANCELED,
            cancellation_reason=data_object.get('last_payment_error', {}).get('message', 'payment_intent_failed')
        )

        append_webhook_log(webhook_event,
            f"❌ Facture {invoice_id} marquée CANCELED (paiement échoué)\n"
            f"Erreur Stripe : {data_object.get('last_payment_error', {}).get('message')}"
        )

        # 📌 GÉRER LA DEMANDE DE PAIEMENT ASSOCIÉE
        if not invoice.demande_paiement:
            _webhook_status_update(
                webhook_event,
                False,
                f"ℹ️ Aucune demande de paiement associée à l'invoice {invoice_id}"
            )
            return

        demande_paiement = Demande_paiement.objects.filter(id=invoice.demande_paiement.id).first()
        if not demande_paiement:
            _webhook_status_update(
                webhook_event,
                False,
                f"ℹ️ Demande_paiement introuvable pour invoice {invoice_id}"
            )
            return

        ancien_statut = demande_paiement.statut_demande
        demande_paiement.statut_demande = Demande_paiement.EN_ATTENTE
        demande_paiement.save()

        append_webhook_log(webhook_event,
            f"📝 Demande_paiement {demande_paiement.id} mise EN_ATTENTE "
            f"({ancien_statut} → {Demande_paiement.EN_ATTENTE})"
        )

        # 🎯 FIN OK
        append_webhook_log(webhook_event,
            f"🎯 Traitement complet de payment_intent.payment_failed terminé avec succès"
        )

        _webhook_status_update(
            webhook_event, 
            True,
            "🏁 Traitement de payment_intent.payment_failed complété avec succès"
        )

    except Exception as e:
        error_msg = f"💥 Erreur critique dans traitement de payment_intent.payment_failed : {e}"
        append_webhook_log(webhook_event, error_msg)

        _webhook_status_update(
            webhook_event,
            False,
            f"❌ {error_msg}"
        )

        return JsonResponse({'error': 'technical_error'}, status=500)



def _log_payment_failure_details(invoice, payment_intent_id, payment_intent, event_id):
    """
    📊 Log des détails spécifiques à l'échec du paiement
    """
    last_payment_error = payment_intent.get('last_payment_error', {})
    error_code = last_payment_error.get('code', 'unknown_error')
    error_message = last_payment_error.get('message', 'Erreur inconnue')
    decline_code = last_payment_error.get('decline_code')
    
    add_webhook_log(event_id, 
        f"📊 [PaymentIntent {payment_intent_id}] Détails d'échec - "
        f"Code: {error_code}, Decline: {decline_code}, "
        f"Message: {error_message}, Facture: {invoice.id}"
    )
    

def _cleanup_failed_payment_resources(invoice, payment_intent_id, payment_intent, event_id):
    """
    🧹 Nettoie les ressources associées à un payment intent échoué
    """
    cleanup_actions = [
        # (_update_demande_paiement_failed, "demande de paiement"),
        # (_cleanup_cart_payment, "panier et items"),  # Identique à canceled
    ]
    
    for action, resource_name in cleanup_actions:
        try:
            action(invoice, payment_intent_id, payment_intent)
            add_webhook_log(event_id, f"🧹 [PaymentIntent {payment_intent_id}] Nettoyage {resource_name} terminé")
        except Exception as e:
            add_webhook_log(event_id, f"⚠️ [PaymentIntent {payment_intent_id}] Échec du nettoyage {resource_name}: {str(e)}")

def _update_demande_paiement_failed(invoice, payment_intent_id, payment_intent, event_id):
    """
    🔄 Met à jour le statut de la demande de paiement après échec
    """
    if not invoice.demande_paiement:
        add_webhook_log(event_id, f"ℹ️ [PaymentIntent {payment_intent_id}] Aucune demande de paiement associée")
        return
        
    demande_paiement = invoice.demande_paiement
    ancien_statut = demande_paiement.statut_demande
    
    # 🔥 DIFFÉRENCE : Statut spécifique pour échec vs annulation
    demande_paiement.statut_demande = Demande_paiement.EN_ATTENTE  # Ou un statut "Échec" si vous en créez un
    demande_paiement.save()
    
    add_webhook_log(event_id, 
        f"📝 [PaymentIntent {payment_intent_id}] Demande de paiement {demande_paiement.id} "
        f"mise à jour après échec: {ancien_statut} → {demande_paiement.statut_demande}"
    )


def handle_payment_intent_canceled( user_admin, data_object, webhook_event ):
    """
    🚫 Gestion de l'annulation d'un PaymentIntent Stripe
    
    Cette fonction est déclenchée lorsqu'un PaymentIntent est annulé par Stripe
    (échec 3D Secure, expiration, annulation manuelle, etc.). 
    Remarque importante: c'est le statut final du PaymentIntent, 
    il n'y aura pas d'autre évènement liés au PaymentIntent.
    Il faut bien traiter cet évènement selon la raison de l'annulation.
    Elle assure :
    - La mise à jour du statut de la facture Invoice et Demande_paiement
    - La mise à jour du statut de l'événement webhook
    """
    
    payment_intent_id = data_object['id']
    append_webhook_log(webhook_event, f"🚫 [PaymentIntent {payment_intent_id}] Début du traitement d'annulation")
    
    # 🔍 EXTRACTION DES MÉTADONNÉES
    invoice_id = data_object.get("metadata", {}).get("invoice_id")
    
    # 🛡️ VALIDATION DES DONNÉES D'ENTRÉE
    if not invoice_id:
        append_webhook_log(webhook_event, f"⚠️ [PaymentIntent {payment_intent_id}] Aucun invoice_id dans les métadonnées")
        # 4️⃣ Marquer l'événement Webhook comme traité mais incomplet (données manquantes)
        _webhook_status_update(webhook_event, is_fully_completed=False, 
                              message="❌ Données manquantes: invoice_id non trouvé dans les métadonnées")
        return JsonResponse({'error': 'Invalid invoice_id'}, status=500) # on oblige Stripe à envoyer de nouveau le contenu de l'évènement

    try:
        # 🔄 TENTATIVE DE MISE À JOUR ATOMIQUE (SANS select_for_update)
        # Utilise update() qui est atomique par nature - plus simple et efficace
        # il faut traiter le cas invoice.status=Ivoice.PAID ( car c'est une contradiction d'enregistrement)
        invoice = Invoice.objects.filter(id=invoice_id).first()
        if not invoice:
                _webhook_status_update(webhook_event, is_fully_completed=False, 
                              message="❌ Données manquantes: invoice_id non trouvé dans Invoice de la BDD"
                              f"❌ [PaymentIntent {payment_intent_id}] Facture {invoice_id} introuvable")
                return

        if invoice.status==Invoice.PAID:
            append_webhook_log(webhook_event, f"⚠️ ❌ 🚫 💥 Attention Erreur fatale: La facture {invoice_id} est notée PAID dans la BDD alors que Webhook nous informe qu'elle est annulée")
            envoie_email_multiple(
                            user_admin.id,
                            [user_admin.id], 
                            sujet_email="Attention Erreur fatale",
                            texte_email = (
                                f"⚠️ ❌ 🚫 💥 Attention Erreur fatale : La facture {invoice_id} est notée PAID dans la BDD "
                                f"alors que le Webhook nous informe qu'elle est annulée.\n"
                                f"L'administrateur est appelé à corriger les données de la base manuellement.\n"
                                f"cancellation_reason = {data_object.get('cancellation_reason', 'payment_intent_canceled')}\n"
                                f"invoice_id = {invoice_id}\n"
                                f"webhook_event_id = {webhook_event.event_id}\n"
                                f"webhook_event_type = {webhook_event.type}\n"
                                f"webhook_payment_intent_id = {payment_intent_id}\n"
                                f"Webhook_amount = {data_object['amount']} centimes\n"
                                f"BDD_invoice_montant = {invoice.total} centimes"
                            ))

            logger.warning(f"⚠️ ❌ 🚫 💥 Attention Erreur fatale: La facture {invoice_id} est notée PAID dans la BDD alors que Webhook nous informe qu'elle est annulée; L'administrateur est appelé à corriger les données de la base de donées manuellement. cancellation_reason={data_object.get('cancellation_reason', 'payment_intent_canceled')} invoice_id={invoice_id}; webhook_event_id={webhook_event.event_id}; webhook_event_type={webhook_event.type}; webhook_payment_intent_id={payment_intent_id}; Webhook_amount={data_object['amount']} Centimes, BDD_invoice_id={invoice_id}; BDD_invoice_montant= {invoice.total} Centimes")
            _webhook_status_update(webhook_event, False, "⚠️ ❌ 🚫 💥 L'administrateur est appelé à corriger les données de la base de donées manuellement")
            return
        
        
        # ✅ SUCCÈS - Récupération de la facture pour le nettoyage
        Invoice.objects.filter(id=invoice_id).update(
            status=Invoice.CANCELED,
            cancellation_reason=data_object.get('cancellation_reason', 'payment_intent_canceled')
        ) # Plus atomique. Plus rapide. Plus sûr.

        append_webhook_log(webhook_event, 
        f"✅ [PaymentIntent {payment_intent_id}] Facture {invoice.id} marquée comme annulée\n"
        f"raison d'annulation: {data_object.get('cancellation_reason', 'payment_intent_canceled')}")

        if not invoice.demande_paiement: # car pour invoice.demande_paiement a la propriété null=True
            _webhook_status_update(webhook_event, is_fully_completed=False, 
                message="🏁 Traitement d'annulation de payment intent complété avec succès,  ℹ️ mais [PaymentIntent {payment_intent_id}] Aucune demande de paiement associée")
            return
        demande_paiement= Demande_paiement.objects.filter(id=invoice.demande_paiement.id).first()
        if not demande_paiement:
            _webhook_status_update(webhook_event, is_fully_completed=False, 
                message="🏁 Traitement d'annulation de payment intent complété avec succès,  ℹ️ mais [PaymentIntent {payment_intent_id}] Aucune demande de paiement associée")
            return
        ancien_statut = demande_paiement.statut_demande
        demande_paiement.statut_demande = Demande_paiement.EN_ATTENTE
        demande_paiement.save()
        
        append_webhook_log(webhook_event,
            f"📝 [PaymentIntent {payment_intent_id}] Demande de paiement {demande_paiement.id} "
            f"mise à jour: {ancien_statut} → {Demande_paiement.EN_ATTENTE}"
            )
        
        # 🎯 SUCCÈS COMPLET DU TRAITEMENT
        append_webhook_log(webhook_event,  f"🎯 [PaymentIntent {payment_intent_id}] Traitement d'annulation terminé avec succès")
        
        # 4️⃣ Marquer l'événement Webhook comme traité et complété
        _webhook_status_update(webhook_event, is_fully_completed=True, 
                              message="🏁 Traitement d'annulation de payment intent complété avec succès")

    except Exception as e:
        error_msg = f"💥 [PaymentIntent {payment_intent_id}] Erreur critique lors du traitement : {e}"
        append_webhook_log(webhook_event, error_msg)
        # 4️⃣ Marquer l'événement Webhook comme traité mais non complété (erreur technique)
        _webhook_status_update(webhook_event, is_fully_completed=False, 
                              message=f"❌ {error_msg}")
        return JsonResponse({'error': 'Invalid invoice_id'}, status=500) # car peut être l'erreur est accidentelle donc il vaut mieu que l'évènement webhook soit répété vu son importance



def handle_charge_failed(charge):
    """Traitement quand une charge échoue - VERSION ADAPTÉE"""
    logger.error(f"💥 Charge échouée : {charge['id']} - Raison : {charge.get('failure_message', 'Inconnue')}")

def handle_charge_dispute_created(dispute):
    """Traitement quand une réclamation (dispute) est créée - VERSION ADAPTÉE"""
    logger.warning(f"⚖️ Réclamation créée : {dispute['id']} - Raison : {dispute.get('reason', 'Inconnue')}")
    
    # Mettre à jour la facture
    invoice = Invoice.objects.filter(stripe_payment_intent_id=dispute.get('payment_intent')).first()
    if invoice:
        invoice.status = "disputed"
        invoice.dispute_created_at = timezone.now()
        invoice.save()
        logger.info(f"⚖️ Facture ID={invoice.id} marquée comme contestée.")

def handle_charge_dispute_closed(dispute):
    """Traitement quand une réclamation est fermée - VERSION ADAPTÉE"""
    logger.info(f"🔒 Réclamation fermée : {dispute['id']} - Statut : {dispute['status']}")

def send_payment_success_notification(invoice):
    """Envoyer une notification de succès de paiement"""
    try:
        # 🔔 Ici vous pouvez :
        # - Envoyer un email de confirmation
        # - Notifier un webhook interne
        # - Mettre à jour d'autres systèmes
        # - Créer une notification dans votre app
        
        logger.info(f"📧 Notification de paiement à envoyer pour la facture ID={invoice.id}")
        
        # Exemple d'envoi d'email :
        # send_mail(
        #     'Paiement confirmé',
        #     f'Votre paiement pour la facture {invoice.id} a été confirmé.',
        #     'noreply@votre-site.com',
        #     [invoice.customer_email],
        #     fail_silently=False,
        # )
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'envoi de la notification : {e}")

# ==================== HANDLERS UNIFIÉS ====================


def handle_payment_intent_succeeded(user_admin, data_object, webhook_event, charge=None, bal=None):
    """
    💰 Traitement quand un payment intent réussit
    mais avant qu'il soit disponible dans le compte Stripe

    🔹 Gère l'événement Stripe 'payment_intent.succeeded'.
    Chaque PaymentIntent peut contenir une ou plusieurs 'charges'.
    Chaque 'charge' est lié à une tentative de paiement
    seule la dernière charge est importante
    pour cloturer les evennement webhook d'une même opération.
    la recupération de charge et de la balance est facultative selon la disposition des données du Webhook
    charge et bal deux paramètres pour assurer le teste du webhook en local seulement
    """
    payment_intent_id=None
    invoice_id=None

    payment_intent_id = data_object['id']
    if payment_intent_id is None:
        append_webhook_log(webhook_event, 
            "⚠️ [PaymentIntent ID ne figure pas dans data_object de Stripe ")
        
        _webhook_status_update(webhook_event, 
            is_fully_completed=False,
            message="❌ Données manquantes : PaymentIntent ID"
        )

        return JsonResponse({'error': 'PaymentIntent ID inexistant'}, status=500)
    
    append_webhook_log(webhook_event, 
        f"✅ [PaymentIntent {payment_intent_id}] Début du traitement payment_intent.succeeded")

    # 🔍 EXTRACTION METADATA
    invoice_id = data_object.get("metadata", {}).get("invoice_id")

    # 🛡️ VALIDATION DES MÉTADONNÉES
    if invoice_id is None:
        append_webhook_log(webhook_event, 
            f"⚠️ [PaymentIntent {payment_intent_id}] Aucun invoice_id trouvé dans metadata")
        
        _webhook_status_update(webhook_event, 
            is_fully_completed=False,
            message="❌ Données manquantes : invoice_id absent"
        )
        return JsonResponse({'error': 'Invalid invoice_id'}, status=500)
    
    try:
        # 🔎 RÉCUPÉRATION DE LA FACTURE
        invoice = Invoice.objects.filter(id=invoice_id).first()
        if not invoice:
            append_webhook_log(webhook_event, 
                f"❌ [PaymentIntent {payment_intent_id}] Facture {invoice_id} introuvable en BDD")
            
            _webhook_status_update(
                webhook_event,
                is_fully_completed=False,
                message="❌ Facture introuvable en BDD"
            )
            return

        # 🚨 Cas fréquent
        # il se peut que lévènement payment_intent.succeeded a été traité 
        # en retard et que lévènement balance.available ou charge.succeed  est traité avant
        if invoice.status == Invoice.PAID:
            _webhook_status_update(
                webhook_event, 
                True,
                f"🏁 [PaymentIntent {payment_intent_id}] Facture {invoice_id} est déjà marqué PAID."
                f"\n🏁 On suppose que la suite des traitement du cas Invoice.PAID est effectué."
            )
            return HttpResponse(status=200)
        
        # 🟡 MARQUER LA FACTURE COMME DRAFT seule l'évènent balance.available peut changer en PAID en mode Live
        # Valablepour les deux cas Test et Live
        invoice.status=Invoice.DRAFT
        invoice.paid_at=timezone.now()
        invoice.stripe_payment_intent_id=payment_intent_id
        invoice.save()

        append_webhook_log(webhook_event,
            f"✅ Facture {invoice_id} marquée DRAFT (payment_intent.succeeded)"
        )

        
        coherent = verifier_coherence_montants(
                    texte1="payment_intent.succeeded",
                    texte2="Invoice BDD",
                    montant1=data_object.get("amount"),
                    montant2=invoice.total,
                    abs_tol=5,
                    user_admin=user_admin
                )
        # tester la coérance du montant non bloquant
        if not coherent:
            logger.error(
                f"💥 Incohérence critique invoice.toal={invoice.total} centimes dans BDD "
                f"amount={data_object.get('amount')} centime deévènement payment_intent.succeeded"
                )

        # 📌 GÉRER LA DEMANDE DE PAIEMENT ASSOCIÉE
        if not invoice.demande_paiement:
            _webhook_status_update(
                webhook_event,
                False,
                f"ℹ️ Aucune demande de paiement associée à l'invoice {invoice_id} Erreur BDD"
            )
            return

        demande_paiement = Demande_paiement.objects.filter(id=invoice.demande_paiement.id).first()
        if not demande_paiement:
            _webhook_status_update(
                webhook_event,
                False,
                f"ℹ️ Demande_paiement introuvable pour invoice {invoice_id}"
            )
            return

        # Mise à jour Demande de paiement valable pour les deux cas Test et Live
        ancien_statut = demande_paiement.statut_demande
        demande_paiement.statut_demande = Demande_paiement.EN_ATTENTE
        demande_paiement.save()

        append_webhook_log(webhook_event,
            f"📝 Demande_paiement {demande_paiement.id} mise EN_ATTENTE "
            f"({ancien_statut} → {Demande_paiement.EN_ATTENTE})"
        )

        # 🎯 FIN OK
        _webhook_status_update(
            webhook_event, 
            True,
            "🎯 Traitement de payment_intent.succeeded complété avec succès"
        ) # car le traitement principale est payment_intent.succeeded, le reste de traitement est facultatif selon la disposition des données

        # ============================================================
        #   🔵 ETAPE : RÉCUPÉRATION CHARGE + BALANCE TRANSACTION
        #   (facultatif selon les données du webhook)
        # ============================================================
        
        # seule la dernière charge est prise en compte (data_object peut être local de teste ou envoyée par Stripe)
        latest_charge_id = data_object.get("latest_charge")

        if latest_charge_id:
            append_webhook_log(
                webhook_event,
                f"🔍 Charge détectée dans PaymentIntent : {latest_charge_id}"
            )

            # ----------------------------
            # 1️⃣ Récupération de CHARGE de Stripe
            # ----------------------------
            try:
                retrieved_charge = stripe.Charge.retrieve(latest_charge_id)
                if retrieved_charge:
                    charge = retrieved_charge  # overwrite uniquement si valide pour ne pas prendre en comte chare du testelocal
                    append_webhook_log(
                        webhook_event,
                        f"💳 Charge récupérée avec succès : {latest_charge_id}"
                    )
                else:
                    append_webhook_log(
                        webhook_event,
                        f"⚠️ Charge Stripe vide. Utilisation de la charge par défaut du test local si charge est pas null."
                    )
            except Exception as e:
                append_webhook_log(
                    webhook_event,
                    f"⚠️ Impossible de récupérer Charge Stripe ({latest_charge_id}) : {e}. "
                    f"Utilisation de la charge par défaut."
                )
                return HttpResponse(status=200)

            append_webhook_log(
                    webhook_event,
                    f"charge = {charge} qui peut être local ou de Stripe"
                )
            
            # Mise à jour Invoice
            if invoice.stripe_charge_id is None or invoice.stripe_charge_id=='': # cas où charge.succeed n'est pas encore détectée
                invoice.stripe_charge_id=latest_charge_id
                invoice.save()
            elif invoice.stripe_charge_id!=latest_charge_id: # car payment.intent.succeed contient la dernière charge
                invoice.stripe_charge_id=latest_charge_id # tj prendre la dernère charge
                invoice.save()
            
            append_webhook_log(
                    webhook_event,
                    f"✅ Mise à jour de latest_charge: invoice.stripe_charge_id = {invoice.stripe_charge_id}"
                )

            # ----------------------------
            # 2️⃣ Extraction balance_transaction_id
            # ----------------------------
            balance_txn_id = None # cas localou Stripe
            retrieved_charge = stripe.Charge.retrieve(latest_charge_id)

            if retrieved_charge: # Cas Stripe seulement
                charge = retrieved_charge  # overwrite uniquement si valide
                if charge:
                    balance_txn_id = charge.get("balance_transaction")
                    if balance_txn_id is not None:
                        invoice.balance_txn_id=balance_txn_id
                        invoice.save()
                        append_webhook_log(
                            webhook_event,
                            f"✅ Mise à jour de invoice.balance_txn_id={balance_txn_id}"
                        )
                    else:
                        append_webhook_log(
                            webhook_event,
                            "⚠️ Aucun balance_transaction trouvé dans la charge"
                        )
                        return HttpResponse(status=200)  # pas de balance → stop la partie optionnelle

                append_webhook_log(
                    webhook_event,
                    f"📌 balance_transaction détecté : {balance_txn_id}"
                )

            # ----------------------------
            # 3️⃣ Récupération BALANCE TRANSACTION
            # ----------------------------
            try:
                retrieved_bal = stripe.BalanceTransaction.retrieve(balance_txn_id)
                if retrieved_bal:
                    bal = retrieved_bal # overwrite uniquement si valide (Cas Stripe non local)
                    append_webhook_log(
                        webhook_event,
                        f"📘 BalanceTransaction récupérée : {balance_txn_id}"
                    )
                else:
                    append_webhook_log(
                        webhook_event,
                        f"⚠️ BalanceTransaction vide — utilisation de la valeur par défaut."
                    )
            except Exception as e:
                append_webhook_log(
                    webhook_event,
                    f"⚠️ Impossible de récupérer BalanceTransaction Stripe : {e}. "
                    f"Utilisation de la valeur par défaut."
                )
                return HttpResponse(status=200)

            # ----------------------------
            # 4️⃣ Mise à jour / création du BalanceTransaction en BDD (Cas local ou Stripe)
            # ----------------------------
            if charge and bal:
                # pour le cas local save_balance_transaction_from_chargen'est pas testée
                balance_txn_obj, created = save_balance_transaction_from_charge(
                    bal=bal,
                    data_object=charge, # ✅ Charge Stripe
                    balance_txn_id=balance_txn_id,
                    charge_succeeded_id=latest_charge_id,
                    webhook_event=webhook_event,
                    payment_intent_id=payment_intent_id
                )

                if not balance_txn_obj:
                    _webhook_status_update(
                    webhook_event,
                    True, # car cette partie du traitement est optionnelle
                    f"❌ Données balance manquantes attendre la correction du Webhook"
                    ) # pas important si not balance_txn_obj

                # On préfère arréter le traitement de l'év?enement àce niveau est 
                # attendre charge.succeed si elle n'est pas encore envoyée par Stripe
                # et ne pas passer à l'étape Payment même si les données sont isponibles

        return HttpResponse(status=200) # car c'est une partie du cod optionnelle

    except Exception as e:
        error_msg = f"💥 Erreur critique dans traitement de payment_intent.succeeded : {e}"
        append_webhook_log(webhook_event, error_msg)

        _webhook_status_update(
            webhook_event,
            False, 
            f"❌ {error_msg}"
        )
        return JsonResponse({'error': 'technical_error'}, status=500)
    


def handle_charge_succeeded(user_admin, data_object, webhook_event, bal=None):
    """
    💳 Traitement de l’événement Stripe `charge.succeeded`

    Cet événement est déclenché juste après `payment_intent.succeeded` et 
    fournit les informations financières détaillées d’une charge :
    - Montant réellement facturé
    - Frais Stripe exacts
    - Informations carte bancaire
    - Identifiant de la balance transaction
    - Pays d’origine, devise, réseau carte, etc.

    ⚠️ Contrairement à `payment_intent.succeeded` :
        → `charge.succeeded` n'indique PAS encore que l'argent est disponible.  
          Il confirme uniquement que la charge a été capturée avec succès.

    Dans notre système :
        - `payment_intent.succeeded` marque la facture comme DRAFT (paiement initié).
        - `charge.succeeded` complète les détails financiers et crée la BalanceTransaction.
        - `balance.available` finalise le paiement (invoice.PAID + mise à jour Payment/Horaire).

    -------------------------------------------------------------------------

    🔍 Rôle principal de cette fonction :
        1. Vérifier la cohérence des montants facturés
        2. Enregistrer ou mettre à jour :
            - les détails de la charge
            - la BalanceTransaction liée
            - la PaymentIntentTransaction pour tracer PI ↔ Charge ↔ Balance
        3. Mettre la facture en statut DRAFT si elle ne l’est pas déjà
        4. Mettre la Demande_paiement en EN_ATTENTE jusqu’à disponibilité des fonds
        5. Garantir que la transaction Stripe est traçable et complète en base de données

    -------------------------------------------------------------------------

    🧩 Paramètres :
        webhook_event : WebhookEvent
            Instance enregistrée dans notre base, permettant d'ajouter des logs
            et de suivre l'état du traitement (succès/erreur).
        
        data_object : dict
            Le contenu JSON Stripe de l’objet `charge`.

        user_admin : User
            Super administrateur pour recevoir d'éventuelles alertes critiques
            (cohérence montants, anomalies, fraudes…)

        bal : dict (optionnel)
            Utilisé uniquement pour les tests en environnement local (mock).  
            En production, la balance transaction est toujours récupérée via l'API Stripe.

    -------------------------------------------------------------------------

    🎯 Remarques importantes :
        - La récupération de `balance_transaction` est *obligatoire* pour enregistrer 
          correctement la transaction dans notre comptabilité interne.
          Si elle est absente → erreur 500 → webhook doit être corrigé.

        - `charge.succeeded` peut parfois arriver après `balance.available`.
          Ce cas rare est déjà géré dans la logique.

        - La fonction ne marque JAMAIS la facture comme PAID.
          Seul l’événement `balance.available` peut le faire (argent réellement reçu).

    
    """
    # Mode des Webhook Test / Live pour permettre en mode teste 
    # de passer austatus=PAID POUR PAYMENT car Stripe en 
    # mode teste n'envoie pas de webhookbalance
    # STRIPE_LIVE_MODE variable booleen si mode teste STRIPE_LIVE_MODE=False

    append_webhook_log(
    webhook_event,
    f"🌍 Environnement Stripe détecté : {'LIVE' if STRIPE_LIVE_MODE else 'TEST'}")

    charge_succeeded_id = data_object['id']
    append_webhook_log(webhook_event, 
        f"✅ [charge_succeeded_id: {charge_succeeded_id}] Début du traitement charge.succeeded")

    # 🔍 EXTRACTION METADATA
    invoice_id = data_object.get("metadata", {}).get("invoice_id")

    # 🛡️ VALIDATION DES MÉTADONNÉES
    if not invoice_id:
        append_webhook_log(webhook_event, 
            f"⚠️ [charge_succeeded_id: {charge_succeeded_id}] Aucun invoice_id trouvé dans metadata")
        
        _webhook_status_update(webhook_event, 
            is_fully_completed=False,
            message="❌ Données manquantes : invoice_id absent"
        )

        return JsonResponse({'error': 'Invalid invoice_id'}, status=500)

    try:
        # 🔎 RÉCUPÉRATION DE LA FACTURE
        invoice = Invoice.objects.filter(id=invoice_id).first()
        if not invoice:
            append_webhook_log(webhook_event, 
                f"❌ [charge_succeeded_id {charge_succeeded_id}] Facture {invoice_id} introuvable en BDD")
            
            _webhook_status_update(
                webhook_event,
                is_fully_completed=False,
                message="❌ Facture introuvable en BDD"
            )
            return

        # 🚨 Cas très rare
        # il se peut que lévènement charge.succeeded a été traité 
        # en retard et que lévènement balance.available est traité avant
        if invoice.status == Invoice.PAID:
            _webhook_status_update(
                webhook_event, 
                True,
                f"🏁 [charge_succeeded_id {charge_succeeded_id}] Facture {invoice_id} est déjà marqué PAID."
            )
            return HttpResponse(status=200)
        
        # 🟡 MARQUER LA FACTURE COMME DRAFT et invoice.stripe_charge_id = charge_succeeded_id,
        #  seule l'évènent balance.available peut changer en PAID (voire le reste des informations non mises à jour)
        invoice.status = Invoice.DRAFT if STRIPE_LIVE_MODE else Invoice.PAID  # pour les testes de simulations seulement
        invoice.paid_at = timezone.now()
        invoice.stripe_charge_id = charge_succeeded_id
        invoice.save()

        append_webhook_log(webhook_event,
            f"✅ Facture {invoice_id} marquée DRAFT (charge.succeeded) / invoice.paid_at = {timezone.now()} / invoice.stripe_charge_id = {charge_succeeded_id}"
        )

        # tester la cohérence du montant
        coherent = verifier_coherence_montants(
                    texte1="charge.succeeded",
                    texte2="Invoice BDD",
                    montant1=data_object.get("amount"),
                    montant2=invoice.total,
                    abs_tol=5,
                    user_admin=user_admin
                )
        if not coherent: # Non bloquante erreur (frode, Sripe, BDD)
            append_webhook_log(webhook_event,
                    f"💥 Incohérence critique invoice.toal={invoice.total} centimes dans BDD\n"
                    f"data_object.get('amount')={data_object.get('amount')} centime d'évènement charge.succeeded"
                    )
            logger.warning(
                f"💥 Incohérence critique invoice.toal={invoice.total} centimes dans BDD\n"
                f"data_object.get('amount')={data_object.get('amount')} centime d'évènement charge.succeeded"
                )
            # envoie émail *a l'admin
            envoie_email_multiple(user_admin.id, [user_admin.id], f"💥 Incohérence critique invoice.toal={invoice.total} centimes dans BDD\n", f"💥 data_object.get('amount')={data_object.get('amount')} centime d'évènement charge.succeeded")

        # 📌 GÉRER LA DEMANDE DE PAIEMENT ASSOCIÉE
        if not invoice.demande_paiement: # Oui bloquante, erreur BDD
            _webhook_status_update(
                webhook_event,
                False,
                f"ℹ️ Aucune demande de paiement associée à l'invoice {invoice_id} dans la BDD, erreur système"
            )
            return

        demande_paiement = Demande_paiement.objects.filter(id=invoice.demande_paiement.id).first()
        if not demande_paiement: # Oui bloquante, erreur BDD
            _webhook_status_update(
                webhook_event,
                False,
                f"ℹ️ Demande_paiement introuvable pour invoice {invoice_id} dans la BDD, erreur système"
            )
            return

        # Mise à jour Demande_paiement status Enattente
        ancien_statut = demande_paiement.statut_demande
        demande_paiement.statut_demande = Demande_paiement.EN_COURS if STRIPE_LIVE_MODE else Demande_paiement.REALISER
        demande_paiement.save()

        append_webhook_log(webhook_event,
            f"📝 Demande_paiement {demande_paiement.id} mise EN_ATTENTE "
            f"({ancien_statut} → {Demande_paiement.EN_ATTENTE})"
        )

        # ============================================================
        #   🔵 ETAPE :  BALANCE TRANSACTION : Obligatoire 
        # Mise à jour / création du BalanceTransaction en BDD
        # passer à la création Payment MáJ Demande_paiement:status, Horaire
        # ============================================================

        balance_txn_id = data_object.get("balance_transaction")
        payment_intent_id = data_object.get("payment_intent")

        # --------------------------------------------------------
        # 1️⃣ Invoice → Attendre l'évènement Balance pour passer au statut PAID en mode Life
        # --------------------------------------------------------
        payment_intent_id = data_object.get("payment_intent")
        stripe_payment_intent_id=invoice.stripe_payment_intent_id
        if not stripe_payment_intent_id:
            invoice.stripe_payment_intent_id = payment_intent_id if payment_intent_id else None
            invoice.balance_txn_id = balance_txn_id if balance_txn_id else None
            if STRIPE_LIVE_MODE: invoice.status = Invoice.PAID
            invoice.save()
            append_webhook_log(
                webhook_event, f"📌 Facture {invoice.id} mise à jour, invoice.stripe_payment_intent_id = {payment_intent_id} / invoice.balance_txn_id = {balance_txn_id} ")
        
        payment, created = Payment.objects.update_or_create(
            invoice=invoice,
            defaults={
                "amount": invoice.total / 100,
                "reference": stripe_payment_intent_id if stripe_payment_intent_id else None,
                "currency": data_object.get("currency", "eur"),
                "status": Payment.PENDING if STRIPE_LIVE_MODE else Payment.APPROVED,
            }
        )

        append_webhook_log(
                webhook_event, f"📌 Payment {payment.id} créer ou  mis à jour reference = {payment_intent_id} "
                f"📌 DEBUG Payment status après save = {payment.status} / created={created}")


        # --------------------------------------------------------
        # 3️⃣ Demande_paiement → lien payment_id
        # --------------------------------------------------------
        demande_paiement=Demande_paiement.objects.filter(id=demande_paiement.id).first()
        demande_paiement.statut_demande = Demande_paiement.EN_COURS  if STRIPE_LIVE_MODE else Demande_paiement.REALISER
        demande_paiement.save()

        append_webhook_log(
            webhook_event,
            f"📌 Mise à jour Demande_paiement payment_id={payment.id}."
            f"📌 DEBUG Demande_paiement status après save = {demande_paiement.statut_demande}")

        # --------------------------------------------------------
        # 4️⃣ Horaire → tous liés au même payment_id
        # --------------------------------------------------------
        Horaire.objects.filter(
            demande_paiement_id=demande_paiement.id
        ).update(
            payment_id= None if STRIPE_LIVE_MODE else payment.id
        )

        horaire_qs = Horaire.objects.filter(demande_paiement_id=demande_paiement.id)

        append_webhook_log(
            webhook_event,
            f"📌 Exemple Horaire payment_id={horaire_qs.first().payment_id if horaire_qs.exists() else 'N/A'}"
        )

        # traitement de la balance à part
        if not balance_txn_id: # Teste bloquant en cas Life
            if STRIPE_LIVE_MODE:
                # ❌ En LIVE → ERREUR CRITIQUE
                _webhook_status_update(
                    webhook_event,
                    False,
                    "❌ Aucun balance_transaction trouvé dans charge.succeeded (LIVE)"
                )
                return JsonResponse({'error': 'balance_transaction missing'}, status=500)
            
            else:
                # 🧪 En TEST → comportement attendu
                append_webhook_log(
                    webhook_event,
                    "🧪 Mode TEST : balance_transaction absente (comportement Stripe normal)"
                )
                return # Impossible de continuer en mode teste


        # ----------------------------
        # 3️⃣ Récupération BALANCE TRANSACTION
        # ----------------------------

        try:
            bal = stripe.BalanceTransaction.retrieve(balance_txn_id)
            if bal:
                
                append_webhook_log(
                    webhook_event,
                    f"📘 BalanceTransaction récupérée : {balance_txn_id}"
                )
            else:
                _webhook_status_update(
                webhook_event,
                False,
                f"❌ Données balance manquantes attendre la correction du Webhook"
                )
                if STRIPE_LIVE_MODE:
                    return JsonResponse({'error Stripe': 'données balance manquante attendre la correction du Webhook'}, status=500)
                else: return

        except Exception as e:
            append_webhook_log(
                webhook_event,
                f"⚠️ Impossible de récupérer BalanceTransaction Stripe : {e}. "
                f"Utilisation de la valeur par défaut."
            )
            if STRIPE_LIVE_MODE:
                return JsonResponse({'error Stripe': 'données balance manquante attendre la correction du Webhook'}, status=500)
            else: return
        

        # ----------------------------
        # 4️⃣ Mise à jour / création du BalanceTransaction en BDD
        # ----------------------------
        from datetime import timezone as dt_timezone

        with transaction.atomic(): 
            balance_txn_obj, created = save_balance_transaction_from_charge(
                bal=bal,
                data_object=data_object,
                balance_txn_id=balance_txn_id,
                charge_succeeded_id=charge_succeeded_id,
                webhook_event=webhook_event,
                payment_intent_id=payment_intent_id
            )

            if not balance_txn_obj: # Erreur non bloquante données Stripe manquantes ou incohérantes
                _webhook_status_update(
                webhook_event,
                False,
                f"❌ Données balance manquantes attendre l'évènement Webhook Balance, Erreur non bloquante données Stripe manquantes ou incohérantes"
                )
                

        # ============================================================
        # 🔒 VALIDATION FINALE NON BLOQUANTE
        # ============================================================

        errors = []
        if STRIPE_LIVE_MODE:
            # 1️⃣ Vérification Invoice
            if invoice.status  != Invoice.DRAFT:
                errors.append(f"Invoice {invoice.id} n'est pas en statut DRAFT (statut={invoice.status})")

            if  invoice.stripe_charge_id is None:
                errors.append("stripe_charge_id manquant sur Invoice")

            if invoice.balance_txn_id is None:
                errors.append("balance_txn_id manquant sur Invoice")

            # 2️⃣ Vérification BalanceTransaction
            if not balance_txn_obj:
                errors.append("BalanceTransaction absente en BDD")

            else:
                if balance_txn_obj.status != "pending":
                    append_webhook_log(
                        webhook_event,
                        f"ℹ️ BalanceTransaction status={balance_txn_obj.status} (LIVE)"
                    )


            # 3️⃣ Vérification Payment
            if not Payment.objects.filter(invoice=invoice, status=Payment.PENDING).exists():
                errors.append("Payment non en attente ou manquant")

            # 4️⃣ Vérification Demande_paiement
            if demande_paiement.statut_demande != Demande_paiement.EN_COURS:
                errors.append(
                    f"Demande_paiement statut invalide ({demande_paiement.statut_demande})"
                )

            # 5️⃣ Vérification Horaire
            if Horaire.objects.filter(
                demande_paiement_id=demande_paiement.id,
                payment_id__isnull=True
            ).exists():
                errors.append(f"Certains horaires ne sont pas liés au payment / STRIPE_LIVE_MODE={STRIPE_LIVE_MODE} ")
        else:
            # 1️⃣ Vérification Invoice
            if invoice.status != Invoice.PAID:
                errors.append(f"Invoice {invoice.id} n'est pas en statut PAID (statut={invoice.status})")

            if  invoice.stripe_charge_id is None:
                errors.append("stripe_charge_id manquant sur Invoice")

            if invoice.balance_txn_id is None:
                errors.append("balance_txn_id manquant sur Invoice")

            # 2️⃣ Vérification BalanceTransaction
            if not balance_txn_obj:
                errors.append("BalanceTransaction absente en BDD")

            else:
                append_webhook_log(
                    webhook_event,
                        "🧪 Mode TEST : statut balance non bloquant"
                    )


                # 3️⃣ Vérification Payment
                if not Payment.objects.filter(invoice=invoice, status=Payment.APPROVED).exists():
                    errors.append("Payment non approuvé  ou manquant")

                # 4️⃣ Vérification Demande_paiement
                if demande_paiement.statut_demande != Demande_paiement.REALISER:
                    errors.append(
                        f"Demande_paiement statut invalide ({demande_paiement.statut_demande})"
                    )

                # 5️⃣ Vérification Horaire
                if Horaire.objects.filter(
                    demande_paiement_id=demande_paiement.id,
                    payment_id__isnull=True
                ).exists():
                    errors.append(f"Certains horaires ne sont pas liés au payment / STRIPE_LIVE_MODE={STRIPE_LIVE_MODE} / webhook_event.id={webhook_event.id}")

            # ------------------------------------------------------------
            # Résultat de validation
            # ------------------------------------------------------------
            if errors:
                error_message = "❌ Validation finale AVANT balance.available échouée :\n" + "\n".join(errors)

                append_webhook_log(webhook_event, error_message)

                _webhook_status_update(
                    webhook_event,
                    False,
                    error_message
                )

            append_webhook_log(
                webhook_event,
                "✅ Validation finale OK – prêt pour balance.available"
            )

            # Fin traitement avec succès
            _webhook_status_update(
                    webhook_event, 
                    True,
                    "🏁 Traitement de charge.succeeded complété avec succès"
                )

    except Exception as e:
        error_msg = f"💥 Erreur critique dans traitement de charge.succeeded : {e}"
        append_webhook_log(webhook_event, error_msg)

        _webhook_status_update(
            webhook_event,
            False,
            f"❌ {error_msg}"
        )

        return JsonResponse({'error': 'technical_error'}, status=500)
    return HttpResponse(status=200)



 

def handle_charge_refunded_unified(user_admin, data_object, webhook_event):
    """
    🔄 Traitement quand un remboursement est effectué - VERSION UNIFIÉE, non encore traité
    """
    _webhook_status_update(
            webhook_event, 
            is_fully_completed=False,
            message=f"🔄 Traitement quand un remboursement est effectué - VERSION UNIFIÉE, non encore traité"
        )
    return HttpResponse(status=200)

def handle_charge_refund_updated_unified(user_admin, data_object, webhook_event):
    """
    🔄 Traitement quand un remboursement est mis à jour - non encore traité
    """
    _webhook_status_update(
            webhook_event, 
            is_fully_completed=True,
            message=f"🔄 Traitement quand un remboursement est mis à jour - non encore traité"
        )
    return HttpResponse(status=200)



# ===================================================================
# 📦 HANDLERS D'ÉVÉNEMENTS DEBUT
# ===================================================================

def handle_charge_refunded_transfert(charge):
    """
    🔄 Traitement quand un remboursement est effectué
    Adapté pour stripe_transfert_webhook qui passe data_object directement
    
    Args:
        charge: L'objet charge (déjà event['data']['object'])
    """
    logger.info(f"🔄 Remboursement effectué : {charge['id']}")
    
    # Informations sur le remboursement
    amount_refunded = charge.get('amount_refunded', 0)
    currency = charge.get('currency', 'eur')
    refunded = charge.get('refunded', False)
    
    logger.info(
        f"💰 Montant remboursé : {amount_refunded/100:.2f} {currency} | "
        f"Complètement remboursé : {refunded}"
    )
    
    # Trouver la facture associée
    payment_intent_id = charge.get('payment_intent')
    if payment_intent_id:
        try:
            invoice = Invoice.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
            if invoice:
                # Marquer comme remboursée
                invoice.status = "refunded"
                invoice.refunded_at = timezone.now()
                
                # Si c'est un remboursement partiel, on peut le noter
                if amount_refunded > 0 and amount_refunded < charge.get('amount', 0):
                    invoice.refund_amount = amount_refunded / 100  # Convertir en unités
                    logger.info(f"↩️ Remboursement partiel : {amount_refunded/100:.2f} {currency}")
                
                invoice.save()
                logger.info(f"🔄 Facture ID={invoice.id} marquée comme remboursée")
            else:
                logger.warning(f"⚠️ Aucune facture trouvée pour PaymentIntent: {payment_intent_id}")
        except Exception as e:
            logger.error(f"💥 Erreur mise à jour facture: {e}")
    else:
        logger.warning(f"⚠️ Aucun PaymentIntent trouvé pour la charge: {charge['id']}")


def handle_charge_refund_updated_transfert(charge):
    """
    🔄 Traitement quand un remboursement de charge est mis à jour
    Adapté pour stripe_transfert_webhook qui passe data_object directement
    
    Args:
        charge: L'objet charge (déjà event['data']['object'])
    """
    logger.info(
        f"🔄 Mise à jour remboursement charge : {charge['id']} | "
        f"Montant remboursé : {charge.get('amount_refunded', 0)/100:.2f} {charge['currency']} | "
        f"Remboursé : {charge.get('refunded', False)}"
    )
    
    # ⚠️ Dans stripe_transfert_webhook, on n'a pas previous_attributes
    # On se base uniquement sur l'état actuel pour le logging
    
    # Loguer les informations importantes sur le remboursement
    amount_refunded = charge.get('amount_refunded', 0)
    total_amount = charge.get('amount', 0)
    currency = charge.get('currency', 'eur')
    refunded = charge.get('refunded', False)
    
    # Détecter le type de remboursement basé sur l'état actuel
    if amount_refunded == 0:
        logger.info("💡 Aucun remboursement effectué")
    elif amount_refunded == total_amount:
        logger.info("✅ Remboursement complet")
    else:
        logger.info(f"↩️ Remboursement partiel : {amount_refunded/100:.2f} {currency} sur {total_amount/100:.2f} {currency}")
    
    # Si complètement remboursé, mettre à jour la facture
    if refunded:
        payment_intent_id = charge.get('payment_intent')
        if payment_intent_id:
            try:
                invoice = Invoice.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
                if invoice and invoice.status != "refunded":
                    invoice.status = "refunded"
                    invoice.refunded_at = timezone.now()
                    invoice.save()
                    logger.info(f"🔄 Facture ID={invoice.id} marquée comme remboursée")
            except Exception as e:
                logger.error(f"💥 Erreur mise à jour facture: {e}")



# à vérifier#############
def handle_charge_succeeded_transfert(charge):
    """
    💳 Traitement quand une charge réussit
    Adapté pour stripe_transfert_webhook qui passe data_object directement
    
    Args:
        charge: L'objet charge (déjà event['data']['object'])
    """
    logger.info(f"💳 Charge réussie : {charge['id']} - Montant : {charge['amount']/100:.2f} {charge['currency']}")
    
    # Informations détaillées sur la charge
    amount = charge.get('amount', 0)
    currency = charge.get('currency', 'eur')
    captured = charge.get('captured', False)
    payment_intent_id = charge.get('payment_intent')
    
    logger.info(
        f"✅ Statut : {charge.get('status', 'unknown')} | "
        f"Capturée : {captured} | "
        f"Payment Intent : {payment_intent_id}"
    )
    
    # Si la charge est capturée (fonds réellement prélevés)
    if captured:
        logger.info(f"💰 Charge {charge['id']} capturée - Fonds prélevés")
        
        # Mettre à jour la facture associée si nécessaire
        if payment_intent_id:
            try:
                invoice = Invoice.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
                if invoice:
                    # Marquer comme capturée si pas déjà fait
                    if not invoice.captured_at:
                        invoice.captured_at = timezone.now()
                        invoice.save()
                        logger.info(f"✅ Facture ID={invoice.id} marquée comme capturée")
            except Exception as e:
                logger.error(f"💥 Erreur mise à jour facture: {e}")


from django.db import transaction


def handle_payment_intent_created( user_admin, data_object, webhook_event):
    """
    🆕 Traitement quand un PaymentIntent est créé.
    Adapté pour stripe_transfert_webhook qui passe data_object directement.

    Args:
        payment_intent: dict - L'objet payment_intent (déjà event['data']['object'])
    """
    
    try:
        payment_intent_amount = data_object['amount']
        stripe_payment_intent_id = data_object['id']
        if stripe_payment_intent_id is not None and payment_intent_amount is not None:
        # 🧾 Log initial
            append_webhook_log(webhook_event, 
                f"🆕 PaymentIntent créé : {data_object['id']} | "
                f"Montant : {payment_intent_amount/100:.2f} {data_object['currency']} | "
                f"Statut : {data_object['status']}" )

        # 💳 Détails de paiement
        payment_method_types = data_object.get('payment_method_types', [])
        append_webhook_log(webhook_event, 
            f"💳 Méthodes de paiement : {', '.join(payment_method_types)} | "
            f"Capture method : {data_object.get('capture_method', 'automatic')}")
        # 📋 Autres métadonnées utiles
        metadata = data_object.get('metadata', {})
        if metadata:
            append_webhook_log(webhook_event, 
            f"📋 Métadonnées : {metadata}")

        # 🔗 Lier le PaymentIntent à la facture (si metadata.invoice_id présent) c'est l'action la plus importante pour cet évènement
        invoice_id = data_object.get('metadata', {}).get('invoice_id')
        if invoice_id:
            try:
                with transaction.atomic():
                    invoice = Invoice.objects.select_for_update().get(id=invoice_id)
                    if invoice.status == Invoice.PAID:
                        _webhook_status_update(
                            webhook_event, 
                            True,
                            f"🏁  Facture {invoice_id} est déjà marqué PAID."
                            f"\n🏁 On suppose que la suite des traitement du cas Invoice.PAID est effectué."
                        )
                        return HttpResponse(status=200)
                    
                    if invoice.stripe_payment_intent_id and  invoice.stripe_payment_intent_id != data_object['id']:
                        texte=f"💥 invoice.stripe_payment_intent_id: {invoice.stripe_payment_intent_id}\n"
                        f"est différent de data_object['id']:{data_object['id']}"
                        envoie_email_multiple(user_admin.id, [user_admin.id], "💥 Allerte: stripe_payment_intent_id du webhook ne correspond pas à celui de la facture", texte)
                        append_webhook_log(webhook_event, texte)

                    invoice.stripe_payment_intent_id = data_object['id'] # car la priorité est aux données du webhook et non pas aux données de la BDD
                    invoice.save(update_fields=["stripe_payment_intent_id"])
                    append_webhook_log(webhook_event, f"📝 Facture {invoice.id} liée au PaymentIntent {data_object['id']} du webhook")

                    # tester de cohérence entre payment_intent['amount'] invoice.total
                    coherent = verifier_coherence_montants(
                        texte1="facture",
                        texte2="payment_intent",
                        montant1=invoice.total,
                        montant2=payment_intent_amount,
                        abs_tol=5,
                        user_admin=user_admin
                    )
                    if not coherent: pass # l'email est déjà envoyé à l'admin par verifier_coherence_montants avec une allerte webhook_log

                    _webhook_status_update(webhook_event, is_fully_completed=True, message=f"")
                    
            except Invoice.DoesNotExist:
                _webhook_status_update(webhook_event, is_fully_completed=False, 
                                       message=f"⚠️ Facture {invoice_id} introuvable pour PaymentIntent {data_object['id']}")
                
            except Exception as e:
                _webhook_status_update(webhook_event, is_fully_completed=False, 
                                       message=f"💥 Erreur lors de la liaison du PaymentIntent à la facture {invoice_id} : {e}")

        else:
            _webhook_status_update(webhook_event, is_fully_completed=False, 
                                       message="⚠️ PaymentIntent sans invoice_id dans metadata")

    except Exception as e:
        _webhook_status_update(webhook_event, is_fully_completed=False, 
                                       message=f"❌ Erreur globale dans handle_payment_intent_created : {e}")


def handle_refund_created(user_admin, data_object, webhook_event):
    """
    🔔 Gestion du webhook Stripe : charge.updated

    Rôle :
        - Lier la Charge Stripe à un RefundPayment interne
        - Marquer le remboursement comme PENDING
        - Récupérer et enregistrer la BalanceTransaction
        - Préparer la suite du flux (balance.available)
    """

    # -------------------------------------------------
    # 1️⃣ Extraction des données Stripe
    # -------------------------------------------------
    charge_updated_id = data_object["id"]
    balance_txn_id = data_object.get("balance_transaction")
    payment_intent_id = data_object.get("payment_intent")
    idempotency_key = data_object.get("idempotency_key")
    local_refund_id = data_object.get("metadata", {}).get("local_refund_id")

    append_webhook_log(
        webhook_event,
        f"✅ Début du traitement du Webhook : charge.updated"
        f"\n1️⃣ charge_updated_id: {charge_updated_id}"
        f"\n2️⃣ balance_txn_id: {balance_txn_id}"
        f"\n3️⃣ payment_intent_id: {payment_intent_id}"
        f"\n4️⃣ idempotency_key: {idempotency_key}"
        f"\n5️⃣ local_refund_id: {local_refund_id}"
    )

    # -------------------------------------------------
    # 2️⃣ Validation des métadonnées (OBLIGATOIRE)
    # -------------------------------------------------
    if not local_refund_id:
        append_webhook_log(
            webhook_event,
            f"⚠️ [charge_updated_id: {charge_updated_id}] Aucun local_refund_id trouvé dans metadata"
        )

        _webhook_status_update(
            webhook_event,
            is_fully_completed=False,
            message="❌ Données manquantes : local_refund_id absent"
        )
        return HttpResponse(status=200)

    # -------------------------------------------------
    # 3️⃣ Récupération du RefundPayment en BDD
    # -------------------------------------------------
    refund_payment = RefundPayment.objects.filter(
        id=local_refund_id,
    ).first()

    if not refund_payment:
        append_webhook_log(
            webhook_event,
            f"❌ [charge_updated_id {charge_updated_id}] RefundPayment {local_refund_id} introuvable en BDD"
        )

        _webhook_status_update(
            webhook_event,
            is_fully_completed=False,
            message="❌ RefundPayment introuvable en BDD"
        )
        return HttpResponse(status=200)

    # -------------------------------------------------
    # 4️⃣ Cas rare : charge.updated reçu APRÈS balance.available
    # -------------------------------------------------
    if refund_payment.status == RefundPayment.APPROVED:
        _webhook_status_update(
            webhook_event,
            True,
            f"🏁 [charge_updated_id {charge_updated_id}] RefundPayment {local_refund_id} déjà APPROVED"
        )
        return HttpResponse(status=200)

    # -------------------------------------------------
    # 5️⃣ Marquer le remboursement comme PENDING
    # -------------------------------------------------
    refund_payment.status = RefundPayment.PENDING
    refund_payment.charge_id = charge_updated_id
    refund_payment.balance_txn_id = balance_txn_id
    refund_payment.payment_intent_id = payment_intent_id
    refund_payment.save()

    append_webhook_log(
        webhook_event,
        f"\n✅ RefundPayment {refund_payment.id} marqué PENDING"
        f"\n✅ charge_id={charge_updated_id}"
        f"\n✅ balance_txn_id={balance_txn_id}"
        f"\n✅ payment_intent_id={payment_intent_id}"
    )

    # -------------------------------------------------
    # 6️⃣ BalanceTransaction : OBLIGATOIRE
    # -------------------------------------------------
    if not balance_txn_id:
        _webhook_status_update(
            webhook_event,
            False,
            "❌ Aucun balance_transaction trouvé dans charge.updated"
        )
        return HttpResponse(status=200)

    # -------------------------------------------------
    # 7️⃣ Récupération de la BalanceTransaction Stripe
    # -------------------------------------------------
    bal = None
    try:
        bal = stripe.BalanceTransaction.retrieve(balance_txn_id)
        if bal:
            append_webhook_log(
                webhook_event,
                f"📘 BalanceTransaction récupérée : {balance_txn_id}"
            )
    except Exception as e:
        append_webhook_log(
            webhook_event,
            f"⚠️ Impossible de récupérer BalanceTransaction Stripe : {e}"
        )

    # -------------------------------------------------
    # 8️⃣ Création / Mise à jour BalanceTransaction en BDD
    # -------------------------------------------------
    with transaction.atomic():
        balance_txn_obj, created = save_balance_transaction_from_charge(
            bal=bal,
            data_object=data_object,
            balance_txn_id=balance_txn_id,
            charge_succeeded_id=charge_updated_id,
            webhook_event=webhook_event,
            payment_intent_id=payment_intent_id
        )

        # Erreur NON bloquante (balance.available peut arriver après)
        if not balance_txn_obj:
            _webhook_status_update(
                webhook_event,
                False,
                "❌ Données balance manquantes — attente webhook balance.available"
            )

    return HttpResponse(status=200)




def handle_charge_updated(user_admin, data_object, webhook_event):
    """
    🔔 Gestion du webhook Stripe : charge.updated

    Rôle :
        - Lier la Charge Stripe à un RefundPayment interne
        - Marquer le remboursement comme PENDING
        - Récupérer et enregistrer la BalanceTransaction
        - Préparer la suite du flux (balance.available)
    """

    # -------------------------------------------------
    # 1️⃣ Extraction des données Stripe
    # -------------------------------------------------
    charge_updated_id = data_object["id"]
    balance_txn_id = data_object.get("balance_transaction")
    payment_intent_id = data_object.get("payment_intent")
    idempotency_key = data_object.get("idempotency_key")
    local_refund_id = data_object.get("metadata", {}).get("local_refund_id")

    append_webhook_log(
        webhook_event,
        f"✅ Début du traitement du Webhook : charge.updated"
        f"\n1️⃣ charge_updated_id: {charge_updated_id}"
        f"\n2️⃣ balance_txn_id: {balance_txn_id}"
        f"\n3️⃣ payment_intent_id: {payment_intent_id}"
        f"\n4️⃣ idempotency_key: {idempotency_key}"
        f"\n5️⃣ local_refund_id: {local_refund_id}"
    )

    # -------------------------------------------------
    # 2️⃣ Validation des métadonnées (OBLIGATOIRE)
    # -------------------------------------------------
    if not local_refund_id:
        append_webhook_log(
            webhook_event,
            f"⚠️ [charge_updated_id: {charge_updated_id}] Aucun local_refund_id trouvé dans metadata"
        )

        _webhook_status_update(
            webhook_event,
            is_fully_completed=False,
            message="❌ Données manquantes : local_refund_id absent"
        )
        return HttpResponse(status=200)

    # -------------------------------------------------
    # 3️⃣ Récupération du RefundPayment en BDD
    # -------------------------------------------------
    refund_payment = RefundPayment.objects.filter(
        id=local_refund_id,
    ).first()

    if not refund_payment:
        append_webhook_log(
            webhook_event,
            f"❌ [charge_updated_id {charge_updated_id}] RefundPayment {local_refund_id} introuvable en BDD"
        )

        _webhook_status_update(
            webhook_event,
            is_fully_completed=False,
            message="❌ RefundPayment introuvable en BDD"
        )
        return HttpResponse(status=200)

    # -------------------------------------------------
    # 4️⃣ Cas rare : charge.updated reçu APRÈS balance.available
    # -------------------------------------------------
    if refund_payment.status == RefundPayment.APPROVED:
        _webhook_status_update(
            webhook_event,
            True,
            f"🏁 [charge_updated_id {charge_updated_id}] RefundPayment {local_refund_id} déjà APPROVED"
        )
        return HttpResponse(status=200)

    # -------------------------------------------------
    # 5️⃣ Marquer le remboursement comme PENDING
    # -------------------------------------------------
    refund_payment.status = RefundPayment.PENDING
    refund_payment.charge_id = charge_updated_id
    refund_payment.balance_txn_id = balance_txn_id
    refund_payment.payment_intent_id = payment_intent_id
    refund_payment.save()

    append_webhook_log(
        webhook_event,
        f"\n✅ RefundPayment {refund_payment.id} marqué PENDING"
        f"\n✅ charge_id={charge_updated_id}"
        f"\n✅ balance_txn_id={balance_txn_id}"
        f"\n✅ payment_intent_id={payment_intent_id}"
    )

    # -------------------------------------------------
    # 6️⃣ BalanceTransaction : OBLIGATOIRE
    # -------------------------------------------------
    if not balance_txn_id:
        _webhook_status_update(
            webhook_event,
            False,
            "❌ Aucun balance_transaction trouvé dans charge.updated"
        )
        return HttpResponse(status=200)

    # -------------------------------------------------
    # 7️⃣ Récupération de la BalanceTransaction Stripe
    # -------------------------------------------------
    bal = None
    try:
        bal = stripe.BalanceTransaction.retrieve(balance_txn_id)
        if bal:
            append_webhook_log(
                webhook_event,
                f"📘 BalanceTransaction récupérée : {balance_txn_id}"
            )
    except Exception as e:
        append_webhook_log(
            webhook_event,
            f"⚠️ Impossible de récupérer BalanceTransaction Stripe : {e}"
        )

    # -------------------------------------------------
    # 8️⃣ Création / Mise à jour BalanceTransaction en BDD
    # -------------------------------------------------
    with transaction.atomic():
        balance_txn_obj, created = save_balance_transaction_from_charge(
            bal=bal,
            data_object=data_object,
            balance_txn_id=balance_txn_id,
            charge_succeeded_id=charge_updated_id,
            webhook_event=webhook_event,
            payment_intent_id=payment_intent_id
        )

        # Erreur NON bloquante (balance.available peut arriver après)
        if not balance_txn_obj:
            _webhook_status_update(
                webhook_event,
                False,
                "❌ Données balance manquantes — attente webhook balance.available"
            )

    return HttpResponse(status=200)



def handle_transfer_created(user_admin, data_object, webhook_event, bal=None):
    """
    Gère le webhook Stripe `transfer.created`.

    Étapes effectuées :
    - Extraction et validation des données Stripe.
    - Récupération du BalanceTransaction.
    - Vérifications de cohérence (montants, destination Stripe du prof).
    - Mise à jour : InvoiceTransfert, Transfer et AccordReglement.
    - Envoi d’un e-mail d’information.

    Remarque: bal est utilisé pour le teste du webhook localement seulement
    """

    from datetime import timezone as dt_timezone

    _webhook_status_update(
        webhook_event, 
        is_fully_completed=False,
        message="📦 Webhook `transfer.created` reçu : traitement en cours..."
    )

    # ------------------------------------------------------------
    # 1️⃣ Extraction des données principales envoyées par Stripe
    # ------------------------------------------------------------
    stripe_transfer_id = data_object.get("id")
    balance_tx_id = data_object.get("balance_transaction")
    metadata = data_object.get("metadata", {}) or {}
    stripe_invoice_id = metadata.get("invoice_id")
    stripe_amount = data_object.get("amount")
    stripe_destination = data_object.get("destination")
    destination_payment = data_object.get("destination_payment") # utile pour suivi avancé (rarement indispensable)
    
    missing = [name for name, value in {
        "invoice_transfert_id": stripe_invoice_id,
        "balance_transaction": balance_tx_id,
        "transfer_id": stripe_transfer_id,
        "amount": stripe_amount,
        "destination": stripe_destination,
    }.items() if not value]

    if missing:
        _webhook_status_update(
            webhook_event,
            is_fully_completed=True,
            message=f"❌ Données manquantes dans transfer.created : {', '.join(missing)} (event ignoré)"
        )
        return HttpResponse(status=200)
        

    _webhook_status_update(
        webhook_event, 
        is_fully_completed=False,
        message=f"🔗 Transfert Stripe détecté : {stripe_transfer_id} (invoice={stripe_invoice_id})"
    )

    # ------------------------------------------------------------
    # 2️⃣ Récupération de la facture correspondante
    # ------------------------------------------------------------
    invoice_transfert = InvoiceTransfert.objects.filter(
        id=stripe_invoice_id,
        stripe_transfer_id=stripe_transfer_id
    ).first()

    if not invoice_transfert:
        _webhook_status_update(
            webhook_event, 
            is_fully_completed=False,
            message=f"❌ Facture introuvable ou non liée : invoice_transfert_id={stripe_invoice_id}"
        )
        

    # ------------------------------------------------------------
    # 3️⃣ Récupération des détails du balance_transaction Stripe
    # ------------------------------------------------------------
    try:
        if not bal: # s'il ne s'agit pas d'un teste local
            balance_tx = stripe.BalanceTransaction.retrieve(balance_tx_id)
        if bal: # pour le teste local
            balance_tx=bal
        montant_net_reel = balance_tx.get("net", 0) / 100
        frais_stripe = balance_tx.get("fee", 0) / 100

        available_on_ts = balance_tx.get("available_on")
        date_mise_en_valeur = (
            datetime.fromtimestamp(available_on_ts, tz=dt_timezone.utc)
            if available_on_ts else None
        )

        _webhook_status_update(
            webhook_event, 
            is_fully_completed=False,
            message=(
                f"💶 BalanceTransaction récupéré : "
                f"net={montant_net_reel}€, frais={frais_stripe}€, "
                f"disponible_le={date_mise_en_valeur}"
            )
        )

    except stripe.error.StripeError as e:
        _webhook_status_update(
            webhook_event,
            is_fully_completed=False,
            message=f"💥 Erreur Stripe lors de retrieve(balance_transaction) : {e}"
        )
        

    except Exception as e:
        _webhook_status_update(
            webhook_event,
            is_fully_completed=False,
            message=f"💥 Erreur inattendue balance_transaction : {e}"
        )
        

    # ------------------------------------------------------------
    # 4️⃣ Test de cohérence : montants + compte Stripe prof
    # ------------------------------------------------------------
    errors = []

    # --- Montant Stripe vs montant facture ---
    is_ok = verifier_coherence_montants(
        texte1="transfer.created",
        texte2="InvoiceTransfert (BDD)",
        montant1=stripe_amount,
        montant2=invoice_transfert.total * 100,
        abs_tol=5,
        user_admin=user_admin
    )

    if not is_ok:
        msg = (
            f"Montant incohérent : Stripe={stripe_amount} centimes vs "
            f"DB={invoice_transfert.total * 100} centimes"
        )
        errors.append(msg)
        logger.warning("💥 " + msg)
        append_webhook_log(webhook_event, "💥 " + msg)

    # --- Vérification compte Stripe du professeur ---
    prof_account = invoice_transfert.user_professeur.professeur.stripe_account_id
    if stripe_destination != prof_account:
        msg = (
            f"Compte Stripe du professeur incorrect : Stripe={stripe_destination} "
            f"vs DB={prof_account}"
        )
        errors.append(msg)
        logger.warning("💥 " + msg)
        append_webhook_log(webhook_event, "💥 " + msg)

    # --- Si incohérences : marquer la facture en FAILED ---
    if errors:
        invoice_transfert.status = InvoiceTransfert.FAILED
        invoice_transfert.save()

        full_error_msg = "⛔ " + " | ".join(errors)
        append_webhook_log(webhook_event, full_error_msg)

        envoie_email_multiple(
            user_admin.id, [user_admin.id],
            "Non conformité des données Stripe",
            full_error_msg
        )

    # ------------------------------------------------------------
    # 5️⃣ Mise à jour de InvoiceTransfert
    # ------------------------------------------------------------
    try:
        if invoice_transfert.status == InvoiceTransfert.PAID:
            _webhook_status_update(
            webhook_event,
            is_fully_completed=True,
            message=f"✅ Facture {invoice_transfert.id} est déjà mise à jour (PAID)"
        )
            return HttpResponse(status=200)
        
        invoice_transfert.status = InvoiceTransfert.INPROGRESS
        invoice_transfert.balance_transaction = balance_tx_id
        invoice_transfert.frais = frais_stripe
        invoice_transfert.montant_net = montant_net_reel
        invoice_transfert.destination_payment = destination_payment if destination_payment else None
        invoice_transfert.save()
        invoice_transfert.generate_pdf()
        invoice_transfert.save()

        _webhook_status_update(
            webhook_event,
            is_fully_completed=False,
            message=f"✅ Facture {invoice_transfert.id} mise à jour (PINPROGRESS)"
        )

    except Exception as e:
        msg = f"💥 Erreur mise à jour facture {invoice_transfert.id} : {e}"
        _webhook_status_update(webhook_event, False, msg)

    # ------------------------------------------------------------
    # 6️⃣ Création/Mise à jour du Transfer
    # ------------------------------------------------------------
    try:
        transfer = Transfer.objects.filter(invoice_transfert=invoice_transfert).first()
        if transfer and transfer.status!=Transfer.PENDING:
            _webhook_status_update(
            webhook_event,
            is_fully_completed=True,
            message=f"✅ Transfer {transfer.id} est déjà mise à jour status={transfer.status}"
        )
            return HttpResponse(status=200)
        
        if transfer is None or transfer.status==Transfer.PENDING:
            transfer, created = Transfer.objects.update_or_create(
                invoice_transfert=invoice_transfert,
                stripe_transfer_id=invoice_transfert.stripe_transfer_id,
                user_transfer_to=invoice_transfert.user_professeur,
                defaults={
                    "amount": data_object.get("amount", 0),
                    "montant_net": montant_net_reel,
                    "frais": frais_stripe,
                    "currency": data_object.get("currency", "eur"),
                    "status": Transfer.PENDING,
                },
            )

            _webhook_status_update(
                webhook_event,
                is_fully_completed=False,
                message=f"{'🆕 Créé' if created else '🔄 Mis à jour'} Transfer ID={transfer.stripe_transfer_id}, status=PENDING" 
            )

    except Exception as e:
        _webhook_status_update(
            webhook_event,
            is_fully_completed=False,
            message=f"💥 Erreur création/mise à jour Transfer : {e}"
        )

    # ------------------------------------------------------------
    # 7️⃣ Mise à jour de l’Accord de règlement (si présent)
    # ------------------------------------------------------------
    try:
        accord_reglement = invoice_transfert.accord_reglement
        if accord_reglement and accord_reglement.status == AccordReglement.PENDING:
            accord_reglement.status = AccordReglement.IN_PROGRESS
            accord_reglement.transfer = transfer
            accord_reglement.save()

        _webhook_status_update(
            webhook_event,
            is_fully_completed=True,
            message="🔄 Accord de règlement mis à jour status = {invoice_transfert.accord_reglement.status}"
        )

    except Exception:
        _webhook_status_update(
            webhook_event,
            is_fully_completed=False,
            message="💥 Erreur lors de la mise à jour de l'accord de règlement"
        )

    # ------------------------------------------------------------
    # 8️⃣ Envoi d’un email au professeur + admin
    # ------------------------------------------------------------
    from datetime import timedelta
    from django.utils import timezone
    date_estimee = timezone.now().date() + timedelta(days=5)
    texte_email = f"""
    Cher Professeur {invoice_transfert.user_professeur.get_full_name()},

    Nous vous informons qu’un transfert de {invoice_transfert.total} € 
    a été créé en votre faveur le {invoice_transfert.created_at:%d/%m/%Y}.

    Les fonds devraient être disponibles au plus tard le 
    {date_estimee.strftime('%d/%m/%Y')}.

    Merci pour votre collaboration.

    Cordialement,
    L’équipe ProfConnect
    """

    result = envoie_email_multiple(
        user_id_envoi=invoice_transfert.user_admin.id,
        liste_user_id_receveurs=[
            invoice_transfert.user_professeur.id,
            invoice_transfert.user_admin.id
        ],
        sujet_email=f"Transfert de {invoice_transfert.total} € créé",
        texte_email=texte_email
    )

    if result.get("erreurs"):
        _webhook_status_update(
            webhook_event,
            is_fully_completed=True,
            message=f"❗ {len(result['erreurs'])} erreur(s) lors de l’envoi des e-mails"
        )
    else:
        _webhook_status_update(
            webhook_event,
            is_fully_completed=True,
            message=f"✅ Envoi des e-mails pour Professeur et admin réussi"
        )
        return HttpResponse(status=200)


# cet évènrement est suite au virement du compte Stripe au compte bancaire administrateur
def handle_payout_created(user_admin, data_object, webhook_event, bal=None):
    """
    💸 Géré lorsque Stripe prépare un virement vers le compte bancaire.
    """
    from datetime import timezone as dt_timezone

    _webhook_status_update(
        webhook_event, 
        is_fully_completed=False,
        message="📦 Webhook `payout.created` reçu : traitement en cours..."
    )

    # ------------------------------------------------------------
    # 1️⃣ Extraction des données principales envoyées par Stripe
    # ------------------------------------------------------------
    stripe_payout_id = data_object.get("id")
    balance_tx_id = data_object.get("balance_transaction")
    metadata = data_object.get("metadata", {}) or {}
    stripe_invoice_id = metadata.get("invoice_transfert_id")
    stripe_amount = data_object.get("amount")
    stripe_destination = data_object.get("destination")

    missing = [name for name, value in {
        "invoice_transfert_id": stripe_invoice_id,
        "balance_transaction": balance_tx_id,
        "transfer_id": stripe_payout_id,
        "amount": stripe_amount,
        "destination": stripe_destination,
    }.items() if not value]

    if missing:
        _webhook_status_update(
            webhook_event, 
            is_fully_completed=False,
            message=f"❌ Données manquantes dans transfer.created : {', '.join(missing)}"
        )
        return JsonResponse({'error': 'Invalid data received from Stripe'}, status=500)

    _webhook_status_update(
        webhook_event, 
        is_fully_completed=False,
        message=f"🔗 Transfert Stripe détecté : {stripe_payout_id} (invoice={stripe_invoice_id})"
    )

    # ------------------------------------------------------------
    # 2️⃣ Récupération de la facture correspondante
    # ------------------------------------------------------------
    invoice_transfert = InvoiceTransfert.objects.filter(
        id=stripe_invoice_id,
    ).first()

    if not invoice_transfert:
        _webhook_status_update(
            webhook_event, 
            is_fully_completed=False,
            message=f"❌ Facture introuvable ou non liée : invoice_transfert_id={stripe_invoice_id}"
        )
        return JsonResponse({'error': 'InvoiceTransfert not found'}, status=500)

    # # ------------------------------------------------------------
    # # 3️⃣ Récupération des détails du balance_transaction Stripe
    # # ------------------------------------------------------------
    # try:
    #     if not bal:
    #         balance_tx = stripe.BalanceTransaction.retrieve(balance_tx_id)
    #     if bal: # pour le teste local
    #         balance_tx=bal
    #     montant_net_reel = balance_tx.get("net", 0) / 100
    #     frais_stripe = balance_tx.get("fee", 0) / 100

    #     available_on_ts = balance_tx.get("available_on")
    #     date_mise_en_valeur = (
    #         datetime.fromtimestamp(available_on_ts, tz=dt_timezone.utc)
    #         if available_on_ts else None
    #     )

    #     _webhook_status_update(
    #         webhook_event, 
    #         is_fully_completed=False,
    #         message=(
    #             f"💶 BalanceTransaction récupéré : "
    #             f"net={montant_net_reel}€, frais={frais_stripe}€, "
    #             f"disponible_le={date_mise_en_valeur}"
    #         )
    #     )

    # except stripe.error.StripeError as e:
    #     _webhook_status_update(
    #         webhook_event,
    #         is_fully_completed=False,
    #         message=f"💥 Erreur Stripe lors de retrieve(balance_transaction) : {e}"
    #     )
    #     return JsonResponse({'error': 'Stripe error retrieving balance_transaction'}, status=500)

    # except Exception as e:
    #     _webhook_status_update(
    #         webhook_event,
    #         is_fully_completed=False,
    #         message=f"💥 Erreur inattendue balance_transaction : {e}"
    #     )
    #     return JsonResponse({'error': f"Unexpected error: {e}"}, status=500)

    # ------------------------------------------------------------
    # 4️⃣ Test de cohérence : montants + compte Stripe prof
    # ------------------------------------------------------------
    errors = []

    # --- Montant Stripe vs montant facture ---
    is_ok = verifier_coherence_montants(
        texte1="transfer.created",
        texte2="InvoiceTransfert (BDD)",
        montant1=stripe_amount,
        montant2=invoice_transfert.total * 100,
        abs_tol=5,
        user_admin=user_admin
    )

    if not is_ok:
        msg = (
            f"Montant incohérent : Stripe={stripe_amount} centimes vs "
            f"DB={invoice_transfert.total * 100} centimes"
        )
        errors.append(msg)
        logger.warning("💥 " + msg)
        append_webhook_log(webhook_event, "💥 " + msg)

    # --- Vérification compte Stripe du professeur ---
    prof_account = invoice_transfert.user_professeur.professeur.stripe_account_id
    if stripe_destination != prof_account:
        msg = (
            f"Compte Stripe du professeur incorrect : Stripe={stripe_destination} "
            f"vs DB={prof_account}"
        )
        errors.append(msg)
        logger.warning("💥 " + msg)
        append_webhook_log(webhook_event, "💥 " + msg)

    # --- Si incohérences : marquer la facture en FAILED ---
    if errors:
        invoice_transfert.status = InvoiceTransfert.FAILED
        invoice_transfert.save()

        full_error_msg = "⛔ " + " | ".join(errors)
        append_webhook_log(webhook_event, full_error_msg)

        envoie_email_multiple(
            user_admin.id, [user_admin.id],
            "Non conformité des données Stripe",
            full_error_msg
        )

        return JsonResponse({
            "error": "Transfert Stripe non conforme",
            "details": errors
        }, status=400)

# non encore développer
def handle_transfer_reversed(user_admin, data_object, webhook_event, transfer=None):
    """
    ↩️ Géré lorsque Stripe annule ou reverse un transfert déjà effectué.
    
    - Met à jour `InvoiceTransfert` avec le statut 'reversed'.
    - Met à jour le `Payment` lié s'il existe.
    """
    try:
        metadata = transfer.get("metadata", {})
        invoice_id = metadata.get("invoice_transfert_id")

        if not invoice_id:
            logger.warning("⚠️ Aucun 'invoice_transfert_id' trouvé dans les metadata du transfert reversé.")
            return

        invoice = InvoiceTransfert.objects.get(id=invoice_id)

        # 🔄 Mise à jour de la facture comme "reversed"
        invoice.status = 'reversed'
        invoice.save()
        logger.info(f"↩️ Transfert reversé pour la facture {invoice.id} (transfer ID: {transfer['id']})")

        # 🔄 Mettre à jour le paiement si existant
        payment = Payment.objects.filter(invoice=invoice).first()
        if payment:
            payment.status = Payment.CANCELED
            payment.save()
            logger.info(f"💳 Paiement lié (ID: {payment.id}) marqué comme CANCELED.")

    except InvoiceTransfert.DoesNotExist:
        logger.error(f"❌ Facture {invoice_id} introuvable pour transfert reversé {transfer['id']}", exc_info=True)
    except Exception as e:
        logger.exception(f"💥 Erreur inattendue lors du traitement d'un transfert reversé : {e}")




def handle_payout_paid(user_admin, data_object, webhook_event):
    """
    ✅ Géré lorsque Stripe confirme que le virement vers le compte bancaire est effectué.
    """
    _webhook_status_update(
            webhook_event, 
            is_fully_completed=False,
            message=f"✅ Géré lorsque Stripe confirme que le virement vers le compte bancaire est effectué. Non traité"
        )
    return HttpResponse(status=200)


def handle_payout_failed(user_admin, data_object, webhook_event):
    """
    🚫 Géré lorsque le virement bancaire échoue.
    """
    _webhook_status_update(
            webhook_event, 
            is_fully_completed=False,
            message=f"🚫 Géré lorsque le virement bancaire échoue. Non achevé"
        )
    return HttpResponse(status=200)

def check_and_close_accord_if_complete(accord: AccordRemboursement):
    """
    🎯 Vérifie si tous les remboursements liés à un accord sont réussis -> auto-close accord
    """
    related_payments = accord.details.values_list('payment', flat=True)
    refunds = RefundPayment.objects.filter(payment_id__in=related_payments)

    if refunds.exists() and all(r.status == RefundPayment.APPROVED for r in refunds):
        accord.status = AccordRemboursement.COMPLETED
        accord.save()
        logger.info(f"🎉 Tous les refunds sont complétés → Accord {accord.id} marqué COMPLÉTÉ")
    else:
        logger.info(f"⏳ Accord {accord.id} pas encore complet - en attente d'autres remboursements")



def handle_refund_updated(user_admin, data_object, webhook_event):
    """
    🔁 Stripe -> refund.updated (modification de statut après création) non important non encore traité
    """
    _webhook_status_update(
            webhook_event, 
            is_fully_completed=True,
            message=f"🔁 Stripe -> refund.updated (modification de statut après création) non important non encore traité"
        )
    return HttpResponse(status=200)

def handle_transfer_updated(user_admin, data_object, webhook_event):
    """
    🔄 Traitement QUAND UN TRANSFERT EST MIS À JOUR
    Gère TOUS les changements de statut : created, paid, failed, etc.
    """
    _webhook_status_update(
            webhook_event, 
            is_fully_completed=False,
            message=f"🔄 Traitement QUAND UN TRANSFERT EST MIS À JOUR"
        )
    return HttpResponse(status=200)

def handle_transfer_paid_success(transfer):
    """Traitement quand un transfert est payé avec succès"""
    try:
        # Récupérer les métadonnées pour identifier le bénéficiaire
        metadata = transfer.get('metadata', {})
        teacher_id = metadata.get('teacher_id')
        invoice_id = metadata.get('invoice_id')
        
        logger.info(f"🎉 TRANSFERT RÉUSSI: {transfer['id']}")
        logger.info(f"   👨‍🏫 Professeur: {teacher_id}")
        logger.info(f"   📄 Facture: {invoice_id}") 
        logger.info(f"   💰 Montant: {transfer['amount']/100:.2f} {transfer['currency']}")
        
        # Mettre à jour votre base de données
        update_transfer_status(transfer['id'], 'paid', teacher_id, invoice_id)
        
    except Exception as e:
        logger.error(f"❌ Erreur traitement transfert payé : {e}")

def handle_transfer_failed(user_admin, data_object, webhook_event):
    """Traitement quand un transfert échoue"""
    
    _webhook_status_update(
            webhook_event, 
            is_fully_completed=False,
            message=f"🔄 Traitement quand un transfert échoue"
        )
    return HttpResponse(status=200)

def handle_transfer_canceled(transfer):
    """Traitement quand un transfert est annulé"""
    logger.warning(f"🛑 TRANSFERT ANNULÉ: {transfer['id']}")
    
    update_transfer_status(transfer['id'], 'canceled')

def update_transfer_status(transfer_id, status, teacher_id=None, invoice_id=None):
    """
    📝 Mettre à jour le statut d'un transfert dans votre base de données
    """
    try:
        # Exemple si vous avez un modèle Transfer ou TeacherPayout
        # if teacher_id:
        #     payout = TeacherPayout.objects.get(
        #         stripe_transfer_id=transfer_id,
        #         teacher_id=teacher_id
        #     )
        #     payout.status = status
        #     if status == 'paid':
        #         payout.paid_at = timezone.now()
        #     payout.save()
        
        logger.info(f"📝 Transfert {transfer_id} mis à jour : {status}")
        
    except Exception as e:
        logger.error(f"❌ Erreur mise à jour base de données : {e}")

def handle_refund_failed(user_admin, data_object, webhook_event):
    """
    ❌ Traitement quand un remboursement échoue
    Événement critique - nécessite une action manuelle
    """
    _webhook_status_update(
            webhook_event, 
            is_fully_completed=False,
            message=f"🔄 Traitement quand un remboursement est effectué - VERSION UNIFIÉE, non encore traité"
        )
    return HttpResponse(status=200)

def notify_refund_failure(refund):
    """
    🔔 Notifier l'équipe d'un échec de remboursement
    """
    try:
        # Informations critiques
        failure_reason = refund.get('failure_reason', 'Raison inconnue')
        charge_id = refund.get('charge', 'Inconnue')
        amount = refund['amount'] / 100
        currency = refund['currency']
        
        # Message d'alerte
        alert_message = f"""
        🚨 REMBOURSEMENT ÉCHOUÉ - ACTION REQUISE 🚨
        
        DÉTAILS :
        - ID Remboursement : {refund['id']}
        - Montant : {amount:.2f} {currency}
        - Charge associée : {charge_id}
        - Raison de l'échec : {failure_reason}
        - Date : {timezone.now().strftime('%Y-%m-%d %H:%M')}
        
        ACTIONS REQUISES :
        1. Vérifier le statut du compte bancaire du client
        2. Contacter le client si nécessaire
        3. Tenter un nouveau remboursement manuellement
        4. Documenter l'incident
        
        Lien Stripe : https://dashboard.stripe.com/refunds/{refund['id']}
        """
        
        logger.critical(alert_message)
        
        # 🔔 Envoyer une notification à l'équipe
        # send_alert_to_team(
        #     subject="🚨 Remboursement échoué - Action requise",
        #     message=alert_message,
        #     priority="high"
        # )
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la notification d'échec de remboursement : {e}")

def update_refund_status_in_database(refund_id, status, failure_reason=None):
    """
    📝 Mettre à jour le statut du remboursement en base de données
    """
    try:
        # Exemple si vous avez un modèle Refund
        # refund = Refund.objects.get(stripe_refund_id=refund_id)
        # refund.status = status
        # refund.failure_reason = failure_reason
        # refund.failed_at = timezone.now() if status == 'failed' else None
        # refund.save()
        
        logger.info(f"📝 Remboursement {refund_id} marqué comme échoué : {failure_reason}")
        
    except Exception as e:
        logger.error(f"❌ Erreur mise à jour statut remboursement {refund_id} : {e}")
        




# def handle_balance_available(user_admin, data_object, webhook_event):
#     """
#     💰 Gestion de l'événement Stripe `balance.available`

#     Ce webhook est déclenché lorsque des fonds deviennent disponibles sur le compte Stripe
#     (en général 2-7 jours après une charge réussie).

#     ⚡ Objectif :
#     - Identifier les transactions internes (BalanceTransaction) encore marquées comme non disponibles
#     - Vérifier leur statut réel chez Stripe
#     - Effectuer le settlement métier (finaliser paiement, transfert ou remboursement)
#     - Marquer les transactions comme disponibles
#     - Assurer l'idempotence et la cohérence comptable
#     """

#     # ---------------------------------------------------
#     # 🔔 Signal reçu
#     # ---------------------------------------------------
#     append_webhook_log(
#         webhook_event,
#         "📩 balance.available reçu — déclenchement de la vérification des transactions pending"
#     )

#     # ---------------------------------------------------
#     # 🔁 Étape 2 — Sélection des transactions internes
#     # ---------------------------------------------------
#     # Récupère toutes les BalanceTransaction encore non finalisées
#     # - is_available=False : fonds pas encore marqués disponibles
#     # - status="pending" : statut Stripe connu au moment de charge.succeeded
#     # select_for_update() : verrou DB pour éviter les conflits en cas de webhooks concurrents
#     pending_balances = (
#         BalanceTransaction.objects
#         .select_for_update()
#         .filter(
#             is_available=False,
#             status="pending"
#         )
#     )

#     # ---------------------------------------------------
#     # 💤 Aucun travail à faire
#     # ---------------------------------------------------
#     if not pending_balances.exists():
#         append_webhook_log(
#             webhook_event,
#             "ℹ️ Aucune BalanceTransaction pending à vérifier"
#         )
#         _webhook_status_update(webhook_event, True, "Rien à traiter (idempotent)")
#         return HttpResponse(status=200)

#     # ---------------------------------------------------
#     # 🔁 Étape 4 — Boucle principale : vérification et settlement
#     # ---------------------------------------------------
#     append_webhook_log(
#         webhook_event,
#         f"📊 Vérification de {pending_balances.count()} BalanceTransaction(s) pending"
#     )

#     # Transaction atomique : rollback si une erreur survient
#     with transaction.atomic():
#         for bal in pending_balances:

#             append_webhook_log(
#                 webhook_event,
#                 f"🔍 Vérification Stripe balance_txn_id={bal.balance_txn_id}"
#             )

#             # ---------------------------------------------------
#             # 🌐 Vérification du statut réel chez Stripe
#             # ---------------------------------------------------
#             # On recharge la transaction via l'API Stripe pour vérifier si elle est maintenant disponible
#             stripe_txn = stripe.BalanceTransaction.retrieve(
#                 bal.balance_txn_id
#             )

#             # ⏳ Si elle n'est pas encore disponible, on ignore pour l'instant
#             if stripe_txn.status != "available":
#                 append_webhook_log(
#                     webhook_event,
#                     f"⏳ Toujours pending chez Stripe"
#                 )
#                 continue

#             # ---------------------------------------------------
#             # 💼 Settlement métier
#             # ---------------------------------------------------
#             # Ici l'argent est effectivement disponible
#             # On applique la logique métier selon le type de transaction
#             try:
#                 if bal.event_type == "charge":
#                     # Paiement client → finaliser facture, cours, horaires, etc.
#                     handle_payment_settlement(bal)
#                 elif bal.event_type == 'transfer':
#                     # Transfert vers compte connecté
#                     handle_transfer_settlement(bal)
#                 elif bal.event_type == 'refund':
#                     # Remboursement confirmé
#                     handle_refund_settlement(bal)
#                 # elif bal.event_type == 'dispute':
#                 #     handle_dispute_settlement(bal)
#                 # elif bal.event_type == 'adjustment':
#                 #     handle_adjustment_settlement(bal)

#                 # ---------------------------------------------------
#                 # ✅ Marquage interne : transaction finalisée
#                 # ---------------------------------------------------
#                 bal.status = "available"
#                 bal.is_available = True
#                 bal.available_on = timezone.now()
#                 bal.save(update_fields=[
#                     "status",
#                     "is_available",
#                     "available_on",
#                     "updated_at"
#                 ])

#                 append_webhook_log(
#                     webhook_event,
#                     f"✅ BalanceTransaction {bal.balance_txn_id} finalisée"
#                 )

#             # ---------------------------------------------------
#             # 💥 Gestion des erreurs critiques
#             # ---------------------------------------------------
#             # Une erreur stoppe tout le batch et rollback la transaction
#             except Exception as e:
#                 append_webhook_log(
#                     webhook_event,
#                     f"💥 Erreur settlement {bal.balance_txn_id} : {str(e)}"
#                 )
#                 raise  # rollback transaction.atomic()7

def handle_balance_available(user_admin, data_object, webhook_event):
    """
    💰 Gestion de l'événement Stripe `balance.available`
    """

    append_webhook_log(
        webhook_event,
        "📩 balance.available reçu — déclenchement de la vérification des transactions pending"
    )

    # ---------------------------------------------------
    # 🔁 Transaction atomique OBLIGATOIRE pour select_for_update
    # ---------------------------------------------------
    with transaction.atomic():

        # ---------------------------------------------------
        # 🔁 Sélection des transactions internes pending
        # ---------------------------------------------------
        #     # Récupère toutes les BalanceTransaction encore non finalisées
        # - is_available=False : fonds pas encore marqués disponibles
        # - status="pending" : statut Stripe connu au moment de charge.succeeded
        # select_for_update() : verrou DB pour éviter les conflits en cas de webhooks concurrents
        # select_for_update() doit être utilisé dans transaction si non => erreur
        pending_balances = (
            BalanceTransaction.objects
            .select_for_update()
            .filter(
                is_available=False,
                status="pending"
            )
        )

        # ---------------------------------------------------
        # 💤 Aucun travail à faire
        # ---------------------------------------------------
        if not pending_balances.exists():
            append_webhook_log(
                webhook_event,
                "ℹ️ Aucune BalanceTransaction pending à vérifier"
            )
            _webhook_status_update(webhook_event, True, "Rien à traiter (idempotent)")
            return HttpResponse(status=200)

        append_webhook_log(
            webhook_event,
            f"📊 Vérification de {pending_balances.count()} BalanceTransaction(s) pending"
        )

        # ---------------------------------------------------
        # 🔁 Boucle principale : vérification et settlement
        # ---------------------------------------------------
        for bal in pending_balances:

            append_webhook_log(
                webhook_event,
                f"🔍 Vérification Stripe balance_txn_id={bal.balance_txn_id}"
            )

            stripe_txn = stripe.BalanceTransaction.retrieve(
                bal.balance_txn_id
            )

            # ⏳ Toujours pending chez Stripe
            if stripe_txn.status != "available":
                append_webhook_log(
                    webhook_event,
                    "⏳ Toujours pending chez Stripe"
                )
                continue

            try:
                # --------------------------------------------
                # 💼 Settlement métier
                # --------------------------------------------
                if bal.event_type == "charge":
                    handle_payment_settlement(bal)
                elif bal.event_type == "transfer":
                    handle_transfer_settlement(bal)
                elif bal.event_type == "refund":
                    handle_refund_settlement(bal)
                # elif bal.event_type == 'dispute':
                #     handle_dispute_settlement(bal)
                # elif bal.event_type == 'adjustment':
                #     handle_adjustment_settlement(bal)
                # --------------------------------------------
                # ✅ Finalisation interne
                # --------------------------------------------
                bal.status = "available"
                bal.is_available = True
                bal.available_on = timezone.now()
                bal.save(update_fields=[
                    "status",
                    "is_available",
                    "available_on",
                    "updated_at"
                ])

                append_webhook_log(
                    webhook_event,
                    f"✅ BalanceTransaction {bal.balance_txn_id} finalisée"
                )

            except Exception as e:
                append_webhook_log(
                    webhook_event,
                    f"💥 Erreur settlement {bal.balance_txn_id} : {str(e)}"
                )
                raise  # rollback complet




@transaction.atomic
def handle_payment_settlement(bal):
    """
    💳 Finalisation MÉTIER d’un paiement APRÈS confirmation Stripe

    Cette fonction est appelée UNIQUEMENT lorsque :
    - balance.available a confirmé que l'argent est réellement encaissé

    Garanties :
    - idempotence
    - cohérence comptable
    - rollback automatique en cas d’erreur
    """

    # ---------------------------------------------------
    # 🔎 Récupération du webhook associé (si existant)
    # ---------------------------------------------------
    webhook_event = WebhookEvent.objects.filter(
        event_id=bal.balance_txn_id
    ).first()

    if webhook_event:
        append_webhook_log(
            webhook_event,
            f"🔁 Début settlement paiement pour balance_txn_id={bal.balance_txn_id}"
        )

    # ---------------------------------------------------
    # 🛑 Idempotence : settlement déjà effectué
    # ---------------------------------------------------
    if bal.is_settled:
        if webhook_event:
            _webhook_status_update(
                webhook_event,
                is_fully_completed=True,
                message="✅ Settlement déjà effectué (idempotent)"
            )
        return

    # ---------------------------------------------------
    # 📄 Récupération de la facture liée
    # ---------------------------------------------------
    invoice = (
        Invoice.objects
        .select_for_update()
        .filter(balance_txn_id=bal.balance_txn_id)
        .first()
    )

    if not invoice:
        if webhook_event:
            append_webhook_log(
                webhook_event,
                "💥 Invoice introuvable pour cette BalanceTransaction"
            )
        raise Exception("Invoice introuvable pour cette BalanceTransaction")

    # ---------------------------------------------------
    # 💳 Création / mise à jour du paiement interne
    # ---------------------------------------------------
    payment, created = Payment.objects.update_or_create(
        invoice=invoice,
        defaults={
            "status": Payment.APPROVED,
            # ⚠️ supposé en euros (float). Si tu stockes en centimes → enlève /100
            "amount": bal.amount / 100,
            "currency": bal.currency,
            "eleve": invoice.demande_paiement.eleve,
            "professeur": invoice.demande_paiement.user.professeur,
        }
    )

    if webhook_event:
        append_webhook_log(
            webhook_event,
            f"✅ Paiement ID {payment.id} → status APPROVED"
        )

    # ---------------------------------------------------
    # 📄 Mise à jour de la facture
    # ---------------------------------------------------
    invoice.status = Invoice.PAID
    invoice.save(update_fields=["status"])

    if webhook_event:
        append_webhook_log(
            webhook_event,
            f"✅ Facture ID {invoice.id} → status PAID"
        )

    # ---------------------------------------------------
    # 🧾 Mise à jour de la demande de paiement
    # ---------------------------------------------------
    Demande_paiement.objects.filter(
        id=invoice.demande_paiement_id
    ).update(
        statut_demande=Demande_paiement.REALISER
    )

    if webhook_event:
        append_webhook_log(
            webhook_event,
            f"✅ Demande_paiement ID {invoice.demande_paiement_id} → REALISER"
        )

    # ---------------------------------------------------
    # 🕒 Association des horaires au paiement
    # ---------------------------------------------------
    Horaire.objects.filter(
        demande_paiement_id=invoice.demande_paiement_id
    ).update(payment=payment)

    if webhook_event:
        append_webhook_log(
            webhook_event,
            "✅ Horaires liés au paiement"
        )

    # ---------------------------------------------------
    # ✅ Marquage FINAL du settlement
    # ---------------------------------------------------
    bal.is_settled = True
    bal.save(update_fields=["is_settled", "updated_at"])

    if webhook_event:
        _webhook_status_update(
            webhook_event,
            is_fully_completed=True,
            message="✅ Settlement paiement terminé avec succès"
        )



@transaction.atomic
def handle_transfer_settlement(bal):
    """
    📤 Settlement d'un TRANSFER Stripe devenu AVAILABLE

    Ce handler est déclenché depuis `balance.available`
    lorsque Stripe confirme que les fonds transférés
    sont définitivement disponibles.

    🎯 Objectifs :
    - Finaliser la facture de transfert
    - Créer / mettre à jour le modèle Transfer interne
    - Marquer la BalanceTransaction comme settled
    - Garantir l'idempotence
    """

    # ---------------------------------------------------
    # 🔎 Récupération du webhook associé (si existant)
    # ⚠️ NB : event_id != balance_txn_id dans Stripe,
    # mais on conserve ce lien pour le logging interne
    # ---------------------------------------------------
    webhook_event = WebhookEvent.objects.filter(
        event_id=bal.balance_txn_id
    ).first()

    if webhook_event:
        append_webhook_log(
            webhook_event,
            f"🔁 Début settlement TRANSFER pour balance_txn_id={bal.balance_txn_id}"
        )

    # ---------------------------------------------------
    # 🛑 Idempotence — settlement déjà effectué
    # ---------------------------------------------------
    if bal.is_settled:
        if webhook_event:
            _webhook_status_update(
                webhook_event,
                is_fully_completed=True,
                message="✅ Settlement transfer déjà effectué (idempotent)"
            )
        return

    # ---------------------------------------------------
    # 🔒 Verrouillage de la facture de transfert associée
    # ---------------------------------------------------
    invoice_transfert = (
        InvoiceTransfert.objects
        .select_for_update()
        .filter(balance_transaction=bal.balance_txn_id)
        .first()
    )

    if not invoice_transfert:
        if webhook_event:
            append_webhook_log(
                webhook_event,
                "❌ [TRANSFER] InvoiceTransfert introuvable pour cette balance_transaction"
            )
        return

    if webhook_event:
        append_webhook_log(
            webhook_event,
            f"🔒 Facture de transfert verrouillée ID={invoice_transfert.id}"
        )

    # ---------------------------------------------------
    # 💰 Normalisation du montant
    # Stripe retourne souvent les transfers en négatif
    # ---------------------------------------------------
    amount = abs(bal.amount) / 100  # centimes → devise

    # ---------------------------------------------------
    # 📤 Création / mise à jour du Transfer interne
    # ---------------------------------------------------
    transfer, created = Transfer.objects.update_or_create(
        invoice_transfert=invoice_transfert,
        defaults={
            "status": Transfer.APPROVED,
            "amount": amount,
            "currency": bal.currency,
            "user_transfer_to": invoice_transfert.user_professeur,
            "stripe_transfer_id": invoice_transfert.stripe_transfer_id
        }
    )

    if webhook_event:
        append_webhook_log(
            webhook_event,
            f"✅ Transfer {'créé' if created else 'mis à jour'} ID={transfer.id}"
        )

    # ---------------------------------------------------
    # 🧾 Mise à jour de la facture de transfert
    # ⚠️ TRANSFERRED ≠ PAID (attente payout.paid)
    # ---------------------------------------------------
    invoice_transfert.status = InvoiceTransfert.TRANSFERRED
    invoice_transfert.save(update_fields=["status"])

    if webhook_event:
        append_webhook_log(
            webhook_event,
            f"📄 Facture de transfert mise à jour → TRANSFERRED (ID={invoice_transfert.id})"
        )

    # ---------------------------------------------------
    # 🧾 Accord de règlement (si existant)
    # ---------------------------------------------------
    if invoice_transfert.accord_reglement:
        AccordReglement.objects.filter(
            id=invoice_transfert.accord_reglement_id
        ).update(status=AccordReglement.IN_PROGRESS)

        if webhook_event:
            append_webhook_log(
                webhook_event,
                f"🤝 AccordReglement mis à jour ID={invoice_transfert.accord_reglement_id}"
            )

    # ---------------------------------------------------
    # 🔒 Settlement final de la BalanceTransaction
    # ---------------------------------------------------
    bal.is_settled = True
    bal.save(update_fields=["is_settled"])

    if webhook_event:
        _webhook_status_update(
            webhook_event,
            is_fully_completed=True,
            message=(
                "✅ Settlement TRANSFER finalisé | "
                f"invoice_transfert={invoice_transfert.id} | "
                f"transfer={transfer.id} | "
                f"amount={amount} {bal.currency}"
            )
        )
    


@transaction.atomic
def handle_refund_settlement(bal):
    """
    💸 Settlement d'un REFUND Stripe devenu AVAILABLE

    Ce handler est appelé depuis `balance.available`
    lorsque Stripe confirme que le remboursement est
    définitivement pris en compte côté solde.

    🎯 Objectifs :
    - Finaliser le RefundPayment interne
    - Mettre à jour l'AccordRemboursement si tous les refunds sont prêts
    - Garantir l'idempotence et la cohérence comptable
    """

    # ---------------------------------------------------
    # 🔎 Récupération du webhook associé (si existant)
    # ⚠️ event_id != balance_txn_id chez Stripe
    # → utilisé ici uniquement pour le logging interne
    # ---------------------------------------------------
    webhook_event = WebhookEvent.objects.filter(
        event_id=bal.balance_txn_id
    ).first()

    if webhook_event:
        append_webhook_log(
            webhook_event,
            f"🔁 Début settlement REFUND pour balance_txn_id={bal.balance_txn_id}"
        )

    # ---------------------------------------------------
    # 🛑 Idempotence — settlement déjà effectué
    # ---------------------------------------------------
    if bal.is_settled:
        if webhook_event:
            _webhook_status_update(
                webhook_event,
                is_fully_completed=True,
                message="✅ Settlement refund déjà effectué (idempotent)"
            )
        return

    # ---------------------------------------------------
    # 💰 Normalisation du montant
    # Stripe renvoie souvent les refunds en négatif
    # ---------------------------------------------------
    amount = abs(bal.amount) / 100  # centimes → devise

    # ---------------------------------------------------
    # 🔄 Mise à jour du RefundPayment interne
    # ---------------------------------------------------
    refund_payment = RefundPayment.objects.filter(
        balance_txn_id=bal.balance_txn_id
    ).first()

    if not refund_payment:
        if webhook_event:
            append_webhook_log(
                webhook_event,
                "❌ RefundPayment introuvable pour cette balance_transaction"
            )
        return

    refund_payment.montant = amount
    refund_payment.status = RefundPayment.APPROVED
    refund_payment.save(update_fields=["montant", "status"])

    if webhook_event:
        append_webhook_log(
            webhook_event,
            f"✅ RefundPayment ID={refund_payment.id} validé (APPROVED)"
        )

    # ---------------------------------------------------
    # 🔎 Récupération du détail d'accord lié au paiement
    # ---------------------------------------------------
    detail = (
        DetailAccordRemboursement.objects
        .select_related("accord")
        .filter(payment=refund_payment.payment)
        .first()
    )

    # Aucun accord associé → rien à mettre à jour
    if not detail:
        if webhook_event:
            append_webhook_log(
                webhook_event,
                "ℹ️ Aucun DetailAccordRemboursement associé à ce paiement"
            )
        bal.is_settled = True
        bal.save(update_fields=["is_settled"])
        return

    # ---------------------------------------------------
    # 🔗 Lien refund → détail (si pas déjà fait)
    # ---------------------------------------------------
    if detail.refund_payment_id != refund_payment.id:
        detail.refund_payment_id = refund_payment.id
        detail.save(update_fields=["refund_payment_id"])

        if webhook_event:
            append_webhook_log(
                webhook_event,
                f"🔗 DetailAccordRemboursement ID={detail.id} "
                f"lié au RefundPayment ID={refund_payment.id}"
            )

    accord = detail.accord

    # ---------------------------------------------------
    # 🔍 Vérification globale de l'accord
    # Tous les détails ont-ils un refund ?
    # ---------------------------------------------------
    has_pending_refunds = accord.details.filter(
        refund_payment_id__isnull=True
    ).exists()

    # ---------------------------------------------------
    # ✅ Passage de l'accord en IN_PROGRESS
    # (tous les refunds Stripe sont confirmés)
    # ---------------------------------------------------
    if not has_pending_refunds and accord.status != AccordRemboursement.COMPLETED:
        accord.status = AccordRemboursement.IN_PROGRESS
        accord.save(update_fields=["status"])

        if webhook_event:
            append_webhook_log(
                webhook_event,
                f"🤝 AccordRemboursement ID={accord.id} → IN_PROGRESS"
            )

    # ---------------------------------------------------
    # 🔒 Settlement final de la BalanceTransaction
    # ---------------------------------------------------
    bal.is_settled = True
    bal.save(update_fields=["is_settled"])

    if webhook_event:
        _webhook_status_update(
            webhook_event,
            is_fully_completed=True,
            message="✅ Settlement refund achevé avec succès"
        )



from django.db import transaction

# # @transaction.atomic
# # def update_accord_remboursement_after_refund(refund_payment):
# #     """
# #     🔄 Mise à jour d'un AccordRemboursement suite à un refund Stripe

# #     Logique :
# #     - Lier le refund au DetailAccordRemboursement
# #     - Vérifier si tous les détails ont un refund_payment_id
# #     - Passer l'accord en IN_PROGRESS si complet
# #     """

# #     # ---------------------------------------------------
# #     # 🔎 Récupération du détail lié au paiement remboursé
# #     # ---------------------------------------------------
# #     detail = (
# #         DetailAccordRemboursement.objects
# #         .select_related("accord")
# #         .filter(payment=refund_payment.payment)
# #         .first()
# #     )

# #     if not detail:
# #         # Rien à mettre à jour → idempotence
# #         return

# #     # ---------------------------------------------------
# #     # 🔗 Lien refund → détail
# #     # ---------------------------------------------------
# #     if detail.refund_payment_id != refund_payment.id:
# #         detail.refund_payment_id = refund_payment.id
# #         detail.save(update_fields=["refund_payment_id"])

# #     accord = detail.accord

# #     # ---------------------------------------------------
# #     # 🔍 Vérification : reste-t-il des refunds manquants ?
# #     # ---------------------------------------------------
# #     has_pending_refunds = accord.details.filter(
# #         refund_payment_id__isnull=True
# #     ).exists()

# #     # ---------------------------------------------------
# #     # ✅ Tous les refunds sont maintenant liés
# #     # ---------------------------------------------------
# #     if not has_pending_refunds and accord.status != AccordRemboursement.IN_PROGRESS:
# #         accord.status = AccordRemboursement.IN_PROGRESS
# #         accord.save(update_fields=["status"])


# #     if invoice_transfert.accord_reglement:
# #         AccordReglement.objects.filter(
# #             id=invoice_transfert.accord_reglement_id
# #         ).update(status=AccordReglement.IN_PROGRESS)

# #         if webhook_event:
# #             append_webhook_log(
# #                 webhook_event,
# #                 f"🤝 AccordReglement mis à jour ID={invoice_transfert.accord_reglement_id}"
# #             )

#     # ---------------------------------------------------
#     # 🔒 Settlement final de la BalanceTransaction
#     # ---------------------------------------------------
#     bal.is_settled = True
#     bal.save(update_fields=["is_settled"])

#     if webhook_event:
#         _webhook_status_update(
#             webhook_event,
#             is_fully_completed=True,
#             message=(
#                 "✅ Settlement TRANSFER finalisé | "
#                 f"invoice_transfert={invoice_transfert.id} | "
#                 f"transfer={transfer.id} | "
#                 f"amount={amount} {bal.currency}"
#             )
#         )




def analyze_balance_cause(balance): # non utilisé
    """
    🔍 Détermine la cause du balance.available
    """
    # Vérifier les transactions récentes
    recent_txns = stripe.BalanceTransaction.list(limit=10)
    
    for txn in recent_txns:
        if txn.type == 'payment':
            return 'payment_settlement'
        elif txn.type == 'refund':
            return 'refund_adjustment' 
        elif txn.type == 'dispute':
            return 'dispute_settlement'
        elif txn.type == 'transfer':
            return 'transfer_in'
        elif txn.type == 'adjustment':
            return 'stripe_adjustment'
    
    return 'unknown'

# ===================================================================
# 📦 HANDLERS D'ÉVÉNEMENTS FIN
# ===================================================================


def execute_test_webhook_ancien(
    invoice_id=61,
    demande_paiement_id=142,
    amount_total=13650,
    payment_intent_id="pi_test_061",
    event_id="evt_pi_failed_061",
):
    """
    💳 Test local du webhook 'payment_intent.payment_failed'

    Exécution :
        python manage.py shell
        >>> from payment.views import execute_test_webhook
        >>> print(execute_test_webhook())

    Objectif :
        - Simule un événement Stripe 'payment_intent.payment_failed'
        - N’effectue aucun appel Stripe
        - Permet de tester la logique Django locale
    """

    # 1️⃣ Récupération d’un administrateur (pour logs éventuels)
    user_admin = User.objects.filter(is_staff=True).first()

    # 2️⃣ Construction de l’objet Stripe simulé
    data_object = {
        "id": payment_intent_id,
        "object": "payment_intent",
        "amount": amount_total,
        "amount_received": 0,
        "currency": "eur",
        "status": "requires_payment_method",   # 👈 État réel après échec paiement
        "customer": None,
        "livemode": False,
        "description": "Paiement cours particulier",

        # ❌ Détails de l’erreur de paiement
        "last_payment_error": {
            "message": "Votre carte a été refusée.",
            "type": "card_error",
            "code": "card_declined",
            "decline_code": "insufficient_funds",
        },

        # 👍 Métadonnées utilisées dans ton app
        "metadata": {
            "invoice_id": invoice_id,
            "demande_paiement_id": demande_paiement_id,
            "horaire_ids": "12,13,14",
            "prof_id": 12,
            "eleve_id": 5
        },

        # Stripe renvoie un charge mais il peut être null
        "latest_charge": None,
        "payment_method": None,
    }

    # 3️⃣ Création ou récupération de l’événement Webhook
    webhook_event, _ = WebhookEvent.objects.get_or_create(
        event_id=event_id,
    )
    webhook_event.type = "payment_intent.payment_failed"    # 👈 IMPORTANT
    webhook_event.payload = data_object
    webhook_event.save()

    # 4️⃣ Appel du handler logique correspondant
    handle_payment_intent_succeeded(webhook_event, data_object)

    # 5️⃣ Retour du log (ou message par défaut)
    return webhook_event.handle_log or "✅ Test webhook PAYMENT_INTENT.PAYMENT_FAILED exécuté avec succès."


def execute_test_webhook_ancien01(
    invoice_id=62,
    demande_paiement_id=144,
    amount_total=13650,
    payment_intent_id="pi_test_062",
    charge_id="ch_test_062",
    balance_txn_id="txn_test_062",
    event_id="evt_pi_succeeded_062",
):
    """
    🔧 Test local du webhook 'payment_intent.succeeded'
    avec simulation complète :
    - PaymentIntent
    - Charge
    - BalanceTransaction
    Exécution :
        python manage.py shell
        >>> from payment.views import execute_test_webhook
        >>> print(execute_test_webhook())
    """

    user_admin = User.objects.filter(is_staff=True).first()

    # ============================================================
    # 1️⃣ SIMULATION PaymentIntent
    # ============================================================
    data_object = {
        "id": payment_intent_id,
        "object": "payment_intent",
        "amount": amount_total,
        "amount_received": amount_total,
        "currency": "eur",
        "status": "succeeded",

        "metadata": {
            "invoice_id": invoice_id,
            "demande_paiement_id": demande_paiement_id,
            "horaire_ids": "12,13,14",
            "prof_id": 12,
            "eleve_id": 5
        },

        "latest_charge": charge_id,
        "payment_method": "pm_test_123",
    }

    # ============================================================
    # 2️⃣ SIMULATION CHARGE (comme Stripe)
    # ============================================================
    charge = {
        "id": charge_id,
        "object": "charge",
        "amount": amount_total,
        "currency": "eur",
        "payment_method_details": {
            "type": "card",
            "card": {
                "brand": "visa",
                "last4": "4242",
                "country": "FR",
            }
        },
        "balance_transaction": balance_txn_id,
        "description": "Test charge for cours particulier",
        "source": {
            "country": "FR"
        }
    }

    # ============================================================
    # 3️⃣ SIMULATION BALANCE TRANSACTION (comme Stripe)
    # ============================================================
    bal = {
        "id": balance_txn_id,
        "object": "balance_transaction",
        "amount": amount_total,
        "currency": "eur",
        "fee": 450,          # ex: Stripe fee 4.50€
        "net": amount_total - 450,
        "status": "pending",  # Stripe renvoie "pending" avant balance.available
        "available_on": None,

        # détails des frais
        "fee_details": [
            {"type": "stripe_fee", "amount": 350},
            {"type": "tax", "amount": 100},
        ],
    }

    # ============================================================
    # 4️⃣ Créer EVENT webhook
    # ============================================================
    webhook_event, _ = WebhookEvent.objects.get_or_create(
        event_id=event_id,
    )
    webhook_event.type = "payment_intent.succeeded"
    webhook_event.payload = data_object
    webhook_event.save()

    # ============================================================
    # 5️⃣ Appel réel du handler
    # ============================================================
    handle_payment_intent_succeeded(webhook_event, data_object, user_admin, charge, bal)

    return webhook_event.handle_log or "OK"


def execute_test_webhook_ancien_03(
    invoice_id=292,
    demande_paiement_id=346,
    amount_total=2394,
    payment_intent_id="pi_test_292",
    charge_id="ch_test_292",
    balance_txn_id="txn_test_292",
    event_id="evt_charge_succeeded_292",
):
    """
    🔧 Test local du webhook 'charge.succeeded'

    ⚠️ Cette fonction simule :
        - un objet Charge Stripe
        - une BalanceTransaction Stripe

    Exécution :
        python manage.py shell
        >>> from payment.views import execute_test_webhook
        >>> execute_test_webhook()
    """

    # SUPERADMIN
    user_admin = User.objects.filter(is_staff=True).first()

    # ============================================================
    # 1️⃣ SIMULATION DE LA CHARGE (faux JSON Stripe)
    # ============================================================
    data_object = {
        "id": charge_id,
        "object": "charge",
        "amount": amount_total,
        "currency": "eur",

        # ✔️ OBLIGATOIRE pour ton handler
        "payment_intent": payment_intent_id,

        "metadata": {
            "invoice_id": invoice_id
        },

        "payment_method_details": {
            "type": "card",
            "card": {
                "brand": "visa",
                "last4": "4242",
                "country": "FR",
            }
        },

        "balance_transaction": balance_txn_id,

        "description": "Test charge for cours particulier",
        "source": {
            "country": "FR"
        }
    }

    # ============================================================
    # 2️⃣ SIMULATION BALANCE TRANSACTION
    # ============================================================
    bal = {
        "id": balance_txn_id,
        "object": "balance_transaction",
        "amount": amount_total,
        "currency": "eur",
        "fee": 450,  # ex: 4.50€
        "net": amount_total - 450,
        "status": "pending",
        "available_on": None,

        "fee_details": [
            {"type": "stripe_fee", "amount": 350},
            {"type": "tax", "amount": 100},
        ],
    }

    # ============================================================
    # 3️⃣ CRÉATION DE L'ÉVÉNEMENT WEBHOOK
    # ============================================================
    webhook_event, _ = WebhookEvent.objects.get_or_create(
        event_id=event_id,
    )
    webhook_event.type = "charge.succeeded"
    webhook_event.payload = data_object
    webhook_event.save()

    # ============================================================
    # 4️⃣ APPEL DU HANDLER RÉEL
    # ============================================================
    handle_charge_succeeded(
        webhook_event=webhook_event,
        data_object=data_object,
        user_admin=user_admin,
        bal=bal
    )

    return webhook_event.handle_log or "OK"

def execute_test_webhook_ancien_4(
    event_id="evt_test_064",
    payment_intent_id="pi_test_064",
    charge_id="ch_test_064"):
    
    """
    🔧 Test local du webhook 'radar.early_fraud_warning.created'

    ⚠️ Cette fonction simule :
        - un objet Early Fraud Warning Stripe

    Exécution :
        python manage.py shell
        >>> from payment.views import execute_test_webhook
        >>> execute_test_webhook()
    """

    # SUPERADMIN
    user_admin = User.objects.filter(is_staff=True).first()

    # ============================================================
    # 1️⃣ SIMULATION DE L'EARLY FRAUD WARNING (faux JSON Stripe)
    # ============================================================
    data_object = {
        "id": "issfr_1QWm9yK9xxABCDEFzyx321",
        "object": "early_fraud_warning", 
        "charge": charge_id,
        "created": 1731905152,
        "fraud_type": "carding",
        "payment_intent": "pi_test_064",
        "livemode": False
    }

    # Structure complète de l'événement pour le webhook_event
    event_payload = {
        "id": "evt_1QWmA7K9xxABCDEF12345678",
        "object": "event",
        "api_version": "2024-06-20",
        "created": 1731905200,
        "pending_webhooks": 1,
        "request": {},
        "type": "radar.early_fraud_warning.created",
        "data": {
            "object": data_object  # Référence au même objet
        }
    }

    # ============================================================
    # 3️⃣ CRÉATION DE L'ÉVÉNEMENT WEBHOOK
    # ============================================================
    webhook_event, _ = WebhookEvent.objects.get_or_create(
        event_id=event_id,
    )
    webhook_event.type = "radar.early_fraud_warning.created"  # ⚠️ Corrigé le type
    webhook_event.payload = event_payload  # Stocke la structure complète
    webhook_event.save()

    # ============================================================
    # 4️⃣ APPEL DU HANDLER RÉEL
    # ============================================================
    handle_radar_fraud_warning(
        webhook_event=webhook_event,
        data_object=data_object,  # Passe uniquement l'objet early_fraud_warning
        user_admin=user_admin,
    )

    return webhook_event.handle_log or "OK"


def execute_test_webhook(event_id="evt_294-293-292"):
    
    """
    🔧 Test local du webhook 'balance.available'

    ⚠️ Cette fonction simule :
        - un objet qui contient trois balances de type charge de  Stripe

    Exécution :
        python manage.py shell
        >>> from payment.views import execute_test_webhook
        >>> execute_test_webhook()
    """

    # SUPERADMIN
    user_admin = User.objects.filter(is_staff=True).first()
    id_1="ch_test_294"
    amount_1=1800
    payment_intent_1="pi_test_294"
    balance_transaction_1="txn_test_294"
    source_1="ch_test_294"

    id_2="ch_test_293"
    amount_2=2106
    payment_intent_2="pi_test_293"
    balance_transaction_2="txn_test_293"
    source_2="ch_test_293"

    id_3="ch_test_292"
    amount_3=2394
    payment_intent_3="pi_test_292"
    balance_transaction_3="txn_test_292"
    source_3="ch_test_292"

    # ============================================================
    # 1️⃣ SIMULATION DE L'EARLY FRAUD WARNING (faux JSON Stripe)
    # ============================================================
    # Data de chaque balance/charge pour l'évènement principal
    data_type = [
        {
            "id": id_1,
            "object": "charge",
            "amount": 1800,
            "currency": "eur",
            "payment_intent": payment_intent_1,
            "balance_transaction": balance_transaction_1,
        },
        {
            "id": id_2,
            "object": "charge",
            "amount": 2106,
            "currency": "eur",
            "payment_intent": payment_intent_2,
            "balance_transaction": balance_transaction_2,
        },
        {
            "id": id_3,
            "object": "charge",
            "amount": 2394,
            "currency": "eur",
            "payment_intent": payment_intent_3,
            "balance_transaction": "balance_transaction_3",
        },
    ]
    # Data de l'évènement principal pour le type: balance/charge
    data_object = [
        {
            "id":"txn_test_294",
            "amount": amount_1,
            "fee": 100,
            "net":amount_1-100 ,
            "currency": "eur",
            "status": "available",
            "source": source_1,
            "available_on": 1732189200,
            "type": "charge", 
        },
        {
            "id":"txn_66",
            "amount": amount_2,
            "fee": 100,
            "net": amount_2-100,
            "currency": "eur",
            "status": "available",
            "source": source_2,
            "available_on": 1732189200,
            "type": "charge", 
        },
        {
            "id":"txn_69",
            "amount": amount_3,
            "fee": 100,
            "net": amount_3-100,
            "currency": "eur",
            "status": "available",
            "source": source_3,
            "available_on": 1732189200,
            "type": "charge", 
        },

    ]

    # Structure complète de l'événement pour le webhook_event
    event_payload = {
        "id": event_id,
        "object": "event",
        "api_version": "2024-06-20",
        "created": 1731905200,
        "pending_webhooks": 1,
        "request": {},
        "type": "balance.available",
        "data": {
                "object": {
                "object": "balance",
                "available":data_object
                }
            }
        }

    # ============================================================
    # 3️⃣ CRÉATION DE L'ÉVÉNEMENT WEBHOOK
    # ============================================================
    webhook_event, _ = WebhookEvent.objects.get_or_create(
        event_id=event_id,
    )
    webhook_event.type = "balance.available"  # ⚠️ Corrigé le type
    webhook_event.payload = event_payload  # Stocke la structure complète
    webhook_event.save()

    # ============================================================
    # 4️⃣ APPEL DU HANDLER RÉEL
    # ============================================================
    handle_balance_available(
        webhook_event=webhook_event,
        data_object=event_payload['data']['object'],  # Passe uniquement la data  de évènement principal event_payload
        user_admin=user_admin,
        data_type=data_type # Passe uniquement les data des balance/type de l'évènement principal event_payload
        )

    return webhook_event.handle_log or "OK"


def execute_test_webhook_ancien_6():

    """
    🔧 Test local du webhook 'transfer.created',

    ⚠️ Cette fonction simule :
        - un objet Trasfert Stripe
        - une BalanceTransaction Stripe

    Exécution :
        python manage.py shell
        >>> from payment.views import execute_test_webhook
        >>> execute_test_webhook()
    """
    # Paramètres
    transfer_id="tr_04"
    balance_txn_id="txn_tr_04"
    event_id="evt_tr_04"
    webhook_event_type="transfer.created"
    invoice_transfert_id=106
    destination="acct_1S9XQaDJIbL5OpH3"
    amount_total=3600
    available_on=1733798400

    # SUPERADMIN
    user_admin = User.objects.filter(is_staff=True).first()

    # ============================================================
    # 1️⃣ SIMULATION DE LA CHARGE (faux JSON Stripe)
    # ============================================================
    data_object = {
        "id": transfer_id,
        "object": "transfer",
        "amount": amount_total,
        "currency": "eur",
        "balance_transaction": balance_txn_id,
        "destination": destination,

        # ✔️ OBLIGATOIRE pour ton handler
        "metadata": {
            "invoice_transfert_id": invoice_transfert_id,
        },
    }

    # ============================================================
    # 2️⃣ SIMULATION BALANCE TRANSACTION
    # ============================================================
    bal = {
        "id": balance_txn_id,
        "object": "balance_transaction",
        "amount": amount_total,
        "currency": "eur",
        "fee": 450,  # ex: 4.50€
        "net": amount_total - 450,
        "status": "pending",
        "available_on": available_on,

        "fee_details": [
            {"type": "stripe_fee", "amount": 350},
            {"type": "tax", "amount": 100},
        ],
    }

    # ============================================================
    # 3️⃣ CRÉATION DE L'ÉVÉNEMENT WEBHOOK
    # ============================================================
    webhook_event, _ = WebhookEvent.objects.get_or_create(
        event_id=event_id,
    )
    webhook_event.type = webhook_event_type
    webhook_event.payload = data_object
    webhook_event.save()

    # ============================================================
    # 4️⃣ APPEL DU HANDLER RÉEL
    # ============================================================
    handle_transfer_created(
        webhook_event=webhook_event,
        data_object=data_object,
        user_admin=user_admin,
        bal=bal
    )

    return webhook_event.handle_log or "OK"