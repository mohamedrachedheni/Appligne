# payment>views.py

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from cart.models import Cart, CartItem, Invoice
from django.utils import timezone
import math
from django.urls import reverse
import stripe
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from datetime import date, datetime
from accounts.models import Payment, Horaire, Historique_prof, Mes_eleves, Detail_demande_paiement, Email_telecharge , Demande_paiement, Professeur, Transfer, DetailAccordReglement, AccordReglement, WebhookEvent, DetailAccordRemboursement, AccordRemboursement
from eleves.models import Eleve
from django.contrib import messages
from django.db.models import Sum
from django.core.validators import validate_email, EmailValidator
from django.contrib.auth.decorators import login_required
import stripe
from django.conf import settings
from pages.utils import decrypt_id, encrypt_id

import logging
import json 
logger = logging.getLogger('payment.views')  # Définit un logger pour ce fichier

import pprint # pour afficher dans cmd  un message formaté (checkout_session)
pp = pprint.PrettyPrinter(indent=2)

# ----------------------------------------------------------
# Début traitement de paiement par carte bancaire des élèves
# ----------------------------------------------------------

# Parce que stripe.checkout.Session.create(...) (et toute autre requête Stripe) nécessite que la clé API soit configurée avant utilisation.
stripe.api_key = settings.STRIPE_SECRET_KEY # obligatoire si non Stripe ne communique pas

@login_required
def create_checkout_session(request):
    """
    1	Vérifie que l'utilisateur est connecté
    2	Récupère le panier utilisateur
    3	Vérifie que le panier contient des articles
    4	Crée une facture (ou la récupère si elle existe déjà)
    5	Construit les line_items requis par Stripe à partir du contenu du panier
    6	Crée une session de paiement Stripe
    7	Sauvegarde l’ID Stripe dans la facture
    8	Redirige vers la page Stripe pour effectuer le paiement
    """
    # 1. Log de début de traitement
    logger.info(f"[{request.user}] ➤ Début de create_checkout_session")

    # 2. Récupération du panier de l'utilisateur connecté
    cart = get_object_or_404(Cart, user=request.user)
    logger.info(f"[{request.user}] ➤ Cart récupéré avec {cart.items.count()} item(s)")

    # 3. Vérification si le panier est vide
    if not cart.items.exists():
        logger.warning(f"[{request.user}] ➤ Panier vide — redirection vers url: eleve_demande_paiement")
        messages.error(request, "Une erreur est survenue. Merci de réessayer plus tard ou de contacter le support technique.")
        return redirect('eleve_demande_paiement')  # Redirection avec message d'erreur

    try:
        # 4. Création ou récupération d’une facture liée au panier
        # Recherche d'une facture existante
        invoice = Invoice.objects.filter(payment=cart.payment).first()
        if not invoice:
            # Création manuelle (car invoice_number est obligatoire)
            invoice = Invoice.objects.create(
                cart=cart,
                payment=cart.payment,
                user=request.user,
                total=cart.total,
                status='draft',
                invoice_number=Invoice().generate_invoice_number()
            )
            logger.info(f"[{request.user}] ➤ Facture créée avec ID {invoice.id} (total={invoice.total})")
        else:

            invoice.cart = cart
            # invoice.invoice_number = Invoice().generate_invoice_number()
            invoice.user = request.user
            invoice.total = cart.total
            invoice.status = 'draft' # draft : brouillon
            invoice.save()
            logger.info(f"[{request.user}] ➤ Facture existante mise à jour avec le panier ID {cart.id}")


    except Exception as e:
        # 5. Gestion des erreurs de création de facture
        import traceback
        logger.error(f"[{request.user}] ❌ Erreur lors de la création de la facture : {e}")
        logger.error(traceback.format_exc())
        return JsonResponse({'error': "Erreur lors de la création de la facture."})

    # 6. Construction des produits à facturer au format Stripe
    line_items = []
    for item in cart.items.all():
        try:
            produit_nom = item.cours          # Nom du cours
            montant = item.price              # Montant en centimes (Stripe utilise les plus petites unités)
            logger.debug(f"[{request.user}] ➤ Ajout item Stripe: {produit_nom} - {montant} centimes")

            line_items.append({
                'price_data': {
                    'currency': 'eur',  # Monnaie : euro
                    'product_data': {'name': produit_nom},  # Nom du produit affiché sur Stripe
                    'unit_amount': montant,  # Montant unitaire en centimes
                },
                'quantity': 1,  # Quantité unique par cours
            })
        except Exception as e:
            logger.error(f"[{request.user}] ❌ Erreur lors de la construction d’un item Stripe : {e}")

    try:
        # 7. Création de la session de paiement Stripe
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],  # Paiement uniquement par carte
            line_items=line_items,          # Liste des produits à facturer
            mode='payment',                 # Mode de paiement immédiat
            success_url=request.build_absolute_uri(
                reverse('payment:success')
            ) + f"?session_id={{CHECKOUT_SESSION_ID}}",  # Redirection en cas de succès
            cancel_url=request.build_absolute_uri(reverse('payment:cancel')),  # Redirection si annulation
            metadata={  # Données personnalisées (utiles pour retrouver la session côté backend)
                'invoice_id': invoice.id,
                'user_id': request.user.id,
            }
        )
        logger.info(f"[{request.user}] ✅ Session Stripe créée avec ID {checkout_session.id}")

        # 8. Mise à jour de la facture avec l'ID de la session Stripe
        invoice.stripe_id = checkout_session.id
        invoice.save()
        logger.info(f"[{request.user}] ✅ Facture mise à jour avec stripe_id={checkout_session.id}")

        # 9. Redirection de l'utilisateur vers la page de paiement Stripe
        return redirect(checkout_session.url)

    except Exception as e:
        # 10. Gestion des erreurs de création de session Stripe
        logger.error(f"[{request.user}] ❌ Erreur lors de la création de la session Stripe : {e}")
        return JsonResponse({'error': str(e)})


@login_required
def payment_success(request):
    """
    Lorsque Stripe redirige l’utilisateur après un paiement réussi, cette vue :
        Récupère la session Stripe (session_id)
        Identifie la facture (Invoice) liée à cette session
        Vérifie si le paiement est bien confirmé
        Met à jour la facture dans la base de données si elle est payée
        Affiche la page success.html avec ou sans information de facture
        Paiement confirmé : l’élève voit sa facture et un message de succès
        Professeur et admin notifiés
        Base de données et panier nettoyés
    """
    session_id = request.GET.get('session_id') #Récupère la session Stripe (session_id)
    
    if session_id:
        """
        On continue uniquement si on a bien reçu un identifiant de session valide.
        Sinon, on passe directement à l’affichage de la page sans facture.
        """
        try: # Tentative de récupération de la session et de la facture
            session = stripe.checkout.Session.retrieve(session_id) # On récupère les détails de la session Stripe via l’API. Cela contient des informations comme payment_status, metadata, etc.
            # on peut introduire plusieurs teste, 
            # vérifier le user:request.user.id==session.metadata.get('user_id')
            # vérifier le montant
            # Vérifier que metadata et invoice_id existent
            invoice_id = session.metadata.get('invoice_id') if session.metadata else None
            if not invoice_id:
                logger.warning("❌ invoice_id absent dans les metadata Stripe")
                messages.error(request, "Identifiant de facture introuvable.")
                return render(request, 'payment/success.html')

            # Récupérer la facture
            logger.info(f"Traitement du paiement pour la facture {invoice_id}, utilisateur {request.user.id}")
            # À partir de metadata (défini lors de la création de la session Stripe), 
            # on récupère l’id de la facture. On filtre aussi par user=request.user 
            # pour sécurité (un utilisateur ne peut pas accéder à la facture d’un autre).
            # vérifier le user:request.user.id==session.metadata.get('user_id')
            invoice = Invoice.objects.get(id=invoice_id, user=request.user)
            

            """
            Stripe peut retourner différents statuts de paiement : 'paid', 'unpaid', 'no_payment_required', etc.
            On s'assure ici que le paiement est bien effectué.
            """
            if session.payment_status == 'paid':
                # on vérifi si le montant à payer envoyé à Strpe est le même que le montant retourné par Stripe au dix centime près
                amount_stripe = session.amount_total /100
                # payment_id = request.session['payment_id'] # le paiement est déjà créé en statut En attente dans la view: eleve_demande_paiement qui envoie payment_id
                amout_payment = invoice.payment.amount
                logger.info(f"Montant Stripe: {amount_stripe}, Montant Facture: {amout_payment}")
                # amout_payment = int(round(payment.amount*100 ,1))/100
                if not math.isclose(amount_stripe, amout_payment, abs_tol=0.05):
                    messages.error(request, f"Le montant payé avec la passerelle de paiement: {amount_stripe} € est différent du montant déclaré par le professeur {amout_payment} €")
                    logger.warning(f"Le montant payé avec la passerelle de paiement: {amount_stripe} € est différent du montant déclaré par le professeur {amout_payment} €")
                    # Envoyer un message d'allerte à l'administration
                    # de même tester session.metadata.invoice_id
                    # de même tester session.metadata.user_id

                """
                On met à jour le statut de la facture dans la base de données :
                Cela permet ensuite de distinguer les factures réglées des autres.
                """
                
                invoice.paid_at = timezone.now()
                invoice.save()

                cart = Cart.objects.filter(user=request.user).first()
                if cart:
                    cart.items.all().delete()  # Suppression de tous les CartItem liés
                    cart.delete()           # Suppression du Cart



                # màj table payment, màj table demande_paiement, màj table Horaire
                # Historique prof nb d'élèves, nb d'heure payées, 
                # envoyé par la view: eleve_demande_paiement 
                prof_id = request.session.get('prof_id')
                if not prof_id:
                    logger.error("prof_id introuvable dans la session")
                    messages.error(request, "Informations de session manquantes: L'ID du professeur manque")
                    return render(request, 'payment/success.html')
                prof = get_object_or_404(User, id=prof_id)
                demande_paiement_id = request.session.get('demande_paiement_id_decript')
                demande_paiement = get_object_or_404(Demande_paiement, id=demande_paiement_id)
                # Création ou mise à jour de l'enregistrement Payment
                payment, created = Payment.objects.update_or_create(
                    model="demande_paiement",
                    model_id=demande_paiement.id,
                    # à redéfinir tous selon Stripe
                    defaults={
                        'status': 'Approuvé',  # À changer par "Approuvé" après validation
                        'slug': f"Dd{demande_paiement.id}Prof{prof.id}Elv{request.user.id}",  # À supprimer du model Payment
                        'reference': session.payment_intent,  # À adapter selon la passerelle de paiement
                        # 'expiration_date': timezone.now(), # À supprimer du model Payment
                        'amount': round(session.amount_total/100,2),
                        'currency': 'eur', # à modifier (session.curreny)
                        # 'payment_register_data': f"PP_d{demande_paiement.id}", # À supprimer du model Payment
                        'payment_body': session,
                    }
                )
                if created:
                    logger.info(f"✅ Nouveau paiement créé : ID={payment.id}, Montant={payment.amount}")
                else:
                    logger.info(f"♻️ Paiement existant mis à jour : ID={payment.id}, Montant={payment.amount}")

                payment_id =  payment.id

                handle_reglement(request, demande_paiement, prof, request.user, payment_id)
                
                # Envoi d'email d'information au professeur si le paiement est réalisé
                admin = User.objects.filter(is_superuser=True).first()
                sujet = (
                    f"Paiement confirmé : {request.user.first_name} {request.user.last_name} "
                    f"a réglé la demande du {demande_paiement.date_creation.strftime('%d/%m/%Y')} "
                    f"d'un montant de {demande_paiement.montant:.2f} €"
                )
                texte = (
                    f"Bonjour {prof.first_name},\n\n"
                    f"L'élève {request.user.first_name} {request.user.last_name} a effectué le paiement de la demande "
                    f"datée du {demande_paiement.date_creation.strftime('%d/%m/%Y')} pour un montant de "
                    f"{demande_paiement.montant:.2f} €.\n\n"
                    f"Vous pouvez désormais consulter les détails dans votre espace personnel.\n\n"
                    f"Cordialement,\nL’équipe Appligne"
                )

                result = envoie_email_multiple(
                    user_id_envoi=request.user.id,
                    liste_user_id_receveurs=[prof.id, admin.id],
                    sujet_email=sujet,
                    texte_email=texte
                )
                # ✅ Vérification des erreurs correctement
                if result.get("erreurs") and len(result["erreurs"]) > 0:
                    logger.warning(f"❗ Il y a {len(result['erreurs'])} erreur(s)d'e-mail de confirmation du transfert.")

                # vider la session
                request.session.pop('payment_id', None)
                request.session.pop('prof_id', None)
                request.session.pop('demande_paiement_id_decript', None)
                """
                Si tout s’est bien passé :
                    On affiche la page success.html
                    En lui passant l’objet invoice pour afficher les détails (n° de facture, montant, date, etc.)
                """
                # visualiser le contenu de la session Stripe
                print("\n=== Contenu de la session Stripe ===")
                pp.pprint(session)
                logger.info(f"Affichage de la page de succès avec la facture: {invoice}")
                return render(request, 'payment/success.html', {'invoice': invoice, 'total_euro': "{:.2f}".format(invoice.total / 100)})
            
            if session.payment_status != 'paid':
                logger.warning(f"Statut du paiement: {session.payment_status}, attendu 'paid'")
                messages.warning(request, "Paiement non encore confirmé")
                return render(request, 'payment/success.html')
        except (Invoice.DoesNotExist, stripe.error.StripeError) as e:
            logger.exception("Erreur lors du traitement du paiement Stripe")
            messages.error(request, "Une erreur est survenue lors du traitement du paiement. Contactez l’administrateur.")

            """
            Si une erreur survient :
                Invoice.DoesNotExist : la facture n’a pas été trouvée en base
                stripe.error.StripeError : Stripe a renvoyé une erreur
                On ignore l’erreur, et passe à l’affichage simple.
            """
            pass

    logger.info("✅ Redirection vers la page de succès sans facture")
    return render(request, 'payment/success.html')


@login_required
def payment_cancel(request):
    """
    Gère les différents scénarios d'annulation/échec de paiement :
    1. Annulation volontaire par l'utilisateur avant paiement
    2. Échec de paiement (carte refusée, etc.)
    3. Expiration de la session de paiement
    4. Problème technique avec Stripe
    Pour chaque cas, on fournit un message approprié et des actions possibles.
    """
    
    # Passer au traitement des différents cas
    context = {}
    
    try:
        # Récupérer le dernier panier non finalisé de l'utilisateur
        cart = Cart.objects.filter(user=request.user).order_by('-created_at').first()
        
        if cart:
            # Récupérer la facture associée si elle existe
            invoice = Invoice.objects.filter(cart=cart).first()
            
            # Récupérer le paiement associé si il existe
            payment = Payment.objects.filter(id=cart.payment.id).first() if cart.payment else None
            
            # Déterminer le type d'échec
            payment_status = None
            if payment:
                payment_status = payment.status
            
            # Cas 1: Paiement déjà marqué comme annulé/échoué (venant de Stripe) 
            # avant même de recréer un nouveau paiement
            #### Attention: avérifier la logique du teste ####
            if payment_status in ['Annulé', 'Invalide']:
                logger.warning(f"Paiement {payment.reference} déjà marqué comme {payment_status}")
                context.update({
                    'error_type': 'payment_failed',
                    'payment_reference': payment.reference,
                    'amount': payment.amount,
                    'can_retry': True
                })
            
            # Cas 2: Session Stripe expirée ou annulée manuellement
            elif invoice and invoice.stripe_id: # créer avec la view : create_checkout_session
                try:
                    # Vérifier l'état réel chez Stripe
                    session = stripe.checkout.Session.retrieve(
                        invoice.stripe_id,
                        api_key=settings.STRIPE_SECRET_KEY
                    )
                    
                    if session.payment_status == 'unpaid': #  plus tôt: if session.payment_status!='paid'
                        # mettre ajour Payment_status = Invalide
                        context.update({
                            'error_type': 'session_expired' if session.expires_at < timezone.now() else 'user_cancelled', # plus tôt invalide que user_cancelled
                            'invoice_number': invoice.invoice_number,
                            'amount': invoice.total / 100,  # Conversion centimes -> euros
                            'expired_at': session.expires_at,
                            'can_retry': True
                        })
                
                except stripe.error.StripeError as e:
                    logger.error(f"Erreur Stripe lors de la récupération de la session: {str(e)}")
                    context.update({
                        'error_type': 'technical_error',
                        'error_message': "Une erreur technique est survenue avec notre processeur de paiement."
                    })
            
            # Cas 3: Panier sans session Stripe créée (annulation très tôt)
            else:
                context.update({
                    'error_type': 'early_cancellation',
                    'can_retry': True
                })
            
            # Nettoyage des données temporaires
            if cart and not invoice:
                cart.delete()
        
        # Si aucun panier trouvé (arrivée directe sur la page)
        else:
            context.update({
                'error_type': 'direct_access',
                'can_retry': False
            })
    
    except Exception as e:
        logger.error(f"Erreur inattendue dans payment_cancel: {str(e)}")
        context.update({
            'error_type': 'unexpected_error',
            'error_message': "Une erreur inattendue s'est produite."
        })
    
    return render(request, 'payment/cancel.html', context)

######################################
# STRIPE WEBHOOK
######################################

"""
Désactive la protection CSRF (Cross-Site Request Forgery).
Obligatoire ici car Stripe envoie la requête — ce n'est pas un utilisateur connecté à ton site.
Sinon, Django rejetterait la requête avec une erreur 403.

Cette vue est exempte de protection CSRF car Stripe n’envoie pas de token CSRF.
C’est obligatoire pour les webhooks externes.
"""
import json
import logging
import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

# Logger spécifique pour les webhooks Stripe
logger = logging.getLogger('payment.views')

@csrf_exempt
def stripe_webhook(request):
    """
    📡 Réception des webhooks Stripe :
    - Vérifie la signature pour authentifier la source
    - Enregistre l'événement reçu dans WebhookEvent
    - Traite tous les événements importants du flux de paiement
    """
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    event = None

    # --- 1️⃣ Vérification de la signature ---
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        logger.info(f"✅ Webhook Stripe reçu : {event['type']} (id: {event.get('id')})")

    except ValueError:
        logger.error("❌ Erreur parsing JSON du payload Stripe.")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        logger.error("❌ Signature Stripe invalide - webhook refusé.")
        return HttpResponse(status=400)
    except Exception as e:
        logger.exception(f"💥 Erreur inattendue lors de la vérification du webhook : {e}")
        return HttpResponse(status=400)

    # --- 2️⃣ Enregistrer l'événement dans WebhookEvent ---
    try:
        event_id = event.get("id")
        event_type = event.get("type")
        payload_json = json.loads(payload.decode("utf-8"))

        webhook_event, created = WebhookEvent.objects.get_or_create(
            event_id=event_id,
            defaults={
                "type": event_type,
                "payload": payload_json,
            },
        )

        if created:
            logger.info(f"📬 Nouvel événement Stripe enregistré : {event_id} ({event_type})")
        else:
            logger.warning(f"⚠️ Événement Stripe déjà reçu : {event_id}")

    except Exception as e:
        logger.exception(f"💥 Impossible d'enregistrer l'événement Stripe dans WebhookEvent : {e}")

    # --- 3️⃣ Traiter les événements importants ---
    try:
        event_type = event["type"]
        logger.info(f"🔍 Traitement de l'événement : {event_type}")

        # 🔄 FLUX DE PAIEMENT SUCCÈS
        if event_type == "checkout.session.completed":
            handle_checkout_session_completed(event)
        
        elif event_type == "payment_intent.succeeded":
            handle_payment_intent_succeeded(event)
        
        elif event_type == "charge.succeeded":
            handle_charge_succeeded(event)

        # 🔄 FLUX D'ÉCHEC
        elif event_type == "payment_intent.payment_failed":
            handle_payment_intent_failed(event)
        
        elif event_type == "charge.failed":
            handle_charge_failed(event)

        # 🔄 REMBOURSEMENTS
        elif event_type == "charge.refunded":
            handle_charge_refunded(event)
        
        elif event_type == "charge.refund.updated":
            handle_charge_refund_updated(event)

        # 🔄 DISPUTES/RÉCLAMATIONS
        elif event_type == "charge.dispute.created":
            handle_charge_dispute_created(event)
        
        elif event_type == "charge.dispute.closed":
            handle_charge_dispute_closed(event)

        # 🔄 ANNULATIONS
        elif event_type == "checkout.session.expired":
            handle_checkout_session_expired(event)
        
        elif event_type == "payment_intent.canceled":
            handle_payment_intent_canceled(event)

        else:
            logger.info(f"📝 Événement non traité : {event_type}")

    except Exception as e:
        logger.exception(f"💥 Erreur lors du traitement de l'événement {event_type} : {e}")

    # --- ✅ Réponse finale ---
    return HttpResponse(status=200)



# =============================================================================
# HANDLERS POUR CHAQUE TYPE D'ÉVÉNEMENT DE STRIPE WEBHOOK DEBUT
# =============================================================================

def handle_checkout_session_completed(event):
    """Traitement quand une session de checkout est complétée"""
    session = event["data"]["object"]
    logger.info("💳 Session checkout complétée : traitement de la facture...")

    invoice_id = session.get("metadata", {}).get("invoice_id")
    if not invoice_id:
        logger.warning("⚠️ Aucun `invoice_id` trouvé dans metadata de la session.")
        return

    try:
        invoice = Invoice.objects.get(id=invoice_id)
    except Invoice.DoesNotExist:
        logger.error(f"❌ Facture ID={invoice_id} introuvable.")
        return

    payment_status = session.get("payment_status")
    
    if payment_status == "paid":
        invoice.status = "paid"
        invoice.paid_at = timezone.now()
        invoice.stripe_payment_intent_id = session.get("payment_intent")
        invoice.save()
        logger.info(f"✅ Facture ID={invoice.id} mise à jour comme payée.")
        
        # 🔔 Notifier l'utilisateur du succès du paiement
        send_payment_success_notification(invoice)
        
    elif payment_status == "unpaid":
        invoice.status = "failed"
        invoice.save()
        logger.warning(f"⚠️ Paiement échoué pour la facture ID={invoice.id}")
        
    else:
        logger.warning(f"📊 Statut de paiement inattendu : {payment_status} pour la facture ID={invoice.id}")



def handle_payment_intent_failed(event):
    """Traitement quand un payment intent échoue"""
    payment_intent = event["data"]["object"]
    logger.warning(f"❌ Payment Intent échoué : {payment_intent['id']}")
    
    last_error = payment_intent.get('last_payment_error', {})
    logger.error(f"📉 Erreur de paiement : {last_error.get('message', 'Raison inconnue')}")
    
    # Mettre à jour la facture si elle existe
    invoice = Invoice.objects.filter(stripe_payment_intent_id=payment_intent['id']).first()
    if invoice:
        invoice.status = "failed"
        invoice.failure_reason = last_error.get('message', 'Erreur inconnue')
        invoice.save()
        logger.info(f"📉 Facture ID={invoice.id} marquée comme échouée.")


def handle_charge_failed(event):
    """Traitement quand une charge échoue"""
    charge = event["data"]["object"]
    logger.error(f"💥 Charge échouée : {charge['id']} - Raison : {charge.get('failure_message', 'Inconnue')}")




def handle_charge_dispute_created(event):
    """Traitement quand une réclamation (dispute) est créée"""
    dispute = event["data"]["object"]
    logger.warning(f"⚖️ Réclamation créée : {dispute['id']} - Raison : {dispute.get('reason', 'Inconnue')}")
    
    # Mettre à jour la facture
    invoice = Invoice.objects.filter(stripe_payment_intent_id=dispute.get('payment_intent')).first()
    if invoice:
        invoice.status = "disputed"
        invoice.dispute_created_at = timezone.now()
        invoice.save()
        logger.info(f"⚖️ Facture ID={invoice.id} marquée comme contestée.")


def handle_charge_dispute_closed(event):
    """Traitement quand une réclamation est fermée"""
    dispute = event["data"]["object"]
    logger.info(f"🔒 Réclamation fermée : {dispute['id']} - Statut : {dispute['status']}")


def handle_checkout_session_expired(event):
    """Traitement quand une session de checkout expire"""
    session = event["data"]["object"]
    logger.info(f"⏰ Session checkout expirée : {session['id']}")
    
    invoice_id = session.get("metadata", {}).get("invoice_id")
    if invoice_id:
        try:
            invoice = Invoice.objects.get(id=invoice_id)
            invoice.status = "expired"
            invoice.save()
            logger.info(f"⏰ Facture ID={invoice.id} marquée comme expirée.")
        except Invoice.DoesNotExist:
            logger.warning(f"⚠️ Facture ID={invoice_id} introuvable pour session expirée.")


def handle_payment_intent_canceled(event):
    """Traitement quand un payment intent est annulé"""
    payment_intent = event["data"]["object"]
    logger.info(f"🚫 Payment Intent annulé : {payment_intent['id']}")

#***
def handle_charge_refund_updated(event):
    """
    🔄 Traitement quand un remboursement de charge est mis à jour
    """
    charge = event["data"]["object"]
    
    logger.info(
        f"🔄 Mise à jour remboursement charge : {charge['id']} | "
        f"Montant remboursé : {charge.get('amount_refunded', 0)/100:.2f} {charge['currency']} | "
        f"Remboursé : {charge.get('refunded', False)}"
    )
    
    # Vérifier les changements de statut de remboursement
    old_refunded = event.get('data', {}).get('previous_attributes', {}).get('refunded')
    if old_refunded is not None and old_refunded != charge.get('refunded'):
        logger.info(f"🔄 Statut remboursement changé : {old_refunded} → {charge.get('refunded')}")

# *
def handle_charge_refunded(event):
    """Traitement quand un remboursement est effectué"""
    charge = event["data"]["object"]
    logger.info(f"🔄 Remboursement effectué : {charge['id']}")
    
    # Trouver la facture associée
    invoice = Invoice.objects.filter(stripe_payment_intent_id=charge.get('payment_intent')).first()
    if invoice:
        invoice.status = "refunded"
        invoice.refunded_at = timezone.now()
        invoice.save()
        logger.info(f"🔄 Facture ID={invoice.id} marquée comme remboursée.")

# *
def handle_charge_succeeded(event):
    """Traitement quand une charge réussit"""
    charge = event["data"]["object"]
    logger.info(f"💳 Charge réussie : {charge['id']} - Montant : {charge['amount']/100:.2f} {charge['currency']}")

#**
def handle_payment_intent_succeeded(event):
    """Traitement quand un payment intent réussit"""
    payment_intent = event["data"]["object"]
    logger.info(f"💰 Payment Intent réussi : {payment_intent['id']}")
    
    # Mettre à jour la facture si elle existe
    invoice = Invoice.objects.filter(stripe_payment_intent_id=payment_intent['id']).first()
    if invoice:
        invoice.status = "paid"
        invoice.paid_at = timezone.now()
        invoice.save()
        logger.info(f"✅ Facture ID={invoice.id} mise à jour via Payment Intent.")



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

"""
🔒 Résumé des bonnes pratiques mises en place :
Sécurité / Robustesse	✅ Mise en œuvre
Vérification de la signature	construct_event(...)
Ignorer les webhooks non pertinents	if event['type'] == ...
Recherche sécurisée d’objets	try/except Invoice.DoesNotExist
Protection CSRF désactivée (justifiée) @csrf_exempt
💡 Suggestions d'amélioration :
Logger les erreurs :
Ajouter d'autres types de webhooks si besoin : elif event['type'] == 'invoice.payment_failed':
Créer une vue de log webhook pour tester les notifications Stripe dans Django admin.(Simuler un webhook Stripe en local pour tester )
Envoyer un e-mail de confirmation à l’utilisateur après paiement.
"""
# =============================================================================
# HANDLERS POUR CHAQUE TYPE D'ÉVÉNEMENT DE STRIPE WEBHOOK FIN
# =============================================================================





# payment>views.py
from django.http import FileResponse
from django.http import Http404
import os

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
"""
✅ Sécurité assurée par :
Élément	Rôle
@login_required	Empêche l’accès aux utilisateurs non connectés
get_object_or_404(..., user=request.user)	Empêche d’accéder à une facture qui ne t’appartient pas
Vérification os.path.exists	Évite l’erreur si le fichier PDF n’existe plus
"""

def handle_reglement(request, demande_paiement, prof, user, payment_id):


    # mise à jour Demande_paiement
    demande_paiement.payment_id = payment_id # le paiement est réalisé
    demande_paiement.statut_demande = "Réaliser" # # à changer par Approuvé
    demande_paiement.save()

    # Mise à jour Horaires, si le paiemnt est invalide horaire.payment_id = None
    horaires = Horaire.objects.filter(demande_paiement_id=demande_paiement.id)
    for horaire in horaires:
        horaire.payment_id = payment_id
        horaire.save()
    
    # mise à jour de l'historique
    update_historique_prof(prof, demande_paiement, user)


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


logger = logging.getLogger('payment.views')
User = get_user_model()

from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.conf import settings
from datetime import date
import logging

logger = logging.getLogger('payment.views')

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






# ------------------------------------------------------
# Début traitement de compte Stripe pour les professeurs
# ------------------------------------------------------

import stripe
import logging
from django.conf import settings
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from accounts.models import Professeur


logger = logging.getLogger('payment.views')
stripe.api_key = settings.STRIPE_SECRET_KEY

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







##############################################
# STRIPE WEBHOOK TRANSFERT
##############################################

import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from decimal import Decimal
import json

from cart.models import CartTransfert, CartTransfertItem, InvoiceTransfert
from cart.models import Cart, CartItem
from accounts.models import Professeur, Payment

stripe.api_key = settings.STRIPE_SECRET_KEY

def is_admin(user):
    return user.is_authenticated and user.is_staff

from datetime import datetime, timezone as dt_timezone

@login_required
@user_passes_test(is_admin)
def create_transfert_session(request):
    """
    Crée un transfert direct Stripe avec génération de facture détaillée
    """
    try:
        # 1. Vérifications admin
        if not request.user.is_staff:
            return JsonResponse({'error': 'Accès non autorisé'}, status=403)

        # 2. Récupérer le panier de transfert
        try:
            cart = CartTransfert.objects.get(user_admin=request.user)
        except CartTransfert.DoesNotExist:
            return JsonResponse({'error': 'Panier de transfert non trouvé'}, status=404)

        if not cart.items.exists():
            return JsonResponse({'error': 'Le panier de transfert est vide'}, status=400)

        # 3. Récupérer le professeur le teste sur le professeur est déjà fait dans la view admin_reglement_detaille
        user_professeur = cart.user_professeur
        professeur = get_object_or_404(Professeur, user=user_professeur)

        # 4. Créer la facture
        invoice_transfert = InvoiceTransfert.objects.create(
            user_admin=request.user,
            user_professeur=professeur.user,
            status='draft',
            total=cart.total/100,
            payment=cart.payment,
        )
        
        # 5. Effectuer le transfert Stripe
        try:
            transfert = stripe.Transfer.create(
                amount=cart.total,  # Montant brut à transférer
                currency="eur",
                destination=professeur.stripe_account_id,
                description=f"Transfert pour {professeur.user.get_full_name()} - Facture {invoice_transfert.invoice_number}",
                metadata={
                    'invoice_transfert_id': invoice_transfert.id,
                    'professeur_id': professeur.id,
                    'cart_transfert_id': cart.id, # c'est vérifié
                    'type': 'transfert_direct_professeur'
                }
            )
            

            # ✅ 6bis. Récupérer les détails complets du balance_transaction lié
            balance_tx = stripe.BalanceTransaction.retrieve(transfert.balance_transaction)
            if balance_tx:
                montant_net_reel = balance_tx['net'] / 100  # Montant net réel (euros)
                frais_stripe = balance_tx['fee'] / 100      # Frais Stripe (euros)
                # date_mise_en_valeur = datetime.fromtimestamp(balance_tx['available_on'], tz=dt_timezone.utc)
                timestamp = balance_tx['available_on']
                if timestamp is not None:
                    date_mise_en_valeur = datetime.fromtimestamp(timestamp, tz=dt_timezone.utc)
                else:
                    date_mise_en_valeur = None
                # date_creation_tx = datetime.fromtimestamp(balance_tx['created'], tz=dt_timezone.utc)

                # print("📊 Détails transfert Stripe :")
                # print("### ### balance_tx :", balance_tx)
                # print("Montant net transféré :", montant_net_reel, "€")
                # print("Frais Stripe :", frais_stripe, "€")
                # print("Date de mise en valeur :", date_mise_en_valeur)
                # print("Date de création transaction :", date_creation_tx)
            else:
                print("détail non disponible #####")

        # Gestion des paramètres GET (retour de Stripe après redirection)
        # 6. GESTION SPÉCIFIQUE DE L'ERREUR "FONDS INSUFFISANTS"
        # Dans create_transfert_session, corriger la ligne de redirection :
        except stripe.error.InvalidRequestError as e:
            if "insufficient available funds" in str(e):
                # Marquer la facture comme en attente, voire les autres modifications à apporter (à revoire si en enregistre Invoice ou pas)
                invoice_transfert.status = 'pending'
                invoice_transfert.save()
                
                # ✅ CORRECTION : Utiliser le bon nom avec le namespace ('payment:insufficient_funds')
                # à vérifier le montant: amount={cart.montant_net/100} ou amount={cart.montant_net}
                return redirect(reverse('payment:insufficient_funds') + f'?invoice_id={invoice_transfert.id}&amount={cart.montant_net/100}')
            else:
                # Relancer les autres types d'erreurs
                raise e
        
        # transfert réussi 

        # 7. Mettre à jour la facture avec les infos Stripe (si transfert réussi)
        invoice_transfert.balance_transaction = transfert.balance_transaction
        invoice_transfert.stripe_transfer_id = transfert.id
        invoice_transfert.status = 'paid' # la confirmation réelle est dans stripe_transfert_webhook ( à changer en production )
        invoice_transfert.paid_at = timezone.now()
        invoice_transfert.total = transfert.amount / 100
        invoice_transfert.frais_stripe = frais_stripe
        invoice_transfert.montant_net_final = montant_net_reel # ou transfert.amount à introduire
        invoice_transfert.date_mise_en_valeur = date_mise_en_valeur
        invoice_transfert.save()

        # créer Transfert

        # Ajouter ou mettre à jour Transfer
        transfer, created = Transfer.objects.get_or_create(
        payment=invoice_transfert.payment,
        stripe_transfer_id=transfert.id,
        user_transfer_to=user_professeur,
        amount=transfert.amount,
        currency = transfert.currency,
        status=Transfer.APPROVED, # en attante de la confirmation du Webhook (à changer en production par status=Transfer.PENDING)
        )

        # 10. Générer le PDF (il faut que l'accé au PDF soit après la confirmation de stripe_transfert_webhook)
        if not invoice_transfert.pdf:
            try:
                invoice_transfert.generate_pdf()
                invoice_transfert.save()
            except Exception as e:
                print(f"Erreur génération PDF: {e}")

        # TODO: Intégrer ici la logique pour mettre à jour 'accord_reglement' si nécessaire

        # 11. Préparer les données pour le template de succès
        request.session['invoice_transfert_id']=invoice_transfert.id 
        request.session['cart_id']=cart.id 
        return redirect('payment:transfert_success')

    # 12. GESTION GÉNÉRIQUE DES ERREURS STRIPE
    except stripe.error.StripeError as e:
        print(f"Erreur Stripe: {e}")
        if 'invoice_transfert' in locals(): # locals() Retourne toutes les variables locales existantes sous forme de dictionnaire.
            invoice_transfert.status = 'failed'# on peut traiter invoice_transfert puis qu'elle existe
        return JsonResponse({'error': f"Erreur Stripe: {str(e)}"}, status=500)
        
    # 13. GESTION DES AUTRES ERREURS (traiter les autres cas selon le dictionnaire Stripe avec GPT)
    except Exception as e:
        print(f"Erreur lors du transfert: {e}")
        import traceback
        print(traceback.format_exc())

        # 🧠 Création d'un journal d'erreur détaillé avec les infos Stripe si disponibles
        error_context = {}

        # 1️⃣ - Ajouter les infos de l'invoice si elle existe
        if 'invoice_transfert' in locals():
            error_context['invoice_id'] = invoice_transfert.id
            error_context['invoice_status'] = invoice_transfert.status

        # 2️⃣ - Ajouter les infos du panier si dispo
        if 'cart' in locals():
            error_context['cart_id'] = cart.id
            error_context['cart_total'] = cart.total / 100

        # 3️⃣ - Ajouter les infos du professeur si dispo
        if 'professeur' in locals():
            error_context['professeur_id'] = professeur.id
            error_context['professeur_stripe'] = professeur.stripe_account_id

        # 4️⃣ - Ajouter les infos du transfert Stripe s’il a été partiellement créé
        if 'transfert' in locals() and transfert is not None:
            error_context.update({
                "stripe_transfer_id": transfert.get('id'),
                "stripe_destination": transfert.get('destination'),
                "stripe_description": transfert.get('description'),
                "stripe_amount": transfert.get('amount'),
                "stripe_currency": transfert.get('currency'),
                "stripe_metadata": transfert.get('metadata'),
                "stripe_balance_tx": transfert.get('balance_transaction'),
                "stripe_reversed": transfert.get('reversed'),
            })

        # 5️⃣ - Marquer la facture comme échouée si elle existe
        if 'invoice_transfert' in locals():
            invoice_transfert.status = 'failed'
            # invoice_transfert.error_message = str(e)[:255]  # tu peux ajouter ce champ dans ton modèle
            invoice_transfert.save()

        # 6️⃣ - Logger proprement pour le debug
        print("📛 CONTEXTE ERREUR TRANSFERT :", json.dumps(error_context, indent=2, default=str))

        # 7️⃣ - Retourner l’erreur JSON détaillée pour l’API admin
        return JsonResponse({
            'error': 'Erreur critique lors du transfert Stripe.',
            'details': error_context,
            'exception': str(e)
        }, status=500)

    




@login_required
@user_passes_test(is_admin)
def transfert_success(request):
    """
    Page de succès après transfert
    """
    # ✅ 1. Récupérer les IDs depuis la session avec sécurité
    invoice_transfert_id = request.session.get('invoice_transfert_id')
    cart_id = request.session.get('cart_id')

    if not invoice_transfert_id or not cart_id:
        messages.error(request, "Impossible d'afficher la page de succès : informations manquantes.")
        return redirect('compte_administrateur')  # 🔁 redirige vers une page par défaut

    # ✅ 2. Récupérer les objets depuis la base
    invoice_transfert = InvoiceTransfert.objects.filter(id=invoice_transfert_id).first()
    cart_transfert = CartTransfert.objects.filter(id=cart_id).first()

    if not invoice_transfert or not cart_transfert:
        messages.error(request, "Données du transfert introuvables.")
        return redirect('compte_administrateur')

    # ✅ 3. Récupérer les items associés
    cart_items = CartTransfertItem.objects.filter(cart_transfert=cart_transfert)

    # ✅ 4. Préparer le contexte pour le template
    context = {
        'invoice': invoice_transfert,
        'items': cart_items,
    }

    return render(request, 'payment/transfert_success.html', context)

# on n'a pas besoin
@login_required
def transfert_cancel(request):# on n'a pas besoin
    """
    Page d'annulation du transfert
    """
    return render(request, 'payment/transfert_cancel.html')



# payment/views.py

import json
import stripe
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings

import json
import logging
import stripe
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

# 📜 Configuration du logger (on recommande de le définir en haut du fichier)
logger = logging.getLogger('payment.views')

@csrf_exempt
def stripe_transfert_webhook(request):
    """
    📡 Webhook Stripe - Gère les événements liés aux transferts et payouts.
    
    - `transfer.created`   : Un transfert vers un compte connecté vient d'être créé
    - `transfer.failed`    : Un transfert a échoué
    - `transfer.reversed`  : Un transfert a été annulé / remboursé
    - `payout.created`     : Un virement bancaire est initié
    - `payout.paid`        : Le virement a été effectué avec succès
    - `payout.failed`      : Le virement a échoué
    """

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET_TRANSFERT

    logger.info("📩 Webhook Stripe reçu sur /stripe_transfert_webhook")

    # 1️⃣ Vérification de la signature Stripe
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        logger.info(f"✅ Signature Stripe vérifiée pour l’événement : {event['id']}")
    except ValueError:
        logger.error("❌ Erreur : Payload JSON invalide")
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        logger.critical("🚨 Signature Stripe invalide - Requête rejetée")
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    except Exception as e:
        logger.exception(f"💥 Erreur inattendue lors de la vérification de signature : {e}")
        return JsonResponse({'error': 'Webhook verification failed'}, status=400)

    event_id = event.get('id')
    event_type = event.get('type')
    data_object = event['data']['object']

    # 2️⃣ Enregistrer l’événement dans WebhookEvent (évite les doublons)
    try:
        payload_json = json.loads(payload.decode('utf-8'))

        webhook_event, created = WebhookEvent.objects.get_or_create(
            event_id=event_id,
            defaults={
                'type': event_type,
                'payload': payload_json,
            }
        )

        if created:
            logger.info(f"📬 Nouvel événement Stripe enregistré : {event_id} ({event_type})")
        else:
            logger.warning(f"⚠️ Événement Stripe déjà reçu : {event_id} ({event_type}) — ignoré pour éviter un traitement en double")
            return HttpResponse(status=200)

    except Exception as e:
        logger.exception(f"💥 Impossible d’enregistrer l’événement Stripe dans WebhookEvent : {e}")
        return JsonResponse({'error': 'Database error'}, status=500)

    # 3️⃣ Dispatcher vers le bon handler
    try:
        logger.info(f"📊 Traitement de l’événement : {event_type}")

        handlers_map = {
            # TRANSFERTS/PAYOUTS
            'transfer.created': handle_transfer_created,
            'transfer.reversed': handle_transfer_reversed,
            'transfer.update': handle_transfer_updated,
            'payout.created': handle_payout_created,
            'payout.paid': handle_payout_paid,
            'payout.failed': handle_payout_failed,
            
            # REMBOURSEMENTS
            'refund.created': handle_refund_created,
            'refund.updated': handle_refund_updated,
            'refund.failed': handle_refund_failed,
            
            
            # ✅ NOUVEAUX HANDLERS AJOUTÉS
            'payment_intent.created': handle_payment_intent_created,
            'charge.updated': handle_charge_updated,
            'balance.available': handle_balance_available,
            
            
            # HANDLERS EXISTANTS (si vous les avez adaptés (à tester))
            'charge.succeeded': handle_charge_succeeded_transfert,  # Version adaptée
            'payment_intent.succeeded': handle_payment_intent_succeeded_transfert,  # Version adaptée
            'charge.refund.updated': handle_charge_refund_updated_transfert,
            'charge.refunded': handle_charge_refunded_transfert, # REMBOURSEMENTS
        }


        handler = handlers_map.get(event_type) # c'est une variable
        if handler:
            handler(data_object) # c'est une fonction
            logger.info(f"✅ Événement {event_type} traité avec succès")
        else:
            logger.info(f"ℹ️ Événement non géré : {event_type}")

    except Exception as e:
        logger.exception(f"💥 Erreur lors du traitement de l’événement {event_type} : {e}")
        return JsonResponse({'error': 'Webhook processing failed'}, status=500)

    # 4️⃣ Réponse finale à Stripe
    logger.info("✅ Webhook Stripe traité avec succès ✅")
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


def handle_payment_intent_succeeded_transfert(payment_intent):
    """
    💰 Traitement quand un payment intent réussit
    Adapté pour stripe_transfert_webhook qui passe data_object directement
    
    Args:
        payment_intent: L'objet payment_intent (déjà event['data']['object'])
    """
    logger.info(f"💰 Payment Intent réussi : {payment_intent['id']}")
    
    # Informations détaillées sur le paiement
    amount = payment_intent.get('amount', 0)
    currency = payment_intent.get('currency', 'eur')
    status = payment_intent.get('status', 'unknown')
    
    logger.info(
        f"💳 Montant : {amount/100:.2f} {currency} | "
        f"Statut : {status} | "
        f"Méthode : {payment_intent.get('payment_method_types', ['unknown'])[0]}"
    )
    
    # Mettre à jour la facture si elle existe
    payment_intent_id = payment_intent['id']
    try:
        invoice = Invoice.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
        if invoice:
            # Vérifier si pas déjà payée pour éviter les doublons
            if invoice.status != "paid":
                invoice.status = "paid"
                invoice.paid_at = timezone.now()
                invoice.save()
                logger.info(f"✅ Facture ID={invoice.id} marquée comme payée via Payment Intent")
            else:
                logger.info(f"ℹ️ Facture ID={invoice.id} déjà marquée comme payée précédemment")
        else:
            logger.warning(f"⚠️ Aucune facture trouvée pour PaymentIntent: {payment_intent_id}")
    except Exception as e:
        logger.error(f"💥 Erreur mise à jour facture: {e}")



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

def handle_payment_intent_created(payment_intent):
    """
    🆕 Traitement quand un Payment Intent est créé
    Adapté pour stripe_transfert_webhook qui passe data_object directement
    
    Args:
        payment_intent: L'objet payment_intent (déjà event['data']['object'])
    """
    logger.info(
        f"🆕 Payment Intent créé : {payment_intent['id']} | "
        f"Montant : {payment_intent['amount']/100:.2f} {payment_intent['currency']} | "
        f"Statut : {payment_intent['status']}"
    )
    
    # Informations supplémentaires
    payment_method_types = payment_intent.get('payment_method_types', [])
    logger.info(
        f"💳 Méthodes de paiement : {', '.join(payment_method_types)} | "
        f"Capture method : {payment_intent.get('capture_method', 'automatic')}"
    )
    
    # Optionnel : Mettre à jour une facture si vous trackez les payment_intents
    invoice_id = payment_intent.get('metadata', {}).get('invoice_id')
    if invoice_id:
        try:
            invoice = Invoice.objects.get(id=invoice_id)
            invoice.stripe_payment_intent_id = payment_intent['id']
            invoice.save()
            logger.info(f"📝 Facture {invoice.id} liée au Payment Intent {payment_intent['id']}")
        except Invoice.DoesNotExist:
            logger.warning(f"⚠️ Facture {invoice_id} introuvable pour Payment Intent {payment_intent['id']}")
        except Exception as e:
            logger.error(f"💥 Erreur liaison facture: {e}")
    
    # Loguer d'autres métadonnées utiles
    metadata = payment_intent.get('metadata', {})
    if metadata:
        logger.info(f"📋 Métadonnées : {metadata}")

        
def handle_charge_updated(charge):
    """
    📝 Traitement quand une charge est mise à jour
    Adapté pour stripe_transfert_webhook qui passe data_object directement
    
    Args:
        charge: L'objet charge (déjà event['data']['object'])
    """
    logger.info(
        f"📝 Charge mise à jour : {charge['id']} | "
        f"Statut : {charge.get('status', 'unknown')} | "
        f"Capturée : {charge.get('captured', False)}"
    )
    
    # ⚠️ Dans stripe_transfert_webhook, on n'a pas previous_attributes
    # On se base uniquement sur l'état actuel pour le logging
    status = charge.get('status')
    captured = charge.get('captured', False)
    
    # Loguer les états importants
    if status == 'succeeded':
        logger.info(f"✅ Charge {charge['id']} réussie")
    elif status == 'failed':
        logger.info(f"❌ Charge {charge['id']} échouée")
        
    # Si la charge est capturée (fonds réellement prélevés)
    if captured:
        logger.info(f"💰 Charge {charge['id']} capturée - Fonds prélevés")
        
        # Mettre à jour la facture associée si nécessaire
        payment_intent_id = charge.get('payment_intent')
        if payment_intent_id:
            try:
                invoice = Invoice.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
                if invoice:
                    # Vérifier si pas déjà capturée pour éviter les doublons
                    if not invoice.captured_at:
                        invoice.captured_at = timezone.now()
                        invoice.save()
                        logger.info(f"✅ Facture {invoice.id} marquée comme capturée")
                    else:
                        logger.info(f"ℹ️ Facture {invoice.id} déjà capturée précédemment")
                else:
                    logger.warning(f"⚠️ Aucune facture trouvée pour PaymentIntent: {payment_intent_id}")
            except Exception as e:
                logger.error(f"💥 Erreur mise à jour facture: {e}")
    
    # Loguer d'autres informations utiles
    if charge.get('refunded'):
        logger.info(f"↩️ Charge {charge['id']} remboursée")
        
    if charge.get('dispute'):
        logger.warning(f"⚖️ Charge {charge['id']} disputée")



def handle_balance_available(balance_transaction):
    """
    🏦 Traitement quand des fonds deviennent disponibles sur le compte Stripe
    Adapté pour stripe_transfert_webhook qui passe data_object directement
    
    Args:
        balance_transaction: L'objet balance (déjà event['data']['object'])
    """
    logger.info(
        f"🏦 Fonds disponibles : {balance_transaction['amount']/100:.2f} {balance_transaction['currency']} | "
        f"Disponible le : {balance_transaction['available_on']} | "
        f"Type : {balance_transaction.get('type', 'unknown')}"
    )
    
    # Convertir la date available_on en datetime
    available_date = timezone.datetime.fromtimestamp(balance_transaction['available_on'], tz=timezone.utc)
    
    # Si c'est lié à une charge spécifique
    if balance_transaction.get('source'):
        source_id = balance_transaction['source']
        
        # Trouver la facture associée via le payment_intent
        if source_id.startswith('ch_'):
            # C'est une charge
            try:
                charge = stripe.Charge.retrieve(source_id)
                payment_intent_id = charge.get('payment_intent')
                if payment_intent_id:
                    invoice = Invoice.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
                    if invoice:
                        invoice.funds_available_date = available_date
                        invoice.save()
                        logger.info(f"📅 Facture {invoice.id} - Fonds disponibles le {available_date.strftime('%Y-%m-%d')}")
                    else:
                        logger.warning(f"⚠️ Aucune facture trouvée pour PaymentIntent: {payment_intent_id}")
            except Exception as e:
                logger.error(f"❌ Erreur récupération charge {source_id} : {e}")
    
    # Loguer d'autres informations utiles
    net_amount = balance_transaction.get('net')
    if net_amount:
        logger.info(f"💰 Montant net : {net_amount/100:.2f} {balance_transaction['currency']}")
    
    fee_amount = balance_transaction.get('fee')
    if fee_amount:
        logger.info(f"💸 Frais Stripe : {fee_amount/100:.2f} {balance_transaction['currency']}")



import logging
from django.utils import timezone


# 📜 Configuration du logger
logger = logging.getLogger('payment.views')

def handle_transfer_created(data_transfer):
    """
    ✅ Gère l'événement Stripe `transfer.created` :
    
    - Récupère les détails du transfert et du `balance_transaction`.
    - Met à jour la facture (`InvoiceTransfert`) liée et le paiement (`Payment`).
    - Crée ou met à jour un `Transfer`.
    - Met à jour l'accord de règlement si applicable.
    - Gère les erreurs de façon robuste et loggée.
    """

    logger.info("📦 [WEBHOOK] Traitement d’un transfert Stripe créé...")

    # --- 1️⃣ Extraire les données principales ---
    transfer_id = data_transfer.get("id")
    balance_tx_id = data_transfer.get("balance_transaction")
    metadata = data_transfer.get("metadata", {})
    invoice_id = metadata.get("invoice_transfert_id")

    if not invoice_id:
        logger.error("❌ Aucun `invoice_transfert_id` trouvé dans les metadata du transfert.")
        return

    logger.info(f"🔗 Transfert Stripe reçu : {transfer_id} lié à la facture ID={invoice_id}")

    montant_net_reel = data_transfer.get("amount", 0) / 100
    frais_stripe = data_transfer.get("net", 0) / 100
    timestamp = data_transfer.get("available_on")
    if timestamp is not None:
        date_mise_en_valeur = datetime.fromtimestamp(timestamp, tz=dt_timezone.utc)
    else:
        date_mise_en_valeur = None

    # --- 2️⃣ Récupérer les détails de la transaction Stripe ---
    try:
        if balance_tx_id:
            balance_tx = stripe.BalanceTransaction.retrieve(balance_tx_id)
            montant_net_reel = balance_tx.get("net", 0) / 100
            frais_stripe = balance_tx.get("fee", 0) / 100
            date_mise_en_valeur = datetime.fromtimestamp(
                balance_tx["available_on"], tz=dt_timezone.utc
            )
            logger.info(f"💶 Détails balance_tx récupérés : net={montant_net_reel}€, frais={frais_stripe}€")
        else:
            logger.warning("⚠️ Aucun `balance_transaction` fourni dans le webhook.")
    except stripe.error.StripeError as e:
        logger.exception(f"💥 Erreur Stripe lors de la récupération du balance_transaction : {e}")
    except Exception as e:
        logger.exception(f"💥 Erreur inattendue lors de la récupération du balance_transaction : {e}")

    # --- 3️⃣ Mettre à jour la facture ---
    try:
        invoice = InvoiceTransfert.objects.get(id=invoice_id)
        invoice.status = "paid" # à modifier en production le status='paid' n'est confirmé que si handle_payout_paid est confirmé
        invoice.paid_at = timezone.now() # à modifier en production n'est confirmé que si handle_payout_paid est confirmé
        invoice.stripe_transfer_id = transfer_id
        invoice.balance_transaction = balance_tx_id
        invoice.frais_stripe = frais_stripe
        invoice.montant_net_final = montant_net_reel # à rectifier si non 'amout' de trensfer
        invoice.date_mise_en_valeur = date_mise_en_valeur
        invoice.save()

        logger.info(f"✅ Facture ID={invoice.id} marquée comme payée.")

    except InvoiceTransfert.DoesNotExist:
        logger.error(f"❌ Aucune facture trouvée avec ID={invoice_id} pour le transfert {transfer_id}.")
        return
    except Exception as e:
        logger.exception(f"💥 Erreur lors de la mise à jour de la facture ID={invoice_id} : {e}")
        return

    # --- 4️⃣ Mettre à jour le paiement lié ---
    try:
        if invoice.payment:
            invoice.payment.status = Payment.APPROVED # à modifier en production le status='paid' n'est confirmé que si handle_payout_paid est confirmé
            invoice.payment.payment_date = invoice.paid_at
            invoice.payment.save()
            logger.info(f"💳 Paiement ID={invoice.payment.id} mis à jour comme APPROVED.")
        else:
            logger.warning(f"⚠️ Aucun paiement lié trouvé pour la facture ID={invoice.id}.")
    except Exception as e:
        logger.exception(f"💥 Erreur lors de la mise à jour du paiement lié : {e}")

    # --- 5️⃣ Créer ou mettre à jour l’objet Transfer ---
    try:
        transfer, created = Transfer.objects.update_or_create(
            stripe_transfer_id=transfer_id,
            user_transfer_to=invoice.payment.professeur.user, # car la conseption du model Transfer peut être pour différent User
            defaults={
                "payment": invoice.payment,
                "amount": montant_net_reel,
                "currency": data_transfer.get("currency", "eur"),
                "status": Transfer.APPROVED, 
                "balance_transaction_id": balance_tx_id,
                "processed_at": timezone.now(),
            },
        )
        logger.info(
            f"{'🆕 Nouveau' if created else '🔄 Transfer mis à jour'} Transfer ID={transfer.stripe_transfer_id}"
        )
    except Exception as e:
        logger.exception(f"💥 Erreur lors de la création ou mise à jour du Transfer : {e}")

    # --- 6️⃣ Générer le PDF de la facture ---
    try:
        if not invoice.pdf:
            invoice.generate_pdf()
            invoice.save()
            logger.info(f"📄 PDF généré pour la facture ID={invoice.id}.")
    except Exception as e:
        logger.exception(f"💥 Erreur lors de la génération du PDF pour la facture ID={invoice.id} : {e}")

    # --- 7️⃣ Mettre à jour l’Accord de règlement si présent ---
    try:
        detail_accord_reglement = DetailAccordReglement.objects.filter(payment=invoice.payment).first()
        if detail_accord_reglement:
            detail_accord_reglement.stripe_transfer_id = transfer.stripe_transfer_id
            detail_accord_reglement.save()

            accord_reglement = detail_accord_reglement.accord
            all_transfers_done = not DetailAccordReglement.objects.filter(
                accord=accord_reglement, stripe_transfer_id__isnull=True
            ).exists()

            accord_reglement.status = (
                AccordReglement.COMPLETED if all_transfers_done else AccordReglement.IN_PROGRESS
            )
            accord_reglement.save()

            logger.info(
                f"📑 AccordReglement ID={accord_reglement.id} mis à jour : "
                f"status={accord_reglement.status}"
            )
        else:
            logger.warning(f"⚠️ Aucun DetailAccordReglement trouvé pour le paiement ID={invoice.payment.id}")
    except Exception as e:
        logger.exception("💥 Erreur lors de la mise à jour de l'accord de règlement.")

    # --- 7️⃣ Envoyer un email au professeur et à l'admine ---
    texte_email = f"""
    Cher Professeur {invoice.user_professeur.get_full_name()},

    Nous avons le plaisir de vous informer qu’un transfert d’un montant de {invoice.total} € a été créé en votre faveur le {invoice.created_at.strftime('%d/%m/%Y') if hasattr(invoice, 'created_at') else '—'}.
    La mise à disposition effective des fonds est prévue pour le {invoice.date_mise_en_valeur.strftime('%d/%m/%Y') if invoice.date_mise_en_valeur else '—'}.

    Une facture détaillée relative à cette opération sera disponible prochainement dans votre espace ProfConnect.

    Nous vous remercions pour votre collaboration et vous souhaitons une excellente continuation.

    Bien cordialement,
    L’équipe ProfConnect
    """

    # ✅ Appel de la fonction d’envoi multiple (IDs uniquement !)
    result = envoie_email_multiple(
        user_id_envoi=invoice.user_admin.id,
        liste_user_id_receveurs=[invoice.user_professeur.id, invoice.user_admin.id],
        sujet_email=f"Un transfert de {invoice.total} € a été créé",
        texte_email=texte_email,
        reponse_email_id=None
    )
    # ✅ Vérification des erreurs correctement
    if result.get("erreurs") and len(result["erreurs"]) > 0:
        logger.warning(f"❗ Il y a {len(result['erreurs'])} erreur(s)d'e-mail de confirmation du transfert.")


def handle_transfer_reversed(transfer):
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
        if invoice.payment:
            invoice.payment.status = Payment.CANCELED
            invoice.payment.save()
            logger.info(f"💳 Paiement lié (ID: {invoice.payment.id}) marqué comme CANCELED.")

    except InvoiceTransfert.DoesNotExist:
        logger.error(f"❌ Facture {invoice_id} introuvable pour transfert reversé {transfer['id']}", exc_info=True)
    except Exception as e:
        logger.exception(f"💥 Erreur inattendue lors du traitement d'un transfert reversé : {e}")


def handle_payout_created(payout):
    """
    💸 Géré lorsque Stripe prépare un virement vers le compte bancaire.
    """
    amount = payout.get('amount', 0) / 100
    currency = payout.get('currency', 'unknown')
    payout_id = payout.get('id')
    logger.info(f"📤 Payout créé : {payout_id} - Montant : {amount} {currency}")


def handle_payout_paid(payout):
    """
    ✅ Géré lorsque Stripe confirme que le virement vers le compte bancaire est effectué.
    """
    payout_id = payout.get('id')
    logger.info(f"🏦 Virement vers le compte bancaire réussi : {payout_id}")


def handle_payout_failed(payout):
    """
    🚫 Géré lorsque le virement bancaire échoue.
    """
    payout_id = payout.get('id')
    failure_reason = payout.get('failure_message', 'Raison non spécifiée')
    logger.error(f"🚫 Virement bancaire échoué : {payout_id} - Raison : {failure_reason}")


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


def handle_refund_created(data):
    """
    🎯 Stripe -> refund.created
    """
    stripe_refund_id = data.get("id")
    status = data.get("status")
    metadata = data.get("metadata", {})
    local_refund_id = metadata.get("local_refund_id")

    logger.info(f"🔔 Refund créé Stripe ID={stripe_refund_id}, local_refund_id={local_refund_id}")

    if not local_refund_id:
        logger.warning(f"⚠ Refund {stripe_refund_id} sans local_refund_id → Ignoré")
        return

    try:
        refund = RefundPayment.objects.get(id=local_refund_id)
        refund.status = status
        refund.stripe_refund_id = stripe_refund_id
        refund.save()

        logger.info(f"✅ Refund local #{refund.id} mis à jour → {status}")

        # 🎯 Auto-check accord
        detail = DetailAccordRemboursement.objects.filter(payment=refund.payment).first()
        if detail:
            check_and_close_accord_if_complete(detail.accord)

    except RefundPayment.DoesNotExist:
        logger.error(f"❌ Refund local ID={local_refund_id} introuvable")


def handle_refund_updated(data):
    """
    🔁 Stripe -> refund.updated (modification de statut après création)
    """
    stripe_refund_id = data.get("id")
    status = data.get("status")

    logger.info(f"🔄 Refund update Stripe ID={stripe_refund_id} -> {status}")

    try:
        refund = RefundPayment.objects.get(stripe_refund_id=stripe_refund_id)
        refund.status = status
        refund.save()

        logger.info(f"✅ Refund #{refund.id} mis à jour → {status}")

        detail = DetailAccordRemboursement.objects.filter(payment=refund.payment).first()
        if detail:
            check_and_close_accord_if_complete(detail.accord)

    except RefundPayment.DoesNotExist:
        logger.warning(f"⚠ Refund Stripe ID={stripe_refund_id} reçu mais pas trouvé en base")

def handle_transfer_updated(data_object):
    """
    🔄 Traitement QUAND UN TRANSFERT EST MIS À JOUR
    Gère TOUS les changements de statut : created, paid, failed, etc.
    """
    transfer = data_object
    
    logger.info(
        f"🔄 Transfert mis à jour : {transfer['id']} | "
        f"Statut : {transfer.get('status', 'unknown')} | "
        f"Montant : {transfer['amount']/100:.2f} {transfer['currency']} | "
        f"Destination : {transfer.get('destination', 'Unknown')}"
    )
    
    # 📊 GESTION DES DIFFÉRENTS STATUTS
    status = transfer.get('status', '')
    
    if status == 'pending':
        logger.info(f"⏳ Transfert {transfer['id']} en attente")
        # Transfert créé mais pas encore traité
        
    elif status == 'in_transit':
        logger.info(f"🚚 Transfert {transfer['id']} en cours de traitement")
        # Fonds en cours d'envoi
        
    elif status == 'paid':
        logger.info(f"💰 Transfert {transfer['id']} PAYÉ avec succès!")
        # FONDS EFFECTIVEMENT ENVOYÉS ✅
        handle_transfer_paid_success(transfer)
        
    elif status == 'failed':
        logger.error(f"❌ Transfert {transfer['id']} ÉCHOUÉ!")
        # Le transfert a échoué
        handle_transfer_failed(transfer)
        
    elif status == 'canceled':
        logger.warning(f"🚫 Transfert {transfer['id']} ANNULÉ")
        # Transfert annulé
        handle_transfer_canceled(transfer)

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

def handle_transfer_failed(transfer):
    """Traitement quand un transfert échoue"""
    logger.error(f"💥 TRANSFERT ÉCHOUÉ: {transfer['id']}")
    
    # Raison possible de l'échec
    failure_message = transfer.get('failure_message', 'Raison inconnue')
    logger.error(f"   📉 Raison: {failure_message}")
    
    # Mettre à jour le statut en base
    update_transfer_status(transfer['id'], 'failed')

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

def handle_refund_failed(data_object):
    """
    ❌ Traitement quand un remboursement échoue
    Événement critique - nécessite une action manuelle
    """
    refund = data_object
    
    logger.error(
        f"❌ REMBOURSEMENT ÉCHOUÉ : {refund['id']} | "
        f"Montant : {refund['amount']/100:.2f} {refund['currency']} | "
        f"Charge : {refund.get('charge', 'Unknown')} | "
        f"Raison : {refund.get('failure_reason', 'Non spécifiée')}"
    )
    
    # 🔥 NOTIFICATION URGENTE
    notify_refund_failure(refund)
    
    # 📝 METTRE À JOUR VOTRE BASE DE DONNÉES
    update_refund_status_in_database(refund['id'], 'failed', refund.get('failure_reason'))

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

# ===================================================================
# 📦 HANDLERS D'ÉVÉNEMENTS FIN
# ===================================================================

from functools import wraps
from django.contrib import messages
import logging

logger = logging.getLogger('payment.views')

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


import stripe
import uuid
from django.views.decorators.http import require_POST
from accounts.models import RefundPayment
from pages.utils import to_cents

stripe.api_key = settings.STRIPE_SECRET_KEY

@require_POST
@secure_stripe_action("refund_payment")  # <<< sécurité globale
def refund_payment(request):
    accord_id = request.session.get('accord_id')
    accord = AccordRemboursement.objects.filter(id=accord_id).first()

    if not accord:
        messages.error(request, "Aucun accord de remboursement trouvé.")
        return redirect('admin_remboursement_detaille')

    details = DetailAccordRemboursement.objects.filter(accord=accord)
    payments = Payment.objects.filter(id__in=details.values_list('payment', flat=True))

    if not payments.exists():
        messages.error(request, "Il n'y a pas de paiement à rembourser.")
        return redirect('admin_remboursement_detaille')

    for payment in payments:
        if payment.status != Payment.APPROVED:
            messages.error(request, "Paiement non remboursable (statut incorrect).")
            return redirect('admin_remboursement_detaille')

    payment_amount_refunds = []

    for detail in details:
        amount_eur = detail.refunded_amount or Decimal('0.00')
        amount_cents = to_cents(amount_eur)
        payment = detail.payment

        if amount_cents <= 0:
            messages.error(request, "Montant invalide.")
            return redirect('admin_remboursement_detaille')

        try:
            charge = None

            # ✅ Si PaymentIntent (référence)
            if payment.reference:
                pi = stripe.PaymentIntent.retrieve(
                    payment.reference,
                    expand=["charges"]
                )

                # Tentative 1: via expand
                if hasattr(pi, "charges") and hasattr(pi.charges, "data") and pi.charges.data:
                    charge = pi.charges.data[0]
                else:
                    # Tentative 2: fallback manuel
                    charge_list = stripe.Charge.list(payment_intent=payment.reference, limit=1)
                    if charge_list.data:
                        charge = charge_list.data[0]

            # ✅ Si Charge directe
            elif payment.stripe_charge_id:
                charge = stripe.Charge.retrieve(payment.stripe_charge_id)

            # ❌ Aucun identifiant Stripe
            else:
                messages.error(request, "Pas d'identifiant Stripe trouvé.")
                return redirect('admin_remboursement_detaille')

            if not charge:
                messages.error(request, "Aucune charge trouvée pour ce paiement.")
                return redirect('admin_remboursement_detaille')

            refundable = charge['amount'] - charge.get('amount_refunded', 0)
            if amount_cents > refundable:
                messages.error(request, "Montant supérieur au montant remboursable.")
                return redirect('admin_remboursement_detaille')

            payment_amount_refunds.append({
                "payment": payment,
                "amount_eur": amount_eur,
                "charge_id": charge['id'],
                "amount_cents": amount_cents,
                "accord": detail.accord
            })

        except stripe.error.StripeError as e:
            messages.error(request, f"Erreur Stripe: {str(e)}")
            return redirect('admin_remboursement_detaille')

    # 🎯 Lancement des remboursements
    for enr in payment_amount_refunds:
        refund_record = RefundPayment.objects.create(
            payment=enr["payment"],
            montant=enr["amount_eur"],
            status=RefundPayment.PENDING,
        )

        idempotency_key = f"refund_payment_{enr['payment'].id}_{enr['amount_cents']}"

        try:
            # ✅ CORRECTION : Utilisation correcte de l'idempotency key
            stripe_refund = stripe.Refund.create(
                charge=enr["charge_id"],
                amount=enr["amount_cents"],
                reason='requested_by_customer',
                metadata={'local_refund_id': refund_record.id},
                idempotency_key=idempotency_key  # ✅ Paramètre direct, pas dans request_options
            )

            refund_record.stripe_refund_id = stripe_refund.id
            refund_record.status = stripe_refund.status
            refund_record.save()
            messages.success(request, f"✅ Remboursement de {enr['amount_eur']}€ initié — Stripe Refund ID : {stripe_refund.id}")
            # mettre à jour accord_rembourcement
            accord=enr["accord"]
            accord.status=AccordReglement.IN_PROGRESS
            accord.save()


        except stripe.error.StripeError as e:
            refund_record.status = RefundPayment.FAILED
            refund_record.save()
            messages.error(request, f"❌ Refund échoué : {str(e)}")

    return redirect('admin_remboursement_detaille')
