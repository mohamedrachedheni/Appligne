from django.shortcuts import render, redirect, get_object_or_404 #dans le cas ou l' id du user ne correspond pas à un user
from django.contrib import messages, auth
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from .models import Eleve, Parent, Temoignage
from accounts.models import Matiere, Niveau, Region, Departement, Email_detaille, Prix_heure, Demande_paiement, Detail_demande_paiement, Payment, Professeur, AccordReglement, AccordRemboursement, Prof_mat_niv
from accounts.models import Demande_paiement, Detail_demande_paiement, Email_telecharge, Payment, Historique_prof, Mes_eleves, Horaire, Detail_demande_paiement, DetailAccordReglement, DetailAccordRemboursement
from pages.models import ReclamationCategorie, PieceJointeReclamation, Reclamation, MessageReclamation
from cart.models import Cart, CartItem
import re


from datetime import date, timedelta, datetime
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.db.models import OuterRef, Subquery, DecimalField, Sum, Q
from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from django.core.validators import validate_email, EmailValidator
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Min, Max
import os
from pages.forms import PieceJointeReclamationForm # c'est un fichier que j'ai créé à l'aide de GPT pour éxécuter les validation du model PieceJointeReclamation
from pages.utils import decrypt_id, encrypt_id
from django.views.decorators.csrf import csrf_protect
from django.conf import settings
from pages.utils import verify_recaptcha
import jwt
import json
import requests
from pages.utils import get_client_ip
import logging
from django.views.decorators.clickjacking import xframe_options_exempt

# Configuration du logger avec le nom du module actuel
logger = logging.getLogger(__name__)

def nouveau_compte_eleve(request):
    # Définir les variables
    is_added = False
    user_nom = ""
    mot_pass = ""
    conf_mot_pass = ""
    prenom = ""
    nom = ""
    email = ""

    
    if request.method == 'POST' and 'btn_enr' in request.POST:
        # definir les variable pour les champs
        user_nom = ""
        mot_pass = ""
        conf_mot_pass = ""
        prenom = ""
        nom = ""
        email = ""
        is_added = True
        
        # get valus from the form
        # si user_nom existe parmis les valeurs retournées par request.POST
        # alors la user_nom prend la valeur retournée user_nom
        # cette erreur peut etre causée en changeant le template en cliquant sur le bouton droit de la souris puis inspecter
        if 'user_nom' in request.POST: 
            user_nom = request.POST['user_nom']
            if not user_nom.strip():
                is_added = False
                messages.error(request, "Le nom de l'utilisateur ne peut pas être vide ou contenir uniquement des espaces.")
        # si non le message d'erreur est envoyé
        else: 
            is_added = False
            messages.error(request, "Erreur liée au nom de l'utilisateur")
        # le paramètre de redirect est url et de render est template
        if 'mot_pass' in request.POST: mot_pass = request.POST['mot_pass']# Vérifier la longueur du mot de passe
        else: 
            is_added = False
            messages.error(request, "Erreur liée au mot de passe")
        if 'conf_mot_pass' in request.POST and mot_pass == request.POST['conf_mot_pass']: conf_mot_pass = request.POST['conf_mot_pass']
        else: 
            is_added = False
            messages.error(request, "Erreur liée à la confirmatio du mot de passe")
            conf_mot_pass = request.POST['conf_mot_pass']
        if 'prenom' in request.POST: prenom = request.POST['prenom'] 
        else: 
            is_added = False
            messages.error(request, "Erreur liée au prénom")
        if 'nom' in request.POST: nom = request.POST['nom']
        else: 
            is_added = False
            messages.error(request, "Erreur liée au nom")
        if 'email' in request.POST: email = request.POST['email']
        else:
            is_added = False 
            messages.error(request, "Erreur liée à l'email")

        if user_nom and mot_pass and conf_mot_pass  and prenom and nom and email :
            if User.objects.filter(username=user_nom).exists():
                is_added = False
                messages.error(request, "Le nom de l'utilisateur est déjà utilisé, donnez un autre nom.")
            else:
                if User.objects.filter(email=email).exists():
                    is_added = False
                    messages.error(request, "L'email est déjà utilisé, donnez un autre email")
                else:
                    if not prenom.strip() or not nom.strip()  or not user_nom.strip():
                        is_added = False
                        messages.error(request, "Le prénom, le nom et le nom de l'utilisateur ne peuvent pas être vide ou contenir uniquement des espaces.")
                    else:
                        if len(mot_pass) < 8:
                            is_added = False
                            messages.error(request, "Le mot de passe doit contenir au moins 8 caractères.")
                        else:
                            # définir un forma pour l'email
                            patt = "^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$"
                            # si le format de l'email est correcte
                            if re.match(patt, email) and is_added :
                                # ajouter le user
                                user = User.objects.create_user(first_name=prenom, last_name=nom, email=email, username=user_nom, password=mot_pass, is_active=True)
                                user.save()
                                # ajouter un élève lié au user
                                eleve = Eleve(user=user)
                                eleve.save()
                                auth.login(request, user)
                                messages.success(request, "Votre identité a été enregistrée avec succès, vous êtes désormais libre de contacter les professeurs de votre préférence.")
                                if not user.is_authenticated: 
                                    messages.error(request, "Vous devez vous connecter à votre compte pour continuer")
                                    return redirect('signin') 
                                # else:
                                #     # messages.success(request, f"Vous êtes actuellement connecté à votre compte nom de l'utilisateur = {request.user.username}")
                                #     messages.success(request, "Votre identité a été enregistrée avec succès, vous êtes désormais libre de contacter les professeurs de votre préférence.")
                                return render(request, 'eleves/compte_eleve.html')
                            else: 
                                is_added = False
                                messages.error(request, "Le format de l'email est incorrecte.")
        else: 
            is_added = False
            messages.error(request, "Les champs obligatoires ne doivent pas être vides")
    # pour conserver les données si il y a erreur
    context={
    'is_added':is_added,
    'user_nom':user_nom,
    'mot_pass':mot_pass,
    'conf_mot_pass':conf_mot_pass,
    'prenom':prenom,
    'nom':nom,
    'email':email
    }
    return render(request, 'eleves/nouveau_compte_eleve.html', context)
    
def compte_eleve(request):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'eleve'):
        messages.error(request, "Vous n'etes pas connecté en tant qu'élève")
        return redirect('signin')
    
    # Effacer tous les paramètres de session sauf l'utilisateur
    keys_to_keep = ['_auth_user_id', '_auth_user_backend', '_auth_user_hash']
    keys_to_delete = [key for key in request.session.keys() if key not in keys_to_keep]
    for key in keys_to_delete:
        del request.session[key]

    return render(request, 'eleves/compte_eleve.html')


def modifier_coordonnee_eleve(request):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'eleve'):
        messages.error(request, "Vous n'etes pas connecté en tant qu'élève")
        return redirect('signin')


    eleve = Eleve.objects.get(user=user)
    #eleve = user.eleve
    first_name = user.first_name
    last_name = user.last_name
    email = user.email
    civilite = eleve.civilite
    #diplome.obtenu = diplome.obtenu.strftime('%d/%m/%Y')
    date_naissance = eleve.date_naissance
    if date_naissance:
        # Conversion de la date de naissance en objet datetime
        date_naissance_formatted = date_naissance.strftime('%d/%m/%Y')
    else: date_naissance_formatted = ""
    numero_telephone = eleve.numero_telephone
    adresse = eleve.adresse
    numero_telephone = eleve.numero_telephone
    date_naissance = eleve.date_naissance
    context={
        'first_name':first_name,
        'last_name':last_name,
        'email':email,
        'civilite':civilite,
        'adresse':adresse,
        'numero_telephone':numero_telephone,
        'date_naissance':date_naissance_formatted,
    }
    if not (request.method == 'POST' and 'btn_enr' in request.POST):
        return render(request, 'eleves/modifier_coordonnee_eleve.html', context)
    else:
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        email = request.POST['email']
        civilite = request.POST['civilite']
        adresse = request.POST['adresse']
        numero_telephone = request.POST['numero_telephone']
        date_naissance = request.POST['date_naissance']
        context={
            'first_name':first_name,
            'last_name':last_name,
            'email':email,
            'civilite':civilite,
            'adresse':adresse,
            'numero_telephone':numero_telephone,
            'date_naissance':date_naissance,
        }

        if User.objects.filter(email=email).exists() and email != user.email:
            messages.error(request, "L'email est déjà utilisé, donnez un autre email")
            return render(request, 'eleves/modifier_coordonnee_eleve.html', context)
        if not first_name.strip() or not last_name.strip():
            messages.error(request, "Le prénom, le nom et le nom de l'utilisateur ne peuvent pas être vide ou contenir uniquement des espaces.")
            return render(request, 'eleves/modifier_coordonnee_eleve.html', context)
        if not re.match(r'^\d{2}/\d{2}/\d{4}$', date_naissance): 
            messages.error(request, "Le format de la date de naissence n'est pas valide. donnez une date sous la forme jj/mm/aaa tel que : 12/06/1990")
            return render(request, 'eleves/modifier_coordonnee_eleve.html', context)
        # définir un forma pour l'email
        patt = "^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$"
        # si le format de l'email est correcte
        if re.match(patt, email):
            # Mettre à jour les données de l'utilisateur et de l'élève
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.save()
            # messages.info(request, f"civilite = {civilite}; email = {email}; adresse = {adresse}; numero_telephone = {numero_telephone}; date_naissance = {date_naissance} ")
            
            eleve.civilite = civilite
            eleve.adresse = adresse
            eleve.numero_telephone = numero_telephone
            eleve.set_date_naissance_from_str(date_naissance)
            eleve.save()
            messages.success(request, "Vos informations ont été mises à jour avec succès.")
            return redirect('compte_eleve')
        messages.error(request, "L'adresse e-mail n'est pas valide.")
    return render(request, 'eleves/modifier_coordonnee_eleve.html', context)



# Formulaire pour les coordonnées du parent
class ParentForm(forms.ModelForm):
    class Meta:
        model = Parent
        fields = ['prenom_parent', 'nom_parent', 'civilite', 'telephone_parent', 'email_parent']
    
    def clean_email_parent(self):
        # Validation personnalisée pour l'adresse e-mail
        email = self.cleaned_data.get('email_parent')
        patt = "^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$"
        if not re.match(patt, email):
            # Si le format de l'email est incorrect, une erreur de validation est levée
            raise forms.ValidationError("L'adresse e-mail n'est pas valide.")
        return email

@login_required  # Assure que l'utilisateur est connecté avant d'accéder à cette vue
def modifier_coordonnee_parent(request):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'eleve'):
        messages.error(request, "Vous n'etes pas connecté en tant qu'élève")
        return redirect('signin')


    try:
        parent = user.parent  # Tente de récupérer l'objet Parent lié à l'utilisateur
    except ObjectDoesNotExist:
        parent = None  # Si l'objet Parent n'existe pas, on initialise à None

    if request.method == 'POST':  # Si la méthode est POST, on traite le formulaire
        form = ParentForm(request.POST, instance=parent)  # Instancie le formulaire avec les données POST et l'instance Parent
        if form.is_valid():  # Vérifie si le formulaire est valide
            if Parent.objects.filter(email_parent=form.cleaned_data['email_parent']).exclude(user=user).exists():
                # Vérifie si l'email est déjà utilisé par un autre utilisateur
                messages.error(request, "L'email est déjà utilisé, donnez un autre email.")
            else:
                form.instance.user = user  # Associe l'utilisateur courant à l'objet Parent
                form.save()  # Sauvegarde l'objet Parent
                messages.success(request, "Les informations du parent ont été mises à jour avec succès.")
                return redirect('compte_eleve')  # Redirige vers la page du compte élève après succès
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")  # Affiche un message d'erreur si le formulaire est invalide
    else:
        form = ParentForm(instance=parent)  # Instancie le formulaire avec l'objet Parent existant pour un GET

    # Contexte à passer au template
    context = {
        'form': form,
        'prenom_parent': form['prenom_parent'].value() if form['prenom_parent'].value() is not None else '',
        'nom_parent': form['nom_parent'].value() if form['nom_parent'].value() is not None else '',
        'civilite': form['civilite'].value() if form['civilite'].value() is not None else '',
        'telephone_parent': form['telephone_parent'].value() if form['telephone_parent'].value() is not None else '',
        'email_parent': form['email_parent'].value() if form['email_parent'].value() is not None else '',
    }
    return render(request, 'eleves/modifier_coordonnee_parent.html', context)  # Affiche le template avec le formulaire



def demande_cours_envoie(request, id_prof):

    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'eleve'):
        messages.error(request, "Vous n'êtes pas connecté en tant qu'élève.<br> Pour contacter un professeur il faut créer un compte élève.")
        return redirect('signin')

    user_prof = get_object_or_404(User, id=id_prof)
    
    
    email_prof = user_prof.email
    nom_prof = user_prof.first_name
    matiere_defaut = request.session.get('matiere_defaut', '[Matière non définie]')
    niveau_defaut = request.session.get('niveau_defaut', '[Niveau scolaire non définie]')
    radio_name = request.session.get('radio_name', '[Format cours non défini]')
    
    nom_eleve = user.first_name + " " + user.last_name
    email_eleve = user.email
    adresse_eleve = user.eleve.adresse
    telephone_eleve = user.eleve.numero_telephone

    if hasattr(user, 'parent'):
        parent = user.parent
        nom_parent = parent.prenom_parent + " " + user.parent.nom_parent
        telephone_parent =parent.telephone_parent
        email_parent =parent.email_parent
    else:
        nom_parent = ""
        telephone_parent = ""
        email_parent = ""

    # Formater le contenu du courriel avec des balises HTML
    formatted_content = f"""
Cher/Chère {nom_prof},
Je suis {nom_parent},
le parent de {nom_eleve}
qui est actuellement en {niveau_defaut}. 
Je me permets de vous contacter pour solliciter votre expertise dans le cadre d'un cours particulier.
Je souhaiterais recevoir des cours dans la matière suivante : {matiere_defaut}, 
sous le format: {radio_name} pendant la période : ...
Voici mes coordonnées :

Téléphone parent : {telephone_parent}
Email parent : {email_parent}
Téléphone élève : {telephone_eleve}
Adresse : {adresse_eleve}
Email : {email_eleve}

Je me tiens à votre disposition pour discuter des détails supplémentaires
et convenir d'une modalité de cours. Dans l'attente de votre réponse que j'espère rapide, 
veuillez confirmer la réception.
Cordialement,
{nom_parent} / {nom_eleve}
"""
    
    context = {
        'formatted_content': formatted_content,
        'id_prof':id_prof
    }
    
    # si non c'est le cas de : (request.method == 'POST' and 'btn_enr' in request.POST)
    if request.method == 'POST' and 'btn_enr' in request.POST:
        text_email = request.POST.get('text_email')
        if text_email:
            user_destinataire = user_prof.id
            
            # traitement de l'envoie de l'email
            # si le sujet de l'email n'est pas défini dans le GET alors sujet='Demande de cours
            sujet = request.POST.get('sujet', '').strip()
            if not sujet: sujet = "Demande de cours"
            destinations = ['prosib25@gmail.com', email_prof]
            # Validation des emails dans destinations
            email_validator = EmailValidator() # Initialiser le validateur d'email
            for destination in destinations:
                try:
                    email_validator(destination)
                except ValidationError:
                    messages.error(request, f"L'adresse email du destinataire {destination} est invalide.<br>Veuillez vérifier l'adresse avec le professeur.")

            # L'envoie de l'email n'est pas obligatoire
            try:
                send_mail(
                    sujet,
                    text_email,
                    email_eleve,
                    destinations,
                    fail_silently=False,
                )
            except Exception as e:
                messages.error(request, f"Une erreur s'est produite lors de l'envoi de l'email: {str(e)}")
            messages.success(request, "L'email a été envoyé avec succès.")
            email_telecharge = Email_telecharge(user=user,
                                                    email_telecharge=email_eleve  , # l'adresse email de l'expéditeur
                                                    sujet=sujet, 
                                                    text_email=text_email, 
                                                    user_destinataire=user_destinataire ) # user.id du destinataire
            email_telecharge.save()
            # Enregistrement dans la table détaille email
            email_detaille = Email_detaille(email=email_telecharge, user_nom=nom_parent + " / " + nom_eleve, matiere=matiere_defaut, niveau=niveau_defaut, format_cours=radio_name )
            email_detaille.save()
            messages.success(request, "Le contenu de l'email est enregistré dans le compte du professeur")

            # Annuler les données précédentes dans la session
            keys_to_clear = [
                'radio_name', 'radio_name_text', 
                'matiere_defaut', 'niveau_defaut', 
                'region_defaut', 'departement_defaut'
            ]
            for key in keys_to_clear:
                request.session.pop(key, None)  # Supprime si existe, sinon rien
            return redirect('compte_eleve')
            
        messages.error(request, "Il faut définir le contenu de l'Email")
    return render(request, 'eleves/demande_cours_envoie.html', context)



def email_recu(request):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'eleve'):
        messages.error(request, "Vous n'etes pas connecté en tant qu'élève")
        return redirect('signin')

    user_id = user.id
    # Fonction interne pour récupérer les emails en fonction des critères de filtrage
    def get_emails(filter_criteria):
        emails = Email_telecharge.objects.filter(user_destinataire=user_id, **filter_criteria).order_by('-date_telechargement')
        if not emails:
            messages.info(request, "Il n'y a pas d'Email correspondant à votre filtre.")
        return emails

    # Filtrage par défaut pour les nouveaux emails (emails avec suivi = null)
    emails = get_emails({'suivi__isnull': True})

    # Vérification du type de requête et application des filtres en fonction du bouton cliqué
    if request.method == 'POST':
        if 'btn_tous' in request.POST:
            # Filtrer pour tous les emails
            emails = get_emails({})
        elif 'btn_nouveau' in request.POST:
            # Filtrer pour les nouveaux emails (suivi = null)
            emails = get_emails({'suivi__isnull': True})
        elif 'btn_attente' in request.POST:
            # Filtrer pour les emails en attente (suivi = 'Réception confirmée')
            emails = get_emails({'suivi': 'Réception confirmée'})
        elif 'btn_repondu' in request.POST:
            # Filtrer pour les emails répondus (suivi = 'Répondu')
            emails = get_emails({'suivi': 'Répondu'})
        elif 'btn_ignore' in request.POST:
            # Filtrer pour les emails ignorés (suivi = 'Mis à côté')
            emails = get_emails({'suivi': 'Mis à côté'})

    # Contexte à passer au template
    context = {
        'emails': emails
    }
    
    # Rendu de la page avec les emails filtrés
    return render(request, 'eleves/email_recu.html', context)



def email_detaille(request, email_id):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user # c'est selui qui va répondre à l'email ( le nouveau expéditeur)
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'eleve') and not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant qu'élève, ni en tant que professeur")
        return redirect('signin')

    email = Email_telecharge.objects.filter(id=email_id).first() # l'email envoyé par le prof et  reçu par l'élève si hasattr(user, 'professeur')
    id_eleve = email.user_destinataire # ID estinataire de l'email
    id_prof = email.user.id # ID expéditeur de l'email
    user = User.objects.filter(id=id_eleve).first() # User qui va répondre à l'email ( c'est le même que user = request.user )
    context={
        'email':email,
        'est_prof': True if hasattr(request.user, 'professeur') else False,
    }
    if 'btn_ignorer' in request.POST:
        # Mettre à jour les champs de l'email reçu
        email.suivi = 'Mis à côté'
        email.date_suivi = date.today()
        email.save() 
        messages.success(request, "L'email est enregistré en tant qu'email ignoré.")
        if hasattr(user, 'eleve'): 
            return redirect('email_recu')
        elif hasattr(user, 'professeur'):
            return redirect('email_recu_prof')
        else: return redirect('index')
    if 'btn_confirmer' in request.POST:
        sujet = "Confirmation de réception"
        text_email =  f"""
J'ai bien reçu votre email
Date de réception:{email.date_telechargement}
Sujet de l'émail: {email.sujet}
Contenu de l'émail:
{email.text_email}
"""
        email_prof = email.user.email # email se l'expéditeur de l'email reçu qu i est le nouveau destinateur de la réponse à envoyer
        email_eleve = user.email # email du nouveau expediteur en réponse à l'email reçu
        eleve_id = user.id
        destinations = ['prosib25@gmail.com', email_prof]
        # Validation des emails dans destinations
        email_validator = EmailValidator() # Initialiser le validateur d'email
        for destination in destinations:
            try:
                email_validator(destination)
            except ValidationError:
                messages.error(request, f"L'adresse email du destinataire {destination} est invalide.<br>Veuillez vérifier l'adresse avec le professeur.")
        try:
            send_mail(
                sujet,
                text_email,
                email_eleve,
                destinations,
                fail_silently=False,
            )  
        except Exception as e:
            messages.error(request, f"Une erreur s'est produite lors de l'envoi de l'email : {str(e)}")

        messages.success(request, "L'email a été envoyé avec succès.")

        email_telecharge = Email_telecharge(user=user, email_telecharge=email_eleve, text_email=text_email, user_destinataire=id_prof, sujet=sujet )
        email_telecharge.save()
        email_reponse_id = email_telecharge.id  # Récupérer l'ID de l'email enregistré  
        # Mettre à jour les champs de l'email envoyé par le prof et  reçu par l'élève
        email.suivi = 'Réception confirmée'
        email.date_suivi = date.today()
        email.reponse_email_id = email_reponse_id
        email.save()
        messages.success(request, "Le contenu de l'email est enregistré")
        if hasattr(user, 'eleve'): 
            return redirect('email_recu')
        elif hasattr(user, 'professeur'):
            return redirect('email_recu_prof')
        else: return redirect('index')
    
    if 'btn_repondre' in request.POST:
        email_eleve = user.email
        sujet = "Suite à votre email"
        text_email =  f"""
Suite à votre email:
Date de réception:{email.date_telechargement}
Sujet de l'émail: {email.sujet}
Contenu de l'émail:
{email.text_email}
"""
        context={
            'text_email':text_email,
            'sujet':sujet, 
            'email_eleve':email_eleve, 
            'email_id': email_id }
        # Stocke les choix de l'élève dans la session
        request.session['text_email'] = text_email
        request.session['sujet'] = sujet
        request.session['email_eleve'] = email_eleve
        request.session['email_id'] = email_id
        return redirect('reponse_email_eleve', email_id=email_id )  # C'est bien fait
    if 'btn_historique' in request.POST:
        if not email.reponse_email_id:
            messages.info(request, "Il n'y a pas de réponse à cet email")
            return render(request, 'eleves/email_detaille.html', context)
        
        email_id = email.reponse_email_id
        # il faut faire une page spéciale pour l'historique de l'émail (def email_detaille(request, email_id):)
        return redirect(reverse('email_detaille', args=[email_id])) # ça marche très bien
    
    if 'btn_ajout_eleve' in request.POST: # bouton ajout élève activé
        return redirect('ajouter_mes_eleve', eleve_id=email.user.id)

    return render(request, 'eleves/email_detaille.html', context)

def reponse_email_eleve(request, email_id): # email_id est envoyé par le template demande_cours_recu_eleve.html
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'eleve') and not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant qu'élève, en tant que professeur")
        return redirect('signin')

    text_email = request.session.get('text_email',None)
    sujet = request.session.get('sujet',None)
    email_eleve = request.session.get('email_eleve',None)
    email_id = request.session.get('email_id',None)
    if not email_id: # donc la réponse est déjà effectuée puisque la session est vide
        messages.error(request, 'La réponse à cet email est déjà effectuée')
        if hasattr(user, 'eleve'): 
            return redirect('email_recu')
        elif hasattr(user, 'professeur'):
            return redirect('email_recu_prof')
        else: return redirect('index')
        
    context={
            'text_email':text_email,
            'sujet':sujet, 
            'email_eleve':email_eleve, 
            'email_id': email_id }
    if request.method == 'POST' and 'btn_enr' in request.POST:
        user = request.user
        email = Email_telecharge.objects.filter(id=email_id).first()
        # messages.success(request, "Teste 03.")
        
        email_eleve = request.POST.get('email_adresse', '').strip()
        if not email_eleve: email_eleve = user.email
         # Validation de l'email
        email_validator = EmailValidator() # Initialiser le validateur d'email
        try:
            email_validator(email_eleve)
        except ValidationError:
            messages.error(request, "L'adresse email de l'envoyeur est invalide.")
            return render(request, 'eleves/reponse_email_eleve.html')

        # si le sujet de l'email n'est pas défini dans le GET alors sujet='Sujet non défini'
        sujet = request.POST.get('sujet', '').strip()  # Obtient la valeur de 'sujet' ou une chaîne vide
        if not sujet:  # Vérifie si sujet est nul ou une chaîne d'espaces après le strip
            sujet = "Suite à votre email"
        email_prof = email.email_telecharge
        text_email =  request.POST['text_email']
        user_destinataire = email.user.id # c'est le user.id du prof qui est l'expéditeur de l'email reçu par l'élève
        destinations = ['prosib25@gmail.com', email_prof]  # Change it to actual destinations
        
        # Validation des emails dans destinations
        email_validator = EmailValidator() # Initialiser le validateur d'email
        for destination in destinations:
            try:
                email_validator(destination)
            except ValidationError:
                messages.error(request, f"L'adresse email du destinataire {destination} est invalide.<br>Veuillez vérifier l'adresse avec le professeur.")

        # L'envoie de l'email n'est pas obligatoire
        try:
            send_mail(
                sujet,
                text_email,
                email_eleve,
                destinations,
                fail_silently=False,
            )
            
        except Exception as e:
            messages.error(request, f"Une erreur s'est produite lors de l'envoi de l'email : {str(e)}")
        messages.success(request, "La réponse à l'email est envoyée avec succé.")
        
        email_telecharge = Email_telecharge(user=user, email_telecharge=email_eleve, text_email=text_email, user_destinataire=user_destinataire, sujet=sujet )
        # messages.error(request, "Teste 04 ")
        email_telecharge.save()
        email_reponse_id = email_telecharge.id  # Récupérer l'ID de l'email enregistré  
        # Mettre à jour les champs de l'email reçu
        email.suivi = 'Répondu'
        email.date_suivi = date.today()
        email.reponse_email_id = email_reponse_id
        email.save() 
        messages.success(request, "Le contenu de l'email est enregistré")

        # vider les paramètres de la session email
        if 'text_email' in request.session:
            del request.session['text_email']
        if 'sujet' in request.session:
            del request.session['sujet']
        if 'email_eleve' in request.session:
            del request.session['email_eleve']
        if 'email_id' in request.session:
            del request.session['email_id']
        if hasattr(user, 'eleve'):
            return redirect('compte_eleve')
        elif hasattr(user, 'professeur'):
            return redirect('compte_prof')
        else: return redirect('index')
        
    
    return render(request, 'eleves/reponse_email_eleve.html', context)


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


def temoignage_eleve(request):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'eleve'):
        messages.error(request, "Vous n'etes pas connecté en tant qu'élève")
        return redirect('signin')

    slug_pattern = f'Elv{user.id}'
    
    # Filtrer les paiements approuvés de l'élève contenant son identifiant dans le slug
    payments = Payment.objects.filter(status='Approuvé', slug__icontains=slug_pattern)
    
    # Si aucun paiement approuvé, informer l'utilisateur et le rediriger
    if not payments.exists():
        messages.info(request, "Vous ne pouvez donner votre témoignage que si vous avez réglé au moins un cours.")
        return redirect('compte_eleve')
    
    # Récupérer les IDs des professeurs basés sur les paiements
    list_prof_ids = []
    for payment in payments:
        slug = payment.slug
        match = re.search(r'Prof(\d+)Elv', slug)
        if match:
            user_prof_id = int(match.group(1))
            if user_prof_id not in list_prof_ids:
                list_prof_ids.append(user_prof_id)
    
    # Obtenir la liste des professeurs concernés
    list_prof = User.objects.filter(id__in=list_prof_ids)
    
    # Initialiser les variables pour la sélection
    selected_prof = selected_temoignage = selected_text = None
    
    # Si le formulaire est soumis
    if 'btn_enr' in request.POST:
        # Récupérer les données du formulaire
        selected_prof = request.POST.get('prof', None)
        selected_temoignage = request.POST.get('temoignage', None)
        selected_text = request.POST.get('text', None)
        
        # Vérifier que les champs nécessaires sont bien remplis
        if selected_prof == '0' or not selected_temoignage or not selected_text.strip():
            messages.error(request, f"selected_temoignage = {selected_temoignage} ; Veuillez sélectionner un professeur, attribuer une évaluation et rédiger un commentaire.")
            return render(request, 'eleves/temoignage_eleve.html', {
                'list_prof': list_prof, 
                'selected_prof': selected_prof,
                'selected_temoignage': selected_temoignage,
                'selected_text': selected_text
            })

        # Récupérer le professeur sélectionné
        user_prof = User.objects.get(id=int(selected_prof))

        # Vérifier ou créer un nouveau témoignage
        temoignage, created = Temoignage.objects.get_or_create(
            user_eleve=user,
            user_prof=user_prof,
            defaults={
                'text_eleve': selected_text,
                'evaluation_eleve': selected_temoignage
            }
        )

        if not created:
            # Si le témoignage existe, le mettre à jour
            evaluation_eleve_ancien = temoignage.evaluation_eleve
            temoignage.text_eleve = selected_text
            temoignage.evaluation_eleve = selected_temoignage
            temoignage.save()
            messages.success(request, "Votre témoignage a été mis à jour.")
            
            # Mettre à jour l'historique du professeur
            historique_prof = Historique_prof.objects.filter(user=user_prof).first()
            historique_prof.total_point_cumule = historique_prof.total_point_cumule - evaluation_eleve_ancien + int(selected_temoignage)
            # messages.info(request, f'historique_prof.total_point_cumule = {historique_prof.total_point_cumule}')
        else:
            # Si un nouveau témoignage est créé
            messages.success(request, "Votre témoignage a été créé avec succès.")
            
            # Mettre à jour l'historique du professeur
            historique_prof = Historique_prof.objects.filter(user=user_prof).first()
            historique_prof.nb_evaluation += 1
            historique_prof.total_point_cumule += int(selected_temoignage)
        
        # Sauvegarder les modifications de l'historique
        historique_prof.save()
        # mise à jour moyenne des total_point_cumule
        if historique_prof.total_point_cumule and historique_prof.nb_evaluation and historique_prof.nb_evaluation>0:
            historique_prof.moyenne_point_cumule = int(historique_prof.total_point_cumule/(historique_prof.nb_evaluation))
            historique_prof.save()
            
        else: messages.error(request, f"Erreur de données dans historique professeur, voire Programmeur, <br> historique_prof.total_point_cumule = {historique_prof.total_point_cumule}, <br> historique_prof.nb_evaluation = {historique_prof.nb_evaluation}")
    
    # Rendre le template avec la liste des professeurs
    return render(request, 'eleves/temoignage_eleve.html', {'list_prof': list_prof})



def liste_paiement_eleve(request):
    """
        Vue permettant d'afficher les paiements de l'élève.

    Fonctionnalités :
    - Filtrer les paiements selon une période donnée (dates de début et de fin).
    - Appliquer des filtres selon le statut du paiement (en attente, approuvé, annulé, etc.).
    - Associer chaque paiement à sa demande de paiement et à une éventuellle date d'accord de règlement.
    """
    date_format = "%d/%m/%Y" # Assurez-vous que ce format est défini quelque part dans votre code

    # Récupérer le user
    user = request.user
    if not user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil d'élève associé
    if not hasattr(user, 'eleve'):
        messages.error(request, "Vous n'etes pas connecté en tant qu'élève")
        return redirect('signin')


    # Récupérer les demandes de paiement du professeur et les paiements associés
    demande_paiement = Demande_paiement.objects.filter(eleve=user.eleve)
    if not demande_paiement:
        messages.error(request, "Vous n'avez pas encore reçu de demande de paiement.")
        return redirect('compte_eleve')

    # Récupérer les paiements liés aux demandes de paiement
    paiement = Payment.objects.filter(
        model='demande_paiement',
        model_id__in=demande_paiement.values_list('id', flat=True)
    )

    # Récupération des dates minimales et maximales depuis les paiements associés aux demandes du professeur
    dates = paiement.aggregate(
        min_date=Min('date_creation'), 
        max_date=Max('date_creation')
    )

    # Définition des valeurs par défaut
    date_min = dates['min_date'] or (timezone.now().date() - timedelta(days=15))
    date_max = dates['max_date'] or timezone.now().date()

    # Récupération des valeurs envoyées par le formulaire POST avec fallback aux valeurs par défaut
    
    date_debut_str = request.POST.get('date_debut', date_min.strftime(date_format))
    date_fin_str = request.POST.get('date_fin', date_max.strftime(date_format))

    try:
        # Conversion des dates en objets de type date
        date_debut = datetime.strptime(date_debut_str, date_format).date()
        date_fin = datetime.strptime(date_fin_str, date_format).date()

        # Vérification de la cohérence des dates
        if date_debut > date_fin:
            raise ValueError("La date de début doit être inférieure ou égale à la date de fin.")

    except ValueError as e:
        # Gestion des erreurs en cas de format de date invalide
        messages.error(request, f"Erreur de date : {e}")
        return render(request, 'accounts/compte_prof.html', {
            'paiements': [], 
            'professeurs': [], 
            'date_debut': date_debut_str,  # Renvoi des valeurs sous forme de chaîne en cas d'erreur
            'date_fin': date_fin_str
        })

    # Définition des critères de filtrage des paiements
    filters = {
        'date_creation__range': (date_debut, date_fin + timedelta(days=1))  # Filtre sur la période sélectionnée
    }

    # Correspondance des boutons de filtrage aux statuts de paiement
    status_filter = {
        'btn_en_ettente': 'En attente',
        'btn_approuve': 'Approuvé',
        'btn_invalide': 'Invalide',
        'btn_annule': 'Annulé',
    }

    # Application du filtre de statut en fonction du bouton cliqué
    status_str = None
    for btn, status in status_filter.items():
        if btn in request.POST:
            filters['status'] = status
            status_str = status
            break

    # Filtrage des paiements contestés (réclamation)
    if 'btn_reclame' in request.POST:
        filters['reclamation__isnull'] = False  # Paiements contestés par l'élève
        status_str = "Réclamé"

    # Filtrage des paiements sans accord de règlement
    if 'btn_sans_accord' in request.POST:
        filters['accord_reglement_id'] = None  # Paiements contestés par l'élève
        status_str = "Sans accord"

    # Récupération des paiements en fonction des filtres
    payments = paiement.filter(**filters).order_by('-date_creation')

    # Initialisation des listes pour stocker les résultats
    paiements = []

    # Parcours des paiements récupérés pour associer les informations nécessaires
    for payment in payments:
        # Récupération de la demande de paiement associée
        demande_paiement = Demande_paiement.objects.filter(id=payment.model_id).first()
        if not demande_paiement: continue  # Ignorer les paiements sans demande associée

        # Récupérer le professeur
        professeur = demande_paiement.user
        
        accord_reglement = None

        # Vérification et récupération de l'accord de règlement associé
        if payment.accord_reglement_id:
            accord_reglement = AccordReglement.objects.filter(id=payment.accord_reglement_id).first()

        # Ajout des informations collectées à la liste des paiements
        # accord_reglement_id = encrypt_id(payment.accord_reglement_id)
        paiements.append((professeur, payment, accord_reglement))

    # Extraction de l'ID du paiement choisi dans le formulaire
    paiement_ids = [key.split('btn_paiement_id')[1] for key in request.POST.keys() if key.startswith('btn_paiement_id')]
    # Vérification du nombre d'IDs extraits
    if paiement_ids:
        if len(paiement_ids) == 1:  # Un seul ID trouvé, on le stocke en session
            eleve = Eleve.objects.filter(user=request.user).first() # Si le user est un professeur
            if eleve:
                paiement = Payment.objects.filter(id=paiement_ids[0]).first() # il faut que le paiement est de l'éléve
                if paiement and not Demande_paiement.objects.filter(id=paiement.model_id, eleve=eleve).exists(): # Si non il y a eu une manipulation des données du template
                    messages.error(request, f"le paiement sélectionné n'est pas de l'élève, paiement_id= {paiement_ids[0]}")
                    return redirect('compte_eleve')
            request.session['payment_id'] = paiement_ids[0] # passer le paramètre au formulaire
            return redirect('admin_payment_demande_paiement')
        elif len(paiement_ids) !=1:  # Plusieurs IDs trouvés, erreur système
            messages.error(request, "Erreur système, veuillez contacter le support technique.")
            return redirect('compte_eleve')

    # Préparation du contexte pour l'affichage dans le template
    context = {
        'paiements': paiements,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'status_str': status_str,
    }
    
    return render(request, 'eleves/liste_payment_eleve.html', context)


def liste_remboursement(request):
    """
        Vue permettant d'afficher les remboursement des élèves.

    Fonctionnalités :
    - Filtrer les remboursements selon une période donnée (dates de début et de fin).
    - Appliquer des filtres selon le statut des remboursements (en attente, approuvé, annulé, etc.).
    - Associer chaque remboursement à sa demande de paiement et à paiement.
    """

    date_format = "%d/%m/%Y" # Assurez-vous que ce format est défini quelque part dans votre code
    teste = True # pour controler les validations

    # Récupérer le user
    user = request.user
    if not user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   

    # Vérifier si l'utilisateur a un profil de eleve associé
    if not hasattr(user, 'eleve'):
        messages.error(request, "Vous n'etes pas connecté en tant qu'élève")
        return redirect('signin')
    

    # Récupération des dates minimales et maximales depuis la base de données
    dates = AccordRemboursement.objects.filter(
        ~Q(status='completed'),  # Exclure les enregistrements avec status='Réalisé'
        transfere_id__isnull=True,
        date_trensfere__isnull=True
    ).aggregate(
        min_date=Min('due_date'),
        max_date=Max('due_date')
    )

    # Définition des valeurs par défaut
    date_min = dates['min_date'] or (timezone.now().date() - timedelta(days=15))
    date_max = dates['max_date'] or timezone.now().date()

    # Récupération des valeurs envoyées par le formulaire POST avec fallback aux valeurs par défaut
    date_debut_str = request.POST.get('date_debut', date_min.strftime(date_format))
    date_fin_str = request.POST.get('date_fin', date_max.strftime(date_format))

    statut=""

    # Validation du format des dates
    try:
        date_debut = datetime.strptime(date_debut_str, date_format).date()
    except ValueError:
        messages.error(request, f"Format de la date de début de période invalide: {date_debut_str}. Utilisez jj/mm/aaaa.")
        teste = False
        date_debut = None

    try:
        date_fin = datetime.strptime(date_fin_str, date_format).date()
    except ValueError:
        messages.error(request, f"Format de la date de fin de période invalide: {date_fin_str}. Utilisez jj/mm/aaaa.")
        teste = False
        date_fin = None

    # Vérification que la date de début est bien avant la date de fin
    if teste:
        if date_debut > date_fin:
            messages.error(request, "La date de début doit être inférieure ou égale à la date de fin de période.")
            teste = False

    # Fonction interne pour récupérer les paiements en attente de règlement
    def get_remboursements(date_debut, date_fin, filter_criteria=None):
        if filter_criteria is None:
            filter_criteria = {}

        return AccordRemboursement.objects.filter(
            due_date__range=(date_debut , date_fin + timedelta(days=1)), eleve=user.eleve,
            **filter_criteria
        ).order_by('due_date') # [date_debut , date_fin]

    # Récupérer tous les accords de remboursements
    accord_remboursements = get_remboursements(date_debut, date_fin)

    # Vérification du type de requête et application des filtres en fonction du bouton cliqué
    if 'btn_tous' in request.POST:
        # Filtrer pour tous les emails
        accord_remboursements = get_remboursements(date_debut, date_fin)
    elif 'btn_en_ettente' in request.POST:
        # Filtrer pour les paiements en attente
        accord_remboursements = get_remboursements(date_debut, date_fin, {'status': 'pending'})
        statut = "En attente"
    elif 'btn_en_cours' in request.POST:
        # Filtrer pour les paiements approuvés
        accord_remboursements = get_remboursements(date_debut, date_fin, {'status': 'in_progress'})
        statut = "En cours"
    elif 'btn_invalide' in request.POST:
        # Filtrer pour les paiements invalides
        accord_remboursements = get_remboursements(date_debut, date_fin, {'status': 'invalid'})
        statut = "Invalide"
    elif 'btn_annule' in request.POST:
        # Filtrer pour les paiements annulés
        accord_remboursements = get_remboursements(date_debut, date_fin, {'status': 'canceled'})
        statut = "Annulé"
    elif 'btn_realiser' in request.POST:
        # Filtrer pour les paiements réclamés par les élèves
        accord_remboursements = get_remboursements(date_debut, date_fin, {'status': 'completed'})
        statut = "Réalisé"

    accord_remboursement_approveds = []
    for accord_remboursement in accord_remboursements:
        payments = Payment.objects.filter(id__in=DetailAccordRemboursement.objects.filter(accord=accord_remboursement).values_list('payment_id', flat=True))
        # si un des paiement est non approuvé par l'élève alors approved = False
        approved =True
        for payment in payments:
            if  payment.reclamation: 
                approved = False
                break
        accord_remboursement_approveds.append((accord_remboursement , approved))
    
    # Extraction de l'ID du remboursement choisi dans le formulaire
    accord_ids = [key.split('btn_detaille_remboursement_id')[1] for key in request.POST.keys() if key.startswith('btn_detaille_remboursement_id')]
    if accord_ids:
        # Vérification du nombre d'IDs extraits
        if len(accord_ids) == 1:  # Un seul ID trouvé, on le stocke en session
            eleve = Eleve.objects.filter(user=request.user).first() # Si le user est un eleve
            if eleve:
                remboursement = AccordRemboursement.objects.filter(id=accord_ids[0], eleve = eleve).first() # il faut que le règlement est pour le eleve
                if eleve and not remboursement: # Si non il y a eu une manipulation des données du template
                    messages.error(request, f"le remboursement sélectionné n'est pas attrubuté au eleve, remboursement_id= {accord_ids[0]}")
                    return redirect('compte_prof')
            request.session['accord_remboursement_id'] = encrypt_id(accord_ids[0])
            return redirect('admin_remboursement_detaille')

        elif len(accord_ids) != 1:  # Plusieurs IDs trouvés, erreur système
            messages.error(request, "Erreur système, veuillez contacter le support technique.")
            return redirect('compte_eleve')
    
    context = {
        'accord_remboursement_approveds': accord_remboursement_approveds,
        'date_fin':date_fin,
        'date_debut':date_debut,
        'statut': statut,
    }

    return render(request, 'eleves/liste_remboursement.html', context)



"""
Le décorateur @csrf_protect dans Django est utilisé pour activer 
la protection contre les attaques CSRF (Cross-Site Request Forgery) sur une vue.
Une attaque CSRF consiste à tromper un utilisateur authentifié pour qu’il soumette 
une requête malveillante à un site web sur lequel il est connecté, à son insu. 
Exemple : si un utilisateur est connecté à un site de banque et visite un site 
piégé, une requête pourrait être envoyée à son insu pour transférer de l'argent.
Vérifie que les requêtes POST (ou autres méthodes dangereuses comme PUT, DELETE) 
contiennent un jeton CSRF valide (csrfmiddlewaretoken) dans le formulaire HTML.
Empêche l'exécution de la vue si le jeton CSRF est manquant ou incorrect.
"""
@csrf_protect
def register_eleve(request):
    # Si la requête est une soumission de formulaire (méthode POST)
    if request.method == 'POST':
        # ===============================================
        # Récupération des données du formulaire utilisateur
        # ===============================================
        username = request.POST.get('username')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        remember_me = request.POST.get('remember_me')
        captcha_response = request.POST.get('g-recaptcha-response')
        logger.info(f"Token reCAPTCHA reçu : {captcha_response}")

        # Dictionnaire pour stocker les messages d’erreur
        errors = {}

        # Récupération de l’adresse IP et du navigateur de l'utilisateur
        user_ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', 'inconnu')

        # ==========================================================================
        # Vérification de la validité du CAPTCHA Google reCAPTCHA v3 (anti-robots)
        # ==========================================================================
        captcha_valid, captcha_score = verify_recaptcha(captcha_response, client_ip=user_ip)

        if not captcha_valid:
            errors['captcha'] = "Validation CAPTCHA échouée. Veuillez réessayer."
            logger.warning(
                f"CAPTCHA invalide - IP: {user_ip} - User-Agent: {user_agent} - Score: {captcha_score}"
            )
        elif captcha_score < getattr(settings, 'RECAPTCHA_MIN_SCORE', 0.5):
            errors['captcha'] = "Activité suspecte détectée"
            logger.warning(
                f"Score CAPTCHA trop bas - IP: {user_ip} - Score: {captcha_score}"
            )

        # ==================================================
        # Validation de l'email : format correct + unicité
        # ==================================================
        try:
            validate_email(email)
            if get_user_model().objects.filter(email=email).exists():
                errors['email'] = "Cet email est déjà utilisé."
                logger.warning(f"Email existant: {email} - IP: {user_ip}")
        except ValidationError:
            errors['email'] = "Veuillez entrer une adresse email valide."

        # ===========================================
        # Vérification que le nom d'utilisateur est libre
        # ===========================================
        if get_user_model().objects.filter(username=username).exists():
            errors['username'] = "Ce nom d'utilisateur est déjà pris."
            logger.warning(f"Username existant: {username} - IP: {user_ip}")

        # ===========================================
        # Vérification de la qualité du mot de passe
        # ===========================================
        if password != password_confirm:
            errors['password'] = "Les mots de passe ne correspondent pas."
        elif len(password) < 8:
            errors['password'] = "Le mot de passe doit contenir au moins 8 caractères."

        # ========================================================
        # En cas d'erreurs, affichage des messages et retour page
        # ========================================================
        if errors:
            for field, error in errors.items():
                messages.error(request, error)
            return render(request, 'eleves/register_eleve.html', {
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'recaptcha_site_key': settings.RECAPTCHA_PUBLIC_KEY,
            })

        # =====================================================================
        # Si aucune erreur, création du compte utilisateur et du profil élève
        # =====================================================================
        try:
            # Création de l'utilisateur Django avec mot de passe chiffré
            user = get_user_model().objects.create(
                username=username,
                email=email,
                password=make_password(password),  # Hachage sécurisé
                first_name=first_name,
                last_name=last_name,
                is_active=True
            )

            # Création du profil élève associé à cet utilisateur
            Eleve.objects.create(user=user)

            logger.info(
                f"Nouvel élève inscrit: {user.username} ({user.email}) - IP: {user_ip} - Score CAPTCHA: {captcha_score}"
            )

            # ==================================================
            # Connexion automatique de l’utilisateur après inscription
            # ==================================================
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)

                # Gestion de la persistance via "remember me" (JWT + cookie)
                if remember_me:
                    payload = {
                        'user_id': user.id,
                        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=30),  # Expiration
                        'iat': datetime.datetime.utcnow(),  # Date de création
                        'ip': user_ip
                    }
                    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
                    response = redirect('compte_eleve')
                    response.set_cookie(
                        'remember_me', token, max_age=30*24*60*60, httponly=True, secure=not settings.DEBUG
                    )
                    return response

                # Redirection vers le tableau de bord élève
                return redirect('compte_eleve')

        # =========================================================
        # Gestion des erreurs imprévues durant la création de compte
        # =========================================================
        except Exception as e:
            logger.error(
                f"Erreur création de compte - Username: {username} - IP: {user_ip} - Erreur: {str(e)}"
            )
            messages.error(request, "Une erreur est survenue lors de la création de votre compte. Veuillez réessayer.")
            return render(request, 'eleves/register_eleve.html', {
                'recaptcha_site_key': settings.RECAPTCHA_PUBLIC_KEY
            })

    # ===============================
    # Affichage de la page d’inscription
    # ===============================
    return render(request, 'eleves/register_eleve.html', {
        'recaptcha_site_key': settings.RECAPTCHA_PUBLIC_KEY
    })


@csrf_protect
def demande_paiement_eleve(request):
    """
    Vue permettant d'afficher les demandes de paiements.

    Fonctionnalités :
    - Filtrer les demandes de paiements selon une période donnée (dates de début et de fin).
    - Appliquer des filtres selon le statut des demandes de paiement (en attente, approuvé, annulé, etc.).
    - Affiche les détailles des demandes de paiements
    - fait passer vers l'execution du paiement
    """

    # Format utilisé pour l'affichage et la conversion des dates
    date_format = "%d/%m/%Y"
    status_str=""

    # Récupérer le user
    user = request.user
    if not user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   

    # Vérifier si l'utilisateur a un profil de eleve associé
    if not hasattr(user, 'eleve'):
        messages.error(request, "Vous n'etes pas connecté en tant qu'élève")
        return redirect('signin')
    
    eleve = user.eleve

    # Récupération des dates minimales et maximales depuis la base de données
    dates = Demande_paiement.objects.filter(
        eleve=eleve,
        statut_demande__in = ('En attente', 'Contester'),
        payment_id__isnull = True, # il n'y a pas de paiement
        accord_reglement_id__isnull = True, # Il n'y a pas encore d'accord de règlement (en plus, pas nécessaire vue la condition précédente)
    ).aggregate(min_date=Min('date_creation'), max_date=Max('date_creation'))

    # Définition des valeurs par défaut
    date_min = dates['min_date'] or (timezone.now().date() - timedelta(days=15))
    date_max = dates['max_date'] or timezone.now().date()

    # Récupération des valeurs envoyées par le formulaire POST avec fallback aux valeurs par défaut
    date_debut_str = request.POST.get('date_debut', date_min.strftime(date_format))
    date_fin_str = request.POST.get('date_fin', date_max.strftime(date_format))

    # Initialisation des variables date_debut et date_fin
    date_debut, date_fin = None, None

    try:
        # Conversion des dates en objets de type date
        date_debut = datetime.strptime(date_debut_str, date_format).date()
        date_fin = datetime.strptime(date_fin_str, date_format).date()

        # Vérification de la cohérence des dates
        if date_debut > date_fin:
            raise ValueError("La date de début doit être inférieure ou égale à la date de fin.")
    
    except ValueError as e:
        # Gestion des erreurs en cas de format de date invalide
        messages.error(request, f"Erreur de date : {e}")
        return render(request, 'eleves/demande_paiement_eleve.html', {
            'demande_paiements': [], 
            'professeurs': [], 
            'date_debut': date_debut, 
            'date_fin': date_fin
        })

    # Définition des critères de filtrage des paiements
    filters = {
        'date_creation__range': (date_debut, date_fin + timedelta(days=1)), # Filtre sur la période sélectionnée
        'eleve': eleve,
    }

    # Correspondance des boutons de filtrage aux statuts de paiement
    status_filter = {
        'btn_en_ettente': 'En attente',   # Demande de paiements en attente
        'btn_en_cours': 'En cours',   # Demande de paiements en cours
        'btn_realiser': 'Réaliser',   # Demande de paiements en réaliser
        'btn_contester': 'Contester',   # Demande de paiements contester
        'btn_annuler': 'Annuler',      # Demande de paiements annuler
    }

    # Application du filtre de statut en fonction du bouton cliqué
    for btn, status in status_filter.items():
        if btn in request.POST:
            filters['statut_demande'] = status
            status_str=status
            break

    # Récupération des paiements en fonction des filtres
    demande_paiements_data = Demande_paiement.objects.filter(**filters).order_by('-date_creation')

    # tester demande_paiements_data si elle est null

    # Initialisation des listes pour stocker les résultats
    demande_paiements, professeurs = [], set()

    # Parcours des paiements récupérés pour associer les informations nécessaires
    for demande_paiement in demande_paiements_data:
        professeur = demande_paiement.user  # Récupération du professeur lié au paiement

        # Ajout des informations collectées à la liste des paiements
        id = encrypt_id(demande_paiement.id)
        demande_paiements.append((demande_paiement, professeur, id))
        professeurs.add(professeur)  # Utilisation d'un set() pour éviter les doublons

    # Extraction de l'ID de la demande de paiement choisi dans le formulaire
    demande_paiement_ids = [key.split('btn_demande_paiement_id')[1] for key in request.POST.keys() if key.startswith('btn_demande_paiement_id')]

    # Vérification du nombre d'IDs extraits
    if demande_paiement_ids:
        if len(demande_paiement_ids) == 1:  # Un seul ID trouvé, on le stocke en session
            request.session['demande_paiement_id'] = demande_paiement_ids[0]
            return redirect('eleve_demande_paiement')
        elif len(demande_paiement_ids) !=1:  # Plusieurs IDs trouvés, erreur système
            messages.error(request, "Erreur système, veuillez contacter le support technique.")
            # return redirect('compte_administrateur')

    # Préparation du contexte pour l'affichage dans le template
    context = {
        'today': timezone.now().date(),  # Date actuelle pour affichage
        'demande_paiements': demande_paiements,
        'professeurs': list(professeurs),
        'date_debut': date_debut,
        'date_fin': date_fin,
        'status_str': status_str,
    }

    # Affichage de la page avec les paiements en attente de règlement
    return render(request, 'eleves/demande_paiement_eleve.html', context)


from django.contrib.auth.decorators import login_required
from django.views.decorators.clickjacking import xframe_options_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@csrf_protect # Optionnel si vous voulez explicitement protéger la vue contre les attaques CSRF
@xframe_options_exempt
@login_required  # Exige que l'utilisateur soit connecté
def eleve_demande_paiement(request):
    user = request.user

    # Vérifie que l'utilisateur a un profil élève
    if not hasattr(user, 'eleve'):
        messages.error(request, "Vous n'êtes pas connecté en tant qu'élève")
        logger.warning("Utilisateur %s tenté d'accéder à la vue élève sans profil élève.", user)
        return redirect('signin')
    
    # Récupère l'ID de la demande de paiement depuis la session
    demande_paiement_id = request.session.get('demande_paiement_id')
    if not demande_paiement_id:
        logger.warning("Aucune demande de paiement trouvée en session pour l'utilisateur %s", user)
        messages.info(request, "Il n'y a pas de paiement")
        return redirect('compte_administrateur')

    # Déchiffrement de l'ID
    try:
        demande_paiement_id_decript = decrypt_id(demande_paiement_id)
        logger.info("Demande de paiement décryptée avec succès: %s", demande_paiement_id_decript)
    except Exception as e:
        logger.error("Erreur lors du déchiffrement de l'ID de demande de paiement : %s", str(e))
        messages.error(request, "Erreur interne lors du traitement de la demande.")
        return redirect('compte_administrateur')

    # Récupère l'objet demande de paiement
    demande_paiement = get_object_or_404(Demande_paiement, id=demande_paiement_id_decript)
    prof = demande_paiement.user

    # Enregistre que l'élève a vu la demande
    if not demande_paiement.vue_le:
        demande_paiement.vue_le = timezone.now()
        demande_paiement.save()
        logger.info("L'élève %s a vu la demande %s", user, demande_paiement.id)

    # Récupère les détails de la demande avec les relations préchargées
    details_demande_paiement = Detail_demande_paiement.objects.select_related('cours', 'horaire').filter(
        demande_paiement=demande_paiement
    )

    # Récupère les emails associés s'ils existent
    email_ids = filter(None, [demande_paiement.email, demande_paiement.email_eleve])
    emails = {email.id: email for email in Email_telecharge.objects.filter(id__in=email_ids)}

    def format_email(email_id):
        email = emails.get(email_id)
        return f"Sujet: {email.sujet}\nContenu: {email.text_email}" if email else "Pas de message"

    texte_email_prof = format_email(demande_paiement.email)
    texte_email_eleve = format_email(demande_paiement.email_eleve)

    # Associe chaque détail (cours + horaire)
    horaires = [(detail.cours, detail.horaire) for detail in details_demande_paiement]
    cours_set = {detail.cours for detail in details_demande_paiement}

    # Récupère les prix publics associés aux cours
    cours_prix_publics = []
    for cours in cours_set:
        matiere_obj = Matiere.objects.filter(matiere=cours.matiere).first()
        niveau_obj = Niveau.objects.filter(niveau=cours.niveau).first()
        prof_mat_niv = Prof_mat_niv.objects.filter(
            user=demande_paiement.user,
            matiere=matiere_obj, 
            niveau=niveau_obj
        ).first()
        prix_public = Prix_heure.objects.filter(
            user=demande_paiement.user,
            prof_mat_niv=prof_mat_niv
        ).values_list('prix_heure', flat=True).first() if prof_mat_niv else None

        cours_prix_publics.append((cours, prix_public))

    # Prépare le contexte pour le template
    context = {
        'today': timezone.now().date(),
        'demande_paiement': demande_paiement,
        'texte_email_prof': texte_email_prof,
        'texte_email_eleve': texte_email_eleve,
        'horaires': horaires,
        'cours_prix_publics': cours_prix_publics,
    }

    # Gère le bouton "Réclamation"
    if 'btn_reclamation' in request.POST:
        if demande_paiement.reclamation and demande_paiement.reclamation.id:
            logger.info("Accès à la réclamation pour la demande %s", demande_paiement.id)
            request.session['reclamation_id'] = demande_paiement.reclamation.id
            return redirect('reclamation')
        else:
            logger.warning("Aucune réclamation liée à la demande %s", demande_paiement.id)
            messages.error(request, "Il n'y a pas de réclamation liée à la demande de paiement")

    # Gère le POST général
    if request.method == 'POST':

        # Bouton Stripe "Payer maintenant"
        if 'btn_paiement_checkout' in request.POST:
            # Récupère de nouveau l'objet demande de paiement pour empécher un double enregistrement
            # c'est une trés bonne idée à généraliser pour les enregistrements importants
            demande_paiement = get_object_or_404(Demande_paiement, id=demande_paiement_id_decript)
            if demande_paiement.payment_id:
                messages.error(request, "La demande de règlement est déjà payée")
                return redirect('compte_eleve')
            from payment.views import create_checkout_session
            Cart.objects.filter(user=request.user).delete()
            cart = Cart.objects.create(user=request.user)
            for cours, prix_public in cours_prix_publics:
                for cours_paiement, horaire in horaires:
                    if cours == cours_paiement:
                        description = (
                            f"{cours.format_cours}, {cours.matiere}, {cours.niveau}, "
                            f"prix/h : {cours.prix_heure} €"
                            f", le : {horaire.date_cours.strftime('%d/%m/%Y')}"
                            f", durée : {horaire.duree}h"
                        )
                        total_price_cents = int(horaire.duree * cours.prix_heure * 100)
                        CartItem.objects.create(
                            cart=cart,
                            cours=description,
                            quantity=1,
                            price=total_price_cents
                        )
            logger.info("Panier Stripe préparé pour l'élève %s", user)
            # Seule le paiement est créé (En attente), les autres tables liées au paiement non
            # leur tour commence aprés confirmation du paiement
            # Création ou mise à jour de l'enregistrement Payment
            payment, created = Payment.objects.update_or_create(
                model="demande_paiement",
                model_id=demande_paiement.id,
                defaults={
                    'status': 'En attente',  # À changer par "Approuvé" après validation
                    'amount': demande_paiement.montant,
                    # 'expiration_date': timezone.now(),
                    'currency': "Euro",
                    'language': "Français",
                }
            )

            # en liant cart au payment on peut lier invoice au payment dans la view create_checkout_session
            cart.payment = payment
            cart.save()
            if created:
                logger.info(f"✅ Nouveau paiement créé : ID={payment.id}, Montant={payment.amount}")
            else:
                logger.info(f"♻️ Paiement existant mis à jour : ID={payment.id}, Montant={payment.amount}")
            
            # mise à jour Demande_paiement mais l'ID du paiement n'est pas encore défini
            demande_paiement.statut_demande = "En cours" # # à changer par Approuvé
            demande_paiement.save()
            request.session['payment_id'] = payment.id
            request.session['prof_id'] = prof.id
            request.session['demande_paiement_id_decript'] = demande_paiement_id_decript 
            return create_checkout_session(request)
        
        else:
            messages.warning(request, "Le paiement n'est pas effectué.")
            logger.info("L'élève %s n'a pas validé le paiement pour la demande %s", user, demande_paiement.id)

    return render(request, 'eleves/eleve_demande_paiement.html', context)

