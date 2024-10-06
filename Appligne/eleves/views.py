from django.shortcuts import render, redirect, get_object_or_404 #dans le cas ou l' id du user ne correspond pas à un user
from django.contrib import messages, auth
from django.contrib.auth.models import User
from .models import Eleve, Parent, Temoignage
from accounts.models import Matiere, Niveau, Region, Departement, Email_detaille, Prix_heure, Demande_paiement, Detail_demande_paiement, Payment
from accounts.models import Demande_paiement, Detail_demande_paiement, Email_telecharge, Payment, Historique_prof, Mes_eleves, Horaire, Detail_demande_paiement
import re
from datetime import date
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.db.models import OuterRef, Subquery, DecimalField, Sum
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from django.core.validators import validate_email, EmailValidator
from django.core.exceptions import ObjectDoesNotExist, ValidationError






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
    if not user.is_authenticated or not hasattr(user, 'eleve'):
        messages.error(request, "Vous devez être connecté pour effectuer cette action.")
        return redirect('signin')
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
    user = request.user  # Obtient l'utilisateur actuellement connecté
    if not user.is_authenticated or not hasattr(user, 'eleve'):
        messages.error(request, "Vous devez être connecté pour effectuer cette action.")
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








def demande_cours_eleve(request):
    # Paramètres par défaut
    # Récupère l'ancienne valeur de la région à partir de la session
    # la valeur de la session par défaut est 'Paris'
    region_ancien = request.session.get('region_ancien', 'PARIS')
    focus_departement = False
    matiere_defaut = "Maths"
    niveau_defaut = "Terminale Générale"
    region_defaut = "ILE-DE-FRANCE"
    departement_defaut = "PARIS"
    radio_name = "a_domicile"
    radio_name_text = "Cours à domicile"
    # Dans Django ORM, une sous-requête est souvent utilisée pour effectuer des requêtes complexes 
    # qui impliquent des relations entre différents modèles. Ici, prix_heure_subquery est utilisée 
    # pour récupérer le prix par heure (prix_heure) des professeurs (utilisateurs) qui correspondent à 
    # certains critères de recherche (matière, niveau et format de cours).
    # La sous-requête prix_heure_subquery est ensuite utilisée dans une requête principale pour 
    # annoter chaque professeur avec leur prix par heure pour les critères spécifiés.
    # pour correspondre au nom de l'annotation utilisée dans la vue. Cela permettra d'afficher correctement le prix par heure pour chaque professeur.
    prix_heure_subquery = Prix_heure.objects.filter( 
        user=OuterRef('pk'),
        prof_mat_niv__matiere__matiere=matiere_defaut,
        prof_mat_niv__niveau__niveau=niveau_defaut,
        format=radio_name_text
    ).values('prix_heure')

    # Utilisez filter au lieu de all pour exclure les utilisateurs sans enregistrement dans Professeur
    # Récupère les professeurs filtrés en fonction des paramètres par défaut
    # Utilise prefetch_related pour optimiser les requêtes SQL et éviter les requêtes multiples
    professeurs = User.objects.filter(
        professeur__isnull=False,
        prof_mat_niv__matiere__matiere=matiere_defaut,
        prof_mat_niv__niveau__niveau=niveau_defaut,
        prof_zone__commune__departement__departement=departement_defaut,
        **{f'format_cour__{radio_name}': True}, # Utilisation de **f'string'__{} pour construire dynamiquement le nom du paramètre
    ).annotate(
        annotated_prix_heure=Subquery(prix_heure_subquery[:1], output_field=DecimalField()) 
        # La méthode annotate est utilisée pour ajouter une annotation prix_heure au QuerySet des professeurs.
        # Cette annotation inclut la première valeur correspondante de prix_heure pour chaque professeur.
        # Cette modification permet d'inclure les valeurs prix_heure dans le QuerySet des professeurs 
        # et les rend accessibles dans le contexte passé au template.
    ).prefetch_related(
        'experience_set',
        'prof_mat_niv_set',
        'diplome_set',
        'professeur',
        'pro_fichier'
    ).distinct().order_by('id')
    
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
            radio_name_text = "Cours à domicile" # pour le filtre de Prix_heure
            radio_name = "a_domicile"
        if request.POST.get('webcam', None):
            radio_name = "webcam"
            radio_name_text = "Cours par webcam"
        if request.POST.get('stage', None):
            radio_name = "stage"
            radio_name_text = "Stage pendant les vacances"
        if request.POST.get('stage_webcam', None):
            radio_name = "stage_webcam"
            radio_name_text = "Stage par webcam"
    
    # Dans Django ORM, une sous-requête est souvent utilisée pour effectuer des requêtes complexes 
        # qui impliquent des relations entre différents modèles. Ici, prix_heure_subquery est utilisée 
        # pour récupérer le prix par heure (prix_heure) des professeurs (utilisateurs) qui correspondent à 
        # certains critères de recherche (matière, niveau et format de cours).
        # La sous-requête prix_heure_subquery est ensuite utilisée dans une requête principale pour 
        # annoter chaque professeur avec leur prix par heure pour les critères spécifiés.
        # pour correspondre au nom de l'annotation utilisée dans la vue. Cela permettra d'afficher correctement le prix par heure pour chaque professeur.
        prix_heure_subquery = Prix_heure.objects.filter( 
            user=OuterRef('pk'),
            prof_mat_niv__matiere__matiere=matiere_defaut,
            prof_mat_niv__niveau__niveau=niveau_defaut,
            format=radio_name_text
        ).values('prix_heure')

        # Utilisez filter au lieu de all pour exclure les utilisateurs sans enregistrement dans Professeur
        # Récupère les professeurs filtrés en fonction des paramètres par défaut
        # Utilise prefetch_related pour optimiser les requêtes SQL et éviter les requêtes multiples
        professeurs = User.objects.filter(
            professeur__isnull=False,
            prof_mat_niv__matiere__matiere=matiere_defaut,
            prof_mat_niv__niveau__niveau=niveau_defaut,
            prof_zone__commune__departement__departement=departement_defaut,
            **{f'format_cour__{radio_name}': True}, # Utilisation de **f'string'__{} pour construire dynamiquement le nom du paramètre
        ).annotate(
            annotated_prix_heure=Subquery(prix_heure_subquery[:1], output_field=DecimalField()) 
            # La méthode annotate est utilisée pour ajouter une annotation prix_heure au QuerySet des professeurs.
            # Cette annotation inclut la première valeur correspondante de prix_heure pour chaque professeur.
            # Cette modification permet d'inclure les valeurs prix_heure dans le QuerySet des professeurs 
            # et les rend accessibles dans le contexte passé au template.
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
        if not (request.method == 'POST' and 'btn_enr' in request.POST):
            return render(request, 'eleves/demande_cours_envoie.html', context)
        
        # si non c'est le cas de : (request.method == 'POST' and 'btn_enr' in request.POST)
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
            # vider la session
            # Supprimer les données spécifiques de la session
            if 'radio_name' in request.session:
                del request.session['radio_name']
            if 'radio_name_text' in request.session:
                del request.session['radio_name_text']
            if 'matiere_defaut' in request.session:
                del request.session['matiere_defaut']
            if 'niveau_defaut' in request.session:
                del request.session['niveau_defaut']
            if 'region_defaut' in request.session:
                del request.session['region_defaut']
            if 'departement_defaut' in request.session:
                del request.session['departement_defaut']
            return redirect('compte_eleve')
            
        messages.error(request, "Il faut définir le contenu de l'Email")
        return render(request, 'eleves/demande_cours_envoie.html', context)
    messages.error(request, "Vous devez être connecté pour effectuer cette action.")
    return redirect('signin')


def email_recu(request):
    # Vérification si l'utilisateur est connecté
    if not request.user.is_authenticated:
        messages.error(request, "Vous devez être connecté pour accéder à cette page.")
        return redirect('signin')
    
    user_id = request.user.id

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
    email = Email_telecharge.objects.filter(id=email_id).first() # l'email envoyé par le prof et  reçu par l'élève
    id_eleve = email.user_destinataire # ID de l'élève
    id_prof = email.user.id
    user = User.objects.filter(id=id_eleve).first() # User lié à l'élève
    context={
        'email':email,
    }
    if 'btn_ignorer' in request.POST:
        # Mettre à jour les champs de l'email reçu
        email.suivi = 'Mis à côté'
        email.date_suivi = date.today()
        email.save() 
        messages.success(request, "L'email est enregistré en tant qu'email ignoré.")
        return redirect('email_recu')
    if 'btn_confirmer' in request.POST:
        sujet = "Confirmation de réception"
        text_email =  f"""
J'ai bien reçu votre email
Date de réception:{email.date_telechargement}
Sujet de l'émail: {email.sujet}
Contenu de l'émail:
{email.text_email}
"""
        email_prof = email.user.email
        email_eleve = user.email
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
        messages.success(request, "Le contenu de l'email est enregistré dans le compte du professeur")
        return redirect('email_recu')
    
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

    return render(request, 'eleves/email_detaille.html', context)

def reponse_email_eleve(request, email_id): # email_id est envoyé par le template demande_cours_recu_eleve.html
    
    text_email = request.session.get('text_email',None)
    sujet = request.session.get('sujet',None)
    email_eleve = request.session.get('email_eleve',None)
    email_id = request.session.get('email_id',None)
    if not email_id: # donc la réponse est déjà effectuée puisque la session est vide
        messages.error(request, 'La réponse à cet email est déjà effectuée')
        return redirect('email_recu')
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
            messages.error(request, "L'adresse email de l'élève est invalide.")
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
        messages.success(request, "Le contenu de l'email est enregistré dans le compte du professeur")

        # vider les paramètres de la session email
        if 'text_email' in request.session:
            del request.session['text_email']
        if 'sujet' in request.session:
            del request.session['sujet']
        if 'email_eleve' in request.session:
            del request.session['email_eleve']
        if 'email_id' in request.session:
            del request.session['email_id']
        return redirect('compte_eleve')
    
    return render(request, 'eleves/reponse_email_eleve.html', context)



def demande_paiement_recu(request):
    user = request.user  # Utilisateur actuel (élève), enregistrement élève dans la table User
    if not user.is_authenticated or not hasattr(user, 'eleve'):
        messages.error(request, "Vous devez être connecté pour effectuer cette action.")
        return redirect('signin')
    eleve = Eleve.objects.filter(user=user).first()  # Enregistrement de l'élève dans la table Eleve
    mon_eleve = Mes_eleves.objects.filter(eleve=eleve).first()
    
    # Récupérer toutes les demandes de paiement liées à cet élève via les professeurs actifs
    demandes_paiement_recues = Demande_paiement.objects.filter(
        statut_demande='En attente', # seul l'état en atternt est accepté
        mon_eleve__eleve=eleve, # ID de l'enregistrement dans la table Mes_eleves doit correspondre à mon_eleve de dermande_paiement,  fait référence à l'élève lié à l'objet Mes_eleves dans la relation ForeignKey.
        mon_eleve__is_active=True, # L'objet mon_eleve lié à la table mes_eleves est activé
        payment_id=None # la demande de paiement n'est pas réglée
    )

    if request.method == 'POST':
        detaille_enr_key = next((key for key in request.POST if key.startswith('btn_detaille_')), None)
        if detaille_enr_key:
            demande_paiement_id = int(detaille_enr_key.split('btn_detaille_')[1])
            try:
                demande_enr = Demande_paiement.objects.get(id=demande_paiement_id)
                return redirect('detaille_demande_paiement_recu', demande_paiement_id=demande_enr.id)
            except Demande_paiement.DoesNotExist:
                messages.error(request, f"La demande de paiement avec l'ID={demande_paiement_id} n'a pas été trouvée.")

    

    return render(request, 'eleves/demande_paiement_recu.html', {'demandes_paiement_recues': demandes_paiement_recues})


def detaille_demande_paiement_recu(request, demande_paiement_id):
    user = request.user
    if not user.is_authenticated or not hasattr(user, 'eleve'):
        messages.error(request, "Vous devez être connecté pour effectuer cette action.")
        return redirect('signin')

    demande_paiement = get_object_or_404(Demande_paiement, id=demande_paiement_id)

    if not demande_paiement.vue_le: # pour informer le prof que l'élève a vue la demande de paiement
        demande_paiement.vue_le = timezone.now()
        demande_paiement.save()

    prof = demande_paiement.user
    detail_demande_paiements = Detail_demande_paiement.objects.filter(demande_paiement=demande_paiement)

    cours_declares = []
    cours_ids = set()
    for enr in detail_demande_paiements:
        if enr.cours.id not in cours_ids:
            cours_declares.append({'cours': enr.cours})
            cours_ids.add(enr.cours.id)

    detaille_declares = [
        {'enr': enr, 'montant': round(enr.horaire.duree * enr.prix_heure, 2)}
        for enr in detail_demande_paiements
    ]

    email = Email_telecharge.objects.filter(id=demande_paiement.email).first()
    email_eleve = Email_telecharge.objects.filter(id=demande_paiement.email_eleve).first()

    context = {
        'demande_paiement': demande_paiement, # demande de paiement envoyée par le prof
        'cours_declares': cours_declares, # liste des cours déclarés dans la demande de paiement du prof
        'detaille_declares': detaille_declares, # liste des détailles horaires de chaque cours déclaré
        'email': email, # Email lié à la demande de paiement envoyé par le prof 
        'email_eleve': email_eleve, # l'email de  l'élève en réponse à la demande de paiement (donnée en plus non utilisée dans le template)
    }

    if request.method == 'POST':
        if 'btn_contester' in request.POST:
            return handle_contestation(request, context, user, prof, email, demande_paiement)
        elif 'btn_reglement' in request.POST:
            # Avant de passer à l'enregistrement il faut tester la coformité des enregistrement horaires
            # il faux que tous les enregistrement horaire liés à la demande de paiement sont non 'Annuler' non réglés
            horaires = Horaire.objects.filter(demande_paiement_id=demande_paiement.id)
            i=0
            for horaire in horaires:
                if horaire.statut_cours == 'Annuler' or horaire.payment_id != None:
                    messages.error(request, f" L'enregistrement horaire.payment_id = {horaire.payment_id}, horaire.statut_cours= {horaire.statut_cours} Dans la table Horaires <br> est déjà réglé, et / ou annulé <br> voire avec le programmeur.")
                    i+=1
            if i>0: return render(request, 'eleves/detaille_demande_paiement_recu.html', context) # si un enregistrement est non valide
            return handle_reglement(request, demande_paiement, prof, user) # si non tous les condition de validation sont vraies

    return render(request, 'eleves/detaille_demande_paiement_recu.html', context)


### Points de rationalisation par ChatGPT:
# 1. **Séparation des responsabilités** : J'ai déplacé la logique de traitement des contestations et des règlements dans des fonctions séparées (`handle_contestation` et `handle_reglement`) pour rendre le code principal plus lisible.
# 2. **Réduction de la duplication** : Le calcul des montants et la gestion des emails ont été simplifiés et intégrés dans des boucles ou des fonctions logiques.
# 3. **Optimisation des requêtes** : L'utilisation de `get_or_create` pour le `Historique_prof` évite des requêtes supplémentaires si un enregistrement existe déjà.
# 4. **Gestion des erreurs** : Les blocs `try-except` ont été conservés et isolés pour gérer spécifiquement les erreurs d'envoi d'email.
# Cela rend le code plus modulaire, facile à maintenir et améliore la lisibilité globale.

def handle_contestation(request, context, user, prof, email, demande_paiement):
    sujet_contestation = request.POST.get('sujet_contestation')
    text_email_contestation = request.POST.get('text_email_contestation')

    if not sujet_contestation or not text_email_contestation:
        messages.error(request, "Il faut désigner l'objet de la contestation et son contenu.")
        return render(request, 'eleves/detaille_demande_paiement_recu.html', context) # revenir à la même page

    destinations =['prosib25@gmail.com', prof.email]
    # Validation des emails dans destinations
    email_validator = EmailValidator() # Initialiser le validateur d'email
    for destination in destinations:
        try:
            email_validator(destination)
        except ValidationError:
            messages.error(request, f"L'adresse email du destinataire {destination} est invalide.<br>Veuillez vérifier l'adresse avec le professeur.")
    try:
        send_mail(
            sujet_contestation,
            text_email_contestation,
            user.email,
            destinations,
            fail_silently=False
        )
        messages.success(request, "L'email a été envoyé avec succès.")
    except Exception as e:
        messages.error(request, f"Une erreur s'est produite lors de l'envoi de l'email : {str(e)}")

    email_telecharge = Email_telecharge.objects.create(
        user=user,
        email_telecharge=user.email,
        text_email=text_email_contestation,
        user_destinataire=prof.id,
        sujet=sujet_contestation,
        suivi='Répondu',
        reponse_email_id=email.id if email else None
    )

    # mise à jour Demande de paiement
    demande_paiement.statut_demande = 'Contester'
    demande_paiement.email_eleve = email_telecharge.id
    demande_paiement.save()

    messages.success(request, "La demande de paiement a été mise à jour avec le statut 'contestée'.")
    return redirect('compte_eleve')


def handle_reglement(request, demande_paiement, prof, user):

    # création enregistrement payment (à réviser)
    payment = Payment.objects.create(
        status='Approuvé',
        model="demande_paiement",
        model_id=demande_paiement.id,
        slug=f"Dd{demande_paiement.id}Prof{prof.id}Elv{user.id}",
        reference=demande_paiement.id,
        expiration_date=timezone.now(),
        amount=demande_paiement.montant,
        currency="Euro",
        language="Français",
        payment_register_data=f"PP_d{demande_paiement.id}"
    )

    # mise à jour Demande_paiement
    demande_paiement.payment_id = payment.id # le paiement est réalisé
    demande_paiement.statut_demande = "Réaliser"
    demande_paiement.save()

    # Mise à jour Horaires
    horaires = Horaire.objects.filter(demande_paiement_id=demande_paiement.id)
    for horaire in horaires:
        horaire.payment_id = payment.id
        horaire.save()
    
    # mise à jour de l'historique
    update_historique_prof(prof, demande_paiement, user)

    messages.success(request, "La demande de paiement a été mise à jour avec le statut 'Réaliser'.")
    return redirect('compte_eleve')



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
    if nb_reglement_eleve == 1 and not created:  # Si c'est le premier règlement réalisé pour cet élève 
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
    # Récupération de l'utilisateur connecté
    user = request.user
    if not user.is_authenticated or not hasattr(user, 'eleve'):
        messages.error(request, "Vous devez être connecté pour effectuer cette action.")
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











