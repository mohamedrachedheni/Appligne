from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404 #dans le cas ou l' id du user ne correspond pas à un user
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Eleve, Parent
from accounts.models import Matiere, Niveau, Region, Departement, Email_telecharge, Email_detaille, Email_suivi
import re
from django.contrib import auth
from accounts.models import Professeur
from datetime import date, datetime
from django.utils import formats
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.shortcuts import render, redirect




# Create your views here.

def nouveau_compte_eleve(request):
    # Définir les variables
    is_added = False
    user_nom = ""
    mot_pass = ""
    conf_mot_pass = ""
    prenom = ""
    nom = ""
    email = ""
    # Définir le context à envoyer au request
    context={
    'is_added':is_added,
    'user_nom':user_nom,
    'mot_pass':mot_pass,
    'conf_mot_pass':conf_mot_pass,
    'prenom':prenom,
    'nom':nom,
    'email':email
    }
    
    if request.method == 'POST' and 'btn_enr' in request.POST:
        # definir les variable pour les champs
        user_nom = ""
        mot_pass = ""
        conf_mot_pass = ""
        prenom = ""
        nom = ""
        email = ""
        is_added = False
        
        # get valus from the form
        # si user_nom existe parmis les valeurs retournées par request.POST
        # alors la user_nom prend la valeur retournée user_nom
        # cette erreur peut etre causée en changeant le template en cliquant sur le bouton droit de la souris puis inspecter
        if 'user_nom' in request.POST: 
            user_nom = request.POST['user_nom']
            if not user_nom.strip():
                messages.error(request, "Le nom de l'utilisateur ne peut pas être vide ou contenir uniquement des espaces.")
        # si non le message d'erreur est envoyé
        else: messages.error(request, "Erreur liée au nom de l'utilisateur")
        # le paramètre de redirect est url et de render est template
        if 'mot_pass' in request.POST: mot_pass = request.POST['mot_pass']# Vérifier la longueur du mot de passe
        else: messages.error(request, "Erreur liée au mot de passe")
        if 'conf_mot_pass' in request.POST and mot_pass == request.POST['conf_mot_pass']: conf_mot_pass = request.POST['conf_mot_pass']
        else: messages.error(request, "Erreur liée à la confirmatio du mot de passe")
        if 'prenom' in request.POST: prenom = request.POST['prenom'] 
        else: messages.error(request, "Erreur liée au prénom")
        if 'nom' in request.POST: nom = request.POST['nom']
        else: messages.error(request, "Erreur liée au nom")
        if 'email' in request.POST: email = request.POST['email']
        else: messages.error(request, "Erreur liée à l'email")

        if user_nom and mot_pass and conf_mot_pass  and prenom and nom and email :
            if User.objects.filter(username=user_nom).exists():
                messages.error(request, "Le nom de l'utilisateur est déjà utilisé, donnez un autre nom.")
            else:
                if User.objects.filter(email=email).exists():
                    messages.error(request, "L'email est déjà utilisé, donnez un autre email")
                else:
                    if not prenom.strip() or not nom.strip()  or not user_nom.strip():
                        messages.error(request, "Le prénom, le nom et le nom de l'utilisateur ne peuvent pas être vide ou contenir uniquement des espaces.")
                    else:
                        if len(mot_pass) < 8:
                            messages.error(request, "Le mot de passe doit contenir au moins 8 caractères.")
                        else:
                            # définir un forma pour l'email
                            patt = "^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$"
                            # si le format de l'email est correcte
                            if re.match(patt, email):
                                # ajouter le user
                                user = User.objects.create_user(first_name=prenom, last_name=nom, email=email, username=user_nom, password=mot_pass, is_active=True)
                                user.save()
                                # ajouter un élève lié au user
                                eleve = Eleve(user=user)
                                eleve.save()
                                auth.login(request, user)
                                if not user.is_authenticated: 
                                    messages.error(request, "Vous devez vous connecter à votre compte pour continuer")
                                    return redirect('signin') 
                                else:
                                    # messages.success(request, f"Vous êtes actuellement connecté à votre compte nom de l'utilisateur = {request.user.username}")
                                    messages.success(request, "Votre identité a été enregistrée avec succès, vous êtes désormais libre de contacter les professeurs de votre préférence.")
                                return render(request, 'eleves/compte_eleve.html')
                            else: messages.error(request, "Le format de l'email est incorrecte.")
        else: messages.error(request, "Les champs obligatoires ne doivent pas être vides")
        # pour conserver les données si il y a erreur
        return render(request, 'eleves/nouveau_compte_eleve.html', {is_added:is_added})
    else:
        return render(request, 'eleves/nouveau_compte_eleve.html', {is_added:is_added})
    
def compte_eleve(request):
    # Récupérer l'utilisateur actuel
    user = request.user
    if user.is_authenticated:
        # messages.success(request, f"Vous etes connecté. {user.first_name}")
        # Vérifier si l'utilisateur a un profil de professeur associé
        if hasattr(user, 'eleve'):
            return render(request, 'eleves/compte_eleve.html')
    messages.error(request, "Vous devez être connecté pour effectuer cette action.")
    return redirect('signin')

def modifier_coordonnee_eleve(request):

    # Récupérer l'utilisateur actuel
    user = request.user
    # eleve = Eleve.objects.get(user=user)
    # messages.info(request, f"civilite = {eleve.civilite}; email = {user.email}; adresse = {eleve.adresse}; numero_telephone = {eleve.numero_telephone}; date_naissance = {eleve.date_naissance} ")

    # messages.info(request, "Teste : 1")
    if user.is_authenticated and hasattr(user, 'eleve'):
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
    messages.error(request, "Vous devez être connecté pour effectuer cette action.")
    return redirect('signin')




def ajout_coordonnee_parent(request):
    user = request.user
    # messages.info(request, "Teste : 1")
    
    if user.is_authenticated and not hasattr(user, 'parent'):
        if request.method == 'POST' and 'btn_enr' in request.POST:
            prenom_parent = request.POST['prenom_parent']
            nom_parent = request.POST['nom_parent']
            civilite = request.POST['civilite']
            telephone_parent = request.POST['telephone_parent']
            email_parent = request.POST['email_parent']
            
            patt = "^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$"
            if re.match(patt, email_parent):
                # Création de l'objet Parent
                parent = Parent.objects.create(
                    user=user,
                    prenom_parent=prenom_parent,
                    nom_parent=nom_parent,
                    civilite=civilite,
                    telephone_parent=telephone_parent,
                    email_parent=email_parent
                )
                messages.success(request, "Vos informations ont été mises à jour avec succès.")
                return redirect('compte_eleve')
            else:
                messages.error(request, "L'adresse e-mail n'est pas valide.")
                context = {
                    'prenom_parent': prenom_parent,
                    'nom_parent': nom_parent,
                    'email_parent': email_parent,
                    'civilite': civilite,
                    'telephone_parent': telephone_parent,
                }
                return render(request, 'eleves/ajout_coordonnee_parent.html', context)
    messages.warning(request, "Vos coordonnées en tant que parent existent déjà. vous pouvez les modifier")
    return render(request, 'eleves/modifier_coordonnee_parent.html')

def modifier_coordonnee_parent(request):
    patt = "^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$"
    user = request.user
    # messages.info(request, "Teste : 1")
    
    if user.is_authenticated and  hasattr(user, 'parent'):
        # messages.info(request, "Teste : 2")
        parent = user.parent
        prenom_parent = parent.prenom_parent
        nom_parent = parent.nom_parent
        civilite = parent.civilite
        telephone_parent = parent.telephone_parent
        email_parent = parent.email_parent
        context = {
            'prenom_parent': prenom_parent,
            'nom_parent': nom_parent,
            'email_parent': email_parent,
            'civilite': civilite,
            'telephone_parent': telephone_parent,
        }
        if not (request.method == 'POST' and 'btn_enr' in request.POST):
            return render(request, 'eleves/modifier_coordonnee_parent.html', context)
        prenom_parent = request.POST['prenom_parent']
        nom_parent = request.POST['nom_parent']
        civilite = request.POST['civilite']
        telephone_parent = request.POST['telephone_parent']
        email_parent = request.POST['email_parent']
        context = {
            'prenom_parent': prenom_parent,
            'nom_parent': nom_parent,
            'email_parent': email_parent,
            'civilite': civilite,
            'telephone_parent': telephone_parent,
        }
        if User.objects.filter(email=email_parent).exists() and email_parent != user.email:
            messages.error(request, "L'email est déjà utilisé, donnez un autre email")
            return render(request, 'eleves/modifier_coordonnee_parent.html', context)
        if not prenom_parent.strip() or not nom_parent.strip():
            messages.error(request, "Le prénom, le nom et le nom de l'utilisateur ne peuvent pas être vide ou contenir uniquement des espaces.")
            return render(request, 'eleves/modifier_coordonnee_parent.html', context)
        if  (re.match(patt, email_parent)) or not email_parent.strip() :
            # Création de l'objet Parent
            # Mise à jour de l'objet Parent existant
            parent.prenom_parent = prenom_parent
            parent.nom_parent = nom_parent
            parent.civilite = civilite
            parent.telephone_parent = telephone_parent
            parent.email_parent = email_parent
            parent.save()
            messages.success(request, "Les informations du parent ont été mises à jour avec succès.")
            return redirect('compte_eleve')
        messages.error(request, "L'adresse e-mail n'est pas valide.")
        return render(request, 'eleves/modifier_coordonnee_parent.html', context)   
    messages.error(request, "Il faut créer vos données de parent avant.")
    # messages.info(request, "Teste : 3")
    return render(request, 'eleves/ajout_coordonnee_parent.html')


def demande_cours_eleve(request):
    # Paramètres par défaut
    # Récupère l'ancienne valeur de la région à partir de la session
    # la valeur de la session par défaut est 'Paris'
    region_ancien = request.session.get('region_ancien', 'PARIS')
    focus_departement = False
    matiere_defaut = "Maths"
    niveau_defaut = "6ème"
    region_defaut = "ILE-DE-FRANCE"
    departement_defaut = "PARIS"
    radio_name = "a_domicile"
    
    # Vérifie si la méthode de la requête est POST
    if request.method == 'POST':
        # Met à jour les paramètres par défaut avec les valeurs soumises dans le formulaire POST
        matiere_defaut = request.POST['matiere']
        niveau_defaut = request.POST['niveau']
        region_defaut = request.POST['region']
        departement_defaut = request.POST['departement']
        # Vérifie si la région a été modifiée
        if region_defaut != region_ancien:
            # Stocke la nouvelle valeur de la région dans la session
            request.session['region_ancien'] = region_defaut
            # Réinitialise le département si la région a été modifiée
            departement_defaut = ""
            messages.warning(request, "Choisissez un département")
            focus_departement = True
                   
        # Vérifie quel type de cours a été sélectionné (à domicile, en ligne, stage, etc.)
        if request.POST.get('a_domicile', None): 
            radio_name = "a_domicile"
        if request.POST.get('webcam', None): 
            radio_name = "webcam"
        if request.POST.get('stage', None): 
            radio_name = "stage"
        if request.POST.get('stage_webcam', None): 
            radio_name = "stage_webcam"
    
    # Récupère les professeurs filtrés en fonction des paramètres par défaut
    # Utilise prefetch_related pour optimiser les requêtes SQL et éviter les requêtes multiples
    professeurs = User.objects.filter(
        professeur__isnull=False, 
        prof_mat_niv__matiere__matiere=matiere_defaut, 
        prof_mat_niv__niveau__niveau=niveau_defaut, 
        prof_zone__commune__departement__departement=departement_defaut, 
        **{f'format_cour__{radio_name}': True},  # Utilisation de f-string pour construire dynamiquement le nom du paramètre
    ).prefetch_related(
        'experience_set',
        'prof_mat_niv_set',
        'diplome_set',
        'professeur',
        'pro_fichier'
    ).distinct().order_by('id')

    # Définit le nombre d'éléments par page pour la pagination
    elements_par_page = 4

    # Initialise un objet Paginator avec les professeurs filtrés
    paginator = Paginator(professeurs, elements_par_page)

    # Obtient le numéro de la page à afficher, par défaut page=1
    page = request.GET.get('page', 1)

    # Obtient la liste des professeurs pour la page spécifiée
    professeurs = paginator.get_page(page)

    # Récupère toutes les matières, niveaux, régions et départements
    matieres = Matiere.objects.all()
    niveaux = Niveau.objects.all()
    regions = Region.objects.filter(nom_pays__nom_pays='France')
    departements = Departement.objects.filter(region__region=region_defaut)

    # Stocke les choix de l'élève dans la session
    request.session['matiere_defaut'] = matiere_defaut
    request.session['niveau_defaut'] = niveau_defaut
    request.session['departement_defaut'] = departement_defaut
    request.session['radio_name'] = radio_name

    # Contexte à passer au modèle pour le rendu HTML
    context = {
        'focus_departement':focus_departement, # paramètre bool pour activer fonction js: document.getElementById('departement_id').focus();
        'professeurs': professeurs, # Table
        'matieres': matieres, # Table
        'niveaux': niveaux, # Table
        'regions': regions, # Table
        'departements': departements, # Table
        'matiere_defaut': matiere_defaut, # valeur
        'niveau_defaut': niveau_defaut, # valeur
        'region_defaut': region_defaut, # valeur
        'departement_defaut': departement_defaut, # valeur
        'radio_name': radio_name, # paramètre pour cocher un radio parmis quatre
    }
    # Rendu du modèle HTML avec le contexte
    return render(request, 'eleves/demande_cours_eleve.html', context)



def demande_cours_envoie(request, id_prof):
    user_prof = get_object_or_404(User, id=id_prof)
    user = request.user
    if user.is_authenticated and hasattr(user, 'eleve'):
        # messages.error(request, "Teste 01 ")
        email_prof = user_prof.email
        nom_prof = user_prof.first_name + " " + user_prof.last_name
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
            'email_prof': email_prof,
            'formatted_content': formatted_content,
            'user': user,
            'id_prof':id_prof
        }
        if not (request.method == 'POST' and 'btn_enr' in request.POST):
            return render(request, 'eleves/demande_cours_envoie.html', context)
        email_user = user.email
        email_prof = request.POST.get('email_user')
        text_email = request.POST.get('text_email')
        # messages.info(request, f"text_email = {text_email}")
        if text_email:
            # messages.error(request, "Teste 01 ")
            if not email_prof:
                #messages.error(request, "Teste 02 ")
                # si l'utilisateur n'a pas spécifié son email, l'email de l'utiluisateur déjà enregistré est pris par défaut
                email_prof = email_user
            # messages.error(request, "Teste 03 ")
            # dans ce cas le destinataire de l'Email est le prof
            user_destinataire = user_prof.id
            
            # traitement de l'envoie de l'email
            # si le sujet de l'email n'est pas défini dans le GET alors sujet='Demande de cours
            sujet = request.POST.get('sujet', '').strip()
            if not sujet: sujet = "Demande de cours"
            # on peut ajouter d'autres destinations: destinations = ['prosib25@gmail.com', 'autre_adresse_email']
            destinations = ['prosib25@gmail.com']
            try:
                send_mail(
                    sujet,
                    text_email,
                    email_prof,
                    destinations,
                    fail_silently=False,
                )
                messages.success(request, "L'email a été envoyé avec succès.")
                email_telecharge = Email_telecharge(user=user, email_telecharge=email_prof, text_email=text_email, user_destinataire=user_destinataire )
                # messages.error(request, "Teste 04 ")
                email_telecharge.save()
                # messages.error(request, "Teste 05 ")
                # messages.success(request, f"Le contenu de l'email est enregistré dans la table Email_telecharge")
                # Enregistrement dans la table détaille email
                email_detaille = Email_detaille(email=email_telecharge, user_nom=nom_parent + " / " + nom_eleve, matiere=matiere_defaut, niveau=niveau_defaut, format_cours=radio_name )
                email_detaille.save()
                # messages.success(request, f"Le contenu du détaille de l'email est enregistré dans la table Email_detaille")

                # enregistrer du code email dans la table de gestion des email à revoire
                return redirect('compte_eleve')
            except Exception as e:
                messages.error(request, f"Une erreur s'est produite lors de l'envoi de l'email: {str(e)}")
        messages.error(request, "Il faut définir le contenu de l'Email")
        return render(request, 'eleves/demande_cours_envoie.html', context)
    messages.error(request, "Vous devez être connecté pour effectuer cette action.")
    return redirect('signin')


def email_recu(request):
    # messages.error(request, "Test 01")
    # Vérification si l'utilisateur est connecté
    if not request.user.is_authenticated:
        messages.error(request, "Vous devez être connecté pour accéder à cette page.")
        return redirect('signin')
    
    user_id = request.user.id
    # recupérer les email destinés au user
    emails = Email_telecharge.objects.filter(user_destinataire=user_id)
    
    if not emails:
        messages.error(request, "Il n'y a pas d'Email envoyé à votre compte.")
        return redirect('votre_compte')
    
    
    context = {
        
        'emails': emails
    }
    
    return render(request, 'eleves/email_recu.html', context)



def email_detaille(request, email_id):
    email = Email_telecharge.objects.filter(id=email_id).first()
    user_id = email.user_destinataire
    user = User.objects.filter(id=user_id).first()
    email_id = email.id
    context={
        'email':email,
    }
    if 'btn_ignorer' in request.POST:
        # messages.success(request, "Teste 02.")
        Email_suivi.objects.create(user=user, email=email, suivi="Ignorer")
        messages.success(request, "L'email est enregistré en tant qu'email ignoré.")
        return redirect('compte_eleve')
    if 'btn_confirmer' in request.POST:
        # messages.success(request, "Teste 03.")
        sujet = "Confirmation de réception"
        text_email =  f"""
J'ai bien reçu votre email
Date de réception:{email.date_telechargement}
Sujet de l'émail: {email.sujet}
Contenu de l'émail:
{email.text_email}
"""
        email_prof = user.email
        email_eleve = email.email_telecharge
        eleve_id = email.user.id
        messages.success(request, f"L'email_eleve: {email_eleve}.")
        destinations = ['prosib25@gmail.com', email_eleve]  # Change it to actual destinations
        try:
            send_mail(
                sujet,
                text_email,
                email_prof,
                destinations,
                fail_silently=False,
            )  
        except Exception as e:
            messages.error(request, f"Une erreur s'est produite lors de l'envoi de l'email : {str(e)}")

        messages.success(request, "L'email a été envoyé avec succès.")
        email_telecharge = Email_telecharge(user=user, email_telecharge=email_prof, text_email=text_email, user_destinataire=eleve_id, sujet=sujet )
        # messages.error(request, "Teste 04 ")
        email_telecharge.save()
        Email_suivi.objects.create(user=user, email=email_telecharge, suivi="Réception confirmée", reponse_email_id=email_id)
        # Ajoutez ici le code pour gérer les enregistrements liés au professeur, si nécessaire.
        # messages.success(request, "L'email est enregistré en tant que réception confirmée et un email de confirmation a été envoyé.")
        return redirect('compte_eleve')
    if 'btn_repondre' in request.POST:
        # messages.success(request, "Teste 04.")
        email_eleve = user.email
        sujet = "Suite à votre email"
        text_email =  f"""
Suite à votre email:
Date de réception:{email.date_telechargement}
Sujet de l'émail: {email.sujet}
Contenu de l'émail:
{email.text_email}
---------------------------
En réponse à votre email, je vous adresse ce qui suit.
"""
        context={
            'text_email':text_email,
            'sujet':sujet, 
            'email_eleve':email_eleve, 
            'email_id': email_id }
        return render(request, 'eleves/reponse_email_eleve.html'  , context)

    return render(request, 'eleves/email_detaille.html', context)

def reponse_email_eleve(request, email_id): # email_id est envoyé par le template demande_cours_recu_eleve.html
    if request.method == 'POST' and 'btn_enr' in request.POST:
        user = request.user
        email = Email_telecharge.objects.filter(id=email_id).first()
        # messages.success(request, "Teste 03.")
        
        email_eleve = request.POST.get('email_adresse', '').strip()
        if not email_eleve: email_eleve = user.email

        # si le sujet de l'email n'est pas défini dans le GET alors sujet='Sujet non défini'
        sujet = request.POST.get('sujet', '').strip()  # Obtient la valeur de 'sujet' ou une chaîne vide
        if not sujet:  # Vérifie si sujet est nul ou une chaîne d'espaces après le strip
            sujet = "Suite à votre email"
        
        email_prof = email.email_telecharge
        # messages.success(request, f"L'email_prof: {email_prof}.")

        text_email =  request.POST['text_email']
        user_destinataire = email.user.id
        destinations = ['prosib25@gmail.com', email_prof]  # Change it to actual destinations
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
        # reponse_email_id = email_telecharge.id
        # messages.error(request, "Teste 05 ")
        # messages.success(request, f"Le contenu de l'email est enregistré dans la table Email_telecharge")
        # enregistrer du code email dans la table de gestion des email à revoire
        
        Email_suivi.objects.create(user=user, email=email_telecharge, suivi="Répondre", reponse_email_id=email_id)
        # success(request, "La réponse à l'email est enregistrée dans la table Email_suivi.")
        # Ajoutez ici le code pour gérer les enregistrements liés au professeur, si nécessaire.
        
        return redirect('compte_eleve')

    return redirect('reponse_email_eleve')