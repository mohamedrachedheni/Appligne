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
from datetime import date
from accounts.models import Payment, Horaire, Historique_prof, Mes_eleves, Detail_demande_paiement, Email_telecharge , Demande_paiement
from eleves.models import Eleve
from django.contrib import messages
from django.db.models import Sum
from django.core.validators import validate_email, EmailValidator
from django.contrib.auth.decorators import login_required
import stripe
from django.conf import settings

import logging
logger = logging.getLogger(__name__)  # Définit un logger pour ce fichier

import pprint # pour afficher dans cmd  un message formaté (checkout_session)
pp = pprint.PrettyPrinter(indent=2)



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

                email_envoye, email_enregistre = envoie_email(
                    user_id_envoi=request.user.id,
                    user_id_receveur=prof.id,
                    sujet_email=sujet,
                    texte_email=texte
                )

                if not email_envoye:
                    logger.warning("❗L'e-mail de confirmation de paiement n'a pas été envoyé au professeur.")
                if not email_enregistre:
                    logger.warning("❗L'e-mail de confirmation de paiement n'a pas été enregistré.")

                # Envoi d'email d'information à l'admin si le paiement de l'élève est réalisé
                admin = User.objects.filter(is_superuser=True).first()
                if admin:
                    sujet = (
                        f"[ADMIN] Paiement confirmé : {request.user.first_name} {request.user.last_name} "
                        f"a réglé la demande du {demande_paiement.date_creation.strftime('%d/%m/%Y')} "
                        f"d'un montant de {demande_paiement.montant:.2f} €"
                    )
                    texte = (
                        f"Bonjour Administrateur,\n\n"
                        f"L'élève {request.user.first_name} {request.user.last_name} a effectué le paiement de la demande "
                        f"datée du {demande_paiement.date_creation.strftime('%d/%m/%Y')} pour un montant de "
                        f"{demande_paiement.montant:.2f} €.\n\n"
                        f"Professeur concerné : {prof.first_name} {prof.last_name} (ID: {prof.id})\n"
                        f"Élève : {request.user.first_name} {request.user.last_name} (ID: {request.user.id})\n\n"
                        f"Cordialement,\nL’équipe Appligne"
                    )

                    email_envoye_admin, email_enregistre_admin = envoie_email(
                        user_id_envoi=request.user.id,
                        user_id_receveur=admin.id,
                        sujet_email=sujet,
                        texte_email=texte
                    )

                    if not email_envoye_admin:
                        logger.warning("❗L'e-mail de confirmation n'a pas été envoyé à l'admin.")
                    if not email_enregistre_admin:
                        logger.warning("❗L'e-mail de confirmation n'a pas été enregistré pour l'admin.")
                else:
                    logger.warning("❌ Aucun utilisateur admin (is_superuser=True) trouvé pour notification.")

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
    La fonction stripe_webhook permet de recevoir des notifications automatiques de Stripe concernant des événements comme :
        un paiement terminé,
        une facture créée,
        un abonnement mis à jour, etc.
        👉 Dans ce cas précis, elle met à jour la facture (Invoice) quand un paiement est réussi.
    """
    # Récupération du contenu brut
    payload = request.body # payload : contient le corps brut de la requête (les données JSON envoyées par Stripe).
    sig_header = request.META['HTTP_STRIPE_SIGNATURE'] # sig_header : contient l'en-tête spécial envoyé par Stripe, (Stripe-Signature) utilisé pour vérifier que la requête est bien authentique.
    event = None

    try: # Vérification de la signature
        """
        Stripe signe les webhooks pour authentifier la source.
            construct_event(...) :
            vérifie la signature avec ta clé secrète Stripe pour webhooks : STRIPE_WEBHOOK_SECRET
            parse et retourne l'objet event.
        """
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    # Gestion des erreurs possibles :
    except ValueError as e: # Si les données sont invalides (parsing JSON échoue) → 400
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e: # Si la signature est mauvaise (fausse requête) → 400
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed': # Si l’événement est un paiement terminé
        # "Le client a terminé la session de paiement (checkout) avec succès."
        session = event['data']['object'] # Récupération de la session Stripe
        """
        session contient tous les détails du paiement 
        (total, statut, id utilisateur, metadata, etc.).
        C’est ce qu’on avait initialisé au moment de Session.create(...).
        """
        try: # Récupération de la facture liée
            invoice = Invoice.objects.get(id=session.metadata.invoice_id)
            if session.payment_status == 'paid': # Si le paiement est bien effectué
                """
                Si Stripe confirme que le paiement est terminé ('paid'), on :
                    met à jour le statut de la facture dans la base de données,
                    enregistre la date du paiement (paid_at).
                """
                invoice.status = 'paid'
                invoice.paid_at = timezone.now()
                invoice.save()
                
        except Invoice.DoesNotExist: # Si la facture n’est pas trouvée
            """
            Si une erreur survient (facture supprimée, mauvaise donnée, etc.), on ignore l’erreur.
            En production, tu pourrais logger ce cas pour audit/debug.
            """
            pass
    """
    On envoie un code 200 OK à Stripe pour confirmer qu’on a bien traité le webhook.
    Si tu renvoies autre chose (erreur 500 par exemple), Stripe réessaiera plus tard.
    """
    return HttpResponse(status=200)
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


logger = logging.getLogger(__name__)
User = get_user_model()

def envoie_email(user_id_envoi, user_id_receveur, sujet_email, texte_email, reponse_email_id=None):
    """
    Envoie un e-mail entre deux utilisateurs et enregistre l'opération dans Email_telecharge.

    Retourne :
        - email_envoye (bool) : True si l'envoi du mail a réussi
        - email_enregistre (bool) : True si l'enregistrement a réussi
    """
    email_envoye = False
    email_enregistre = False

    # Vérification des utilisateurs
    try:
        user_envoi = User.objects.get(id=user_id_envoi)
        user_receveur = User.objects.get(id=user_id_receveur)
    except User.DoesNotExist as e:
        logger.error(f"❌ Utilisateur introuvable : {e}")
        return email_envoye, email_enregistre

    email_expediteur = user_envoi.email
    email_destinataire = user_receveur.email

    # Validation des e-mails
    try:
        validate_email(email_expediteur)
        validate_email(email_destinataire)
    except ValidationError as e:
        logger.error(f"❌ E-mail invalide : {e}")
        return email_envoye, email_enregistre

    # Envoi de l'e-mail
    try:
        send_mail(
            subject=sujet_email,
            message=texte_email,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email_destinataire],
            fail_silently=False,
        )
        logger.info(f"✅ E-mail envoyé de {email_expediteur} à {email_destinataire}")
        email_envoye = True
    except Exception as e:
        logger.error(f"❌ Échec de l'envoi de l'e-mail : {e}")
        return email_envoye, email_enregistre

    # Enregistrement dans Email_telecharge
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
        logger.info("📩 Enregistrement effectué dans Email_telecharge.")
        email_enregistre = True
    except Exception as e:
        logger.error(f"❌ Échec de l'enregistrement dans Email_telecharge : {e}")

    return email_envoye, email_enregistre
