from django.shortcuts import render, redirect, get_object_or_404, HttpResponseRedirect
from django.contrib import messages, auth
from django.contrib.auth.models import User
from .models import Professeur, Diplome, Experience, Format_cour, Matiere  , Niveau, Prof_mat_niv, Departement, Region, Commune, Prof_zone, Pro_fichier, Prof_doc_telecharge, Diplome_cathegorie, Pays, Experience_cathegorie, Matiere_cathegorie
from .models import Email_telecharge, Email_detaille, Prix_heure, Mes_eleves, Cours, Eleve, Horaire, Demande_paiement, Detail_demande_paiement, Historique_prof, Payment
from datetime import date, datetime
# from datetime import timedelta
from django.http import JsonResponse
from django.core.mail import send_mail
from django.core.validators import validate_email, EmailValidator
from django.core.files.base import ContentFile
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.conf import settings
from django.utils import timezone
# from django.utils import formats
from django.contrib.auth.hashers import make_password
# from django.contrib.auth.hashers import  check_password
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django.urls import reverse
from googleapiclient.discovery import build
from decouple import config
from eleves.models import Eleve, Parent, Temoignage
from django.db.models import F, Value, CharField
from django.db.models import F, Value, CharField
from django.db.models import Func
from django.db.models import Sum, F, ExpressionWrapper, DurationField, FloatField, fields, DecimalField
from django.db.models.functions import Concat
from django.contrib.auth.password_validation import validate_password

import re
import os
import requests # pour utiliser des API (voire nouveau_compte_prof, mot de passe)
import hashlib # convertir le suffixe en une chaîne d'octets

def is_password_compromised(password):
    # Hash du mot de passe en SHA-1
    hashed_password = hashlib.sha1(password.encode('utf-8')).hexdigest()
    # Préfixe du hash (5 premiers caractères)
    hash_prefix = hashed_password[:5]
    # URL de l'API Have I Been Pwned
    url = f"https://api.pwnedpasswords.com/range/{hash_prefix}"
    # Requête GET à l'API
    response = requests.get(url)
    # Vérification de la réponse
    if response.status_code == 200:
        # Séparation des réponses par ligne
        hashes = response.text.splitlines()
        # Vérification si le suffixe du hash est présent dans les réponses
        suffix = hashed_password[5:].upper()
        for h in hashes:
            if suffix in h:
                return True
    # Si le suffixe n'est pas trouvé, le mot de passe n'est pas compromis
    return False



def nouveau_compte_prof(request):
    # Initialiser les variables
    user_nom = request.POST.get('user_nom', '')
    mot_pass = request.POST.get('mot_pass', '')
    conf_mot_pass = request.POST.get('conf_mot_pass', '')
    civilite = request.POST.get('civilite', None)
    prenom = request.POST.get('prenom', '')
    nom = request.POST.get('nom', '')
    adresse = request.POST.get('adresse', '')
    email = request.POST.get('email', '')
    phone = request.POST.get('phone', '')
    date_naiss = request.POST.get('date_naiss', '')
    photo = request.FILES.get('photo', None)  # Photo peut être None si non fournie
    teste = True
    # Vérification de la photo
    if not photo:
        default_photo_path = os.path.join(settings.BASE_DIR, 'static/img/favicon.png')
        try:
            with open(default_photo_path, 'rb') as f:
                photo_data = f.read()
                photo_file = ContentFile(photo_data, name='favicon.png')
                photo = photo_file
        except IOError:
            messages.error(request, "Fichier par défaut introuvable.")

    if 'btn_enr' in request.POST:
        # Validation du nom d'utilisateur
        if User.objects.filter(username=user_nom).exists():
            messages.error(request, "Le nom de l'utilisateur est déjà utilisé.")
            teste = False
        if not user_nom.strip():
            messages.error(request, "Le nom de l'utilisateur ne peut pas être vide.")
            teste = False

        # Validation du mot de passe
        if not mot_pass:
            messages.error(request, "Le mot de passe ne peut pas être vide.")
            teste = False
        elif mot_pass != conf_mot_pass:
            messages.error(request, "La confirmation du mot de passe ne correspond pas.")
            teste = False
        else:
            try:
                validate_password(mot_pass)
            except ValidationError as e:
                for error in e:
                    messages.error(request, error)
                teste = False

        # Validation de l'email
        if email:
            try:
                validate_email(email)
            except ValidationError:
                messages.error(request, "Le format de l'email est incorrect.")
                teste = False
            if User.objects.filter(email=email).exists():
                messages.error(request, "Cet email est déjà utilisé.")
                teste = False

        # Validation de la date de naissance
        if date_naiss:
            try:
                date_naiss = datetime.strptime(date_naiss, '%d/%m/%Y')
            except ValueError:
                messages.error(request, "Le format de la date de naissance est incorrect.")
                teste = False

        # Vérification si tout est valide
        if teste:
            user = User.objects.create_user(
                first_name=prenom,
                last_name=nom,
                email=email,
                username=user_nom,
                password=mot_pass,
                is_active=True
            )
            user.save()

            professeur = Professeur(
                user=user,
                adresse=adresse,
                numero_telephone=phone,
                civilite=civilite,
                photo=photo
            )
            professeur.set_date_naissance_from_str(request.POST['date_naiss'])
            professeur.save()

            auth.login(request, user)
            messages.success(request, "Enregistrement réussi.")
            diplome_cathegories = Diplome_cathegorie.objects.all()
            return render(request, 'accounts/nouveau_diplome.html', {'diplome_cathegories': diplome_cathegories})
    # Contexte initial
    context = {
        'user_nom': user_nom,
        'mot_pass': mot_pass,
        'conf_mot_pass': conf_mot_pass,
        'civilite': civilite,
        'prenom': prenom,
        'nom': nom,
        'adresse': adresse,
        'email': email,
        'phone': phone,
        'date_naiss': date_naiss,
        'photo': photo,
    }
    return render(request, 'accounts/nouveau_compte_prof.html', context)

def nouveau_diplome(request):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin')

    diplome_cathegories = Diplome_cathegorie.objects.all()

    context = {'diplome_cathegories': diplome_cathegories}
    if not request.method == 'POST' or not 'btn_enr' in request.POST:
        return render(request, 'accounts/nouveau_diplome.html', context)
    if 'btn_enr' in request.POST:
        # Liste des diplômes dans le request dont le nom commence par: diplome_
        diplome_keys = [key for key in request.POST.keys() if key.startswith('diplome_')]
        if not diplome_keys:
            messages.error(request, "Il faut donner au moins un diplôme")
            return render(request, 'accounts/nouveau_diplome.html', context)
        else:
            for i in range(1, len(diplome_keys) + 1): # il faut ajouter une logique d'analyse pour confirmer l'enregistrement final par message.success
                # Récupération des valeurs du formulaire
                diplome_key = f'diplome_{i}'
                date_obtenu_key = f'date_obtenu_{i}'
                principal_key = f'principal_{i}'
                intitule_key = f'intitule_{i}'
                autre_diplome_key = f'autre_diplome_{i}' # champ réservé pour les diplomes qui ne figure pas dans la liste
                if request.POST.get(diplome_key):
                    diplome = request.POST.get(diplome_key)
                    if diplome == 'Autre':
                        autre_diplome = request.POST.get(autre_diplome_key)
                        if autre_diplome != '' and autre_diplome != 'Autre':
                            # Vérification si le diplôme "Autre" n'existe pas déjà pour le pays France
                            diplome_autre_exists = Diplome_cathegorie.objects.filter(nom_pays__nom_pays='France', dip_cathegorie=autre_diplome).exists()
                            if not diplome_autre_exists:
                                # Récupération de l'objet Pays France
                                pays_france = Pays.objects.get(nom_pays='France')
                                # Création d'un nouvel enregistrement dans Diplome_cathegorie pour le diplôme "Autre"
                                diplome_autre = Diplome_cathegorie.objects.create(nom_pays=pays_france, dip_cathegorie=autre_diplome)
                                diplome_autre.save()
                                diplome = autre_diplome
                            else: # le diplome ajouté existe déjà dans la table diplome_cathegorie
                                diplome = autre_diplome
                        else:
                            messages.error(request, "Le diplôme 'Autre' ne peut pas être vide ou égal à 'Autre'.")

                    # Requête pour récupérer l'objet Diplome_cathegorie
                    diplome_obj = Diplome_cathegorie.objects.get(dip_cathegorie=diplome)
                    # Récupérer l'ID de l'objet Diplome_cathegorie
                    diplome_cathegorie_id = diplome_obj.id
                    date_obtenu = request.POST.get(date_obtenu_key, None)
                    if request.POST.get(principal_key, None) == "on":
                        principal = True
                    else: principal = False
                    intitule = request.POST.get(intitule_key, None)

                        # Vérification si le diplôme n'existe pas déjà pour cet utilisateur
                    if not Diplome.objects.filter(user=user, diplome_cathegorie_id=diplome_cathegorie_id, intitule=intitule).exists():
                        if date_obtenu:
                            # il faut tester le format de date_obtenu
                            try:
                                    # si la convertion est réussie
                                    date_obtenu_01 = datetime.strptime(date_obtenu, '%d/%m/%Y')
                            except ValueError:
                                messages.error(request, f"Format de la date: {date_obtenu}, est invalide. Utilisez jj/mm/aaaa")
                                return render(request, 'accounts/nouveau_diplome.html', context)
                                
                            diplome_instance = Diplome(user=user, diplome_cathegorie_id=diplome_cathegorie_id, intitule=intitule, principal=principal)
                            diplome_instance.set_date_obtenu_from_str(date_obtenu)
                            diplome_instance.save()
                        else:
                            messages.error(request, f"Erreur liée à la date d'obtention du diplôme {diplome}")
                            return render(request, 'accounts/nouveau_diplome.html', context)
                    else:  messages.warning(request, f"Le diplôme '{diplome}' : '{intitule}' , existe déjà pour cet utilisateur.")
                else:
                    # erreur à dépasser
                    messages.error(request, f"Erreur liée au diplôme {i}")
        # Rendre la réponse en utilisant le template 'pages/index.html'
        response = render(request, 'accounts/nouveau_experience.html') # ?.??
        # Ajouter les en-têtes pour empêcher la mise en cache de la page
        # Cela garantit que le navigateur récupère toujours les données les plus récentes
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # HTTP 1.1.
        response['Pragma'] = 'no-cache'  # HTTP 1.0.
        response['Expires'] = '0'  # Proxies.
        # Retourner la réponse
        return response



def nouveau_experience(request):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin')
    
    if 'btn_enr' in request.POST:
        # Liste des expériences dans le request dont le nom commence par: type_
        type_keys = [key for key in request.POST.keys() if key.startswith('type_')]
        if not type_keys: # s'il n'y a pas d'expérience sélectionnée
            messages.error(request, "Il faut donner au moins une expérience, sinon sélectionnez Débutant(e)")
            return render(request, 'accounts/nouveau_experience.html')
        else: # s'il y a au mois une expérience sélectionnée
            for i in range(1, len(type_keys) + 1):
                # Récupération des valeurs du formulaire
                # Définir les paramaitres
                type_key = f'type_{i}'
                # car il y a deux dates avec des indice différents paire et impaire (voire function ReOrderId02() dans Appligne/static/js/Code_en_plus.js)
                date_debut_key = f'date_debut_{2 * i - 1}'
                date_fin_key = f'date_fin_{2 * i}'
                principal_key = f'principal_{i}'
                actuellement_key = f'act_{i}'
                Commentaire_key = f'comm_{i}'

                if request.POST.get(type_key): # car dans le JS de la page on a réodonner les ID
                    debut = request.POST.get(date_debut_key, None)
                    fin = request.POST.get(date_fin_key, None)
                    
                    type = request.POST.get(type_key)
                    commentaire = request.POST.get(Commentaire_key, None)
                    if request.POST.get(principal_key, None) == "on":
                        principal = True
                    else: principal = False
                    if request.POST.get(actuellement_key, None) == "on":
                        actuellement = True
                    else: actuellement = False
                    # Vérification si le type d'expérience n'existe pas déjà pour cet utilisateur
                    if not Experience.objects.filter(user=user, type=type, commentaire=commentaire).exists():
                        if debut:
                            # tester le format des dates
                            try:
                                # si la convertion est réussie
                                debut_01 = datetime.strptime(debut, '%d/%m/%Y') # debut_01 juste pour le try seulement
                                if fin: fin_01 = datetime.strptime(fin, '%d/%m/%Y') # fin_01 juste pour le try seulement
                            except ValueError:
                                messages.error(request, "Format de l'un des dates est invalide. Utilisez jj/mm/aaaa")
                                return render(request, 'accounts/nouveau_experience.html')
                            experience_instance = Experience(user=user, type=type, commentaire=commentaire, principal=principal, actuellement=actuellement)
                            experience_instance.set_date_debut_from_str(debut)
                            experience_instance.set_date_fin_from_str(fin)
                            experience_instance.save()
                        else: # on peut définir par défaut date début ou rendre date début non obligatoire
                            debut = datetime.now().strftime('%d/%m/%Y')
                            experience_instance = Experience(user=user, type=type, commentaire=commentaire, principal=principal, actuellement=actuellement)
                            experience_instance.set_date_debut_from_str(debut)
                            experience_instance.set_date_fin_from_str(fin)
                            experience_instance.save()
                            return render(request, 'accounts/nouveau_experience.html')
                        
                    else: continue # on passe au type d'expérience suivant s'il y en a

                else: continue # on passe au type d'expérience suivant s'il y en a

            return redirect('nouveau_matiere')

    return render(request, 'accounts/nouveau_experience.html')



def nouveau_matiere(request):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin')

    # Vérifie si la méthode de la requête est POST et si le bouton 'btn_enr' a été soumis
    if 'btn_enr' in request.POST:

        # Récupérer les listes de matières et de niveaux sélectionnés dans le formulaire
        liste_matieres = [key for key in request.POST.keys() if key.startswith('matiere_')]
        liste_niveaux = [key for key in request.POST.keys() if key.startswith('niveau_chx_')]
        
        # Vérifier si au moins une matière et ses niveaux correspondants ont été sélectionnés
        if not liste_matieres or not liste_niveaux:
            messages.error(request, "Il faut sélectionner au moins une matière à enseigner et les niveaux correspondants")
            return render(request, 'accounts/nouveau_matiere.html')

        # Parcourir chaque matière sélectionnée
        for matiere_key in liste_matieres:
            # extraire l'indice de la matière
            # renvoie la partie de la chaîne matiere_key qui commence après le préfixe 'matiere_'
            i = int(matiere_key[len('matiere_'):])
            # récupérer la valeur du clé 'matiere_{i}'
            matiere = request.POST.get(f'matiere_{i}')
            # Récupérer l'objet Matiere correspondant à la matière sélectionnée
            matiere_obj = Matiere.objects.filter(matiere=matiere).first()
            
            # Vérifier si la matière existe dans la base de données
            if not matiere_obj:
                messages.error(request, f"Matière = '{matiere}' non trouvée. Contactez l'administrateur du site")
                return render(request, 'accounts/nouveau_matiere.html')
            
            matiere_id = matiere_obj.id
            # Vérifier si la case à cocher 'principal' est cochée
            # si request.POST.get(f'principal_{i}') == "on" => principal=True
            # si non => principal=False
            principal = request.POST.get(f'principal_{i}') == "on"
            
            # Récupérer les niveaux sélectionnés pour cette matière
            niveau_chx = request.POST.getlist(f'niveau_chx_{i}')
            # Remarque: Si niveau_chx est vide le reste du code est ignoré
            if not niveau_chx: 
                messages.error(request, f"La matière = '{matiere}' n'a pas de niveaux sélectionnés, elle n'est pas prise en compte")
                # passer à la matière suivante
                continue
            # pour le cas si niveau_chx est non null
            niveaux_id = [] # initialiser la liste niveaux_id
            
            # Parcourir chaque niveau sélectionné
            for niveau_name in niveau_chx:
                try: 
                    # Récupérer l'objet Niveau correspondant au niveau sélectionné
                    niveau_obj = Niveau.objects.get(niveau=niveau_name)
                    niveaux_id.append(niveau_obj.id)
                except Niveau.DoesNotExist:
                    messages.error(request, f"Niveau = '{niveau_name}' non trouvé. Contactez l'administrateur du site")
                    return render(request, 'accounts/nouveau_matiere.html')
            
            # Sauvegarder les enregistrements Prof_mat_niv pour chaque niveau sélectionné
            for niveau_id in niveaux_id:
                
                # pour les filtres on utilise la valeur des ID (matiere_id ; niveau_id))
                # si l'enregistrement n'existe pas
                if not Prof_mat_niv.objects.filter(user=user, matiere=matiere_id, niveau=niveau_id).exists():
                    niveau_obj = Niveau.objects.get(id=niveau_id)
                    # pour l'enregistrement on utilise les objets liés aux ID (matiere_obj ; niveau_obj)
                    prof_mat_niv = Prof_mat_niv(user=user, matiere=matiere_obj, niveau=niveau_obj, principal=principal)
                    prof_mat_niv.save()

                else:
                    continue # passer au suivant niveau si l'enregistrement existe déjà
        # Rediriger vers une autre page après traitement
        messages.success(request, " L'enregistrement des matières et des niveaux sélectionnés est achevé avec succès")
        return redirect('nouveau_zone')

    return render(request, 'accounts/nouveau_matiere.html')


    
def nouveau_zone(request):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin') 


    btn_text = "Enregistrez les zones"  # Texte par défaut du bouton
    if 'btn_enr' in request.POST:
        # Récupérer les listes des communes du GET sélectionnées dans le deuxième select name="communes_chx"
        liste_communes = request.POST.getlist('communes_chx')
        if not liste_communes:
            messages.error(request, "Pas de commune")
            return render(request, 'accounts/nouveau_zone.html')
        for commune in liste_communes:
            # il faut extraire les ID à par et les commune à par car value= id_commune
            # Extraction de l'id de la commune et du texte de la commune
            commune_id, commune_text = commune.split('_')
            # pour les filtres on utilise la valeur des ID (matiere_id ; niveau_id))
                
            # si l'enregistrement n'existe pas
            if not Commune.objects.filter(id=commune_id).exists():
                messages.error(request, f"L'ID de la  commune: '{commune_text}' n'est pas reconnue, Contactez l'administrateur")
                continue # on ignore les ID non reconnus
            if not Prof_zone.objects.filter(user=user, commune=commune_id).exists():
                commune_obj = Commune.objects.get(id=commune_id)
                # pour l'enregistrement on utilise les objets liés aux ID (matiere_obj ; niveau_obj)
                prof_zone = Prof_zone(user=user, commune=commune_obj)
                prof_zone.save()
                
                # Modifier le texte du bouton après l'enregistrement réussi
                btn_text = "Ajoutez d'autres zones"
            else:
                # messages.info(request, f"Enregistrement de la Commune  = '{commune_text}' éxiste déjà.")
                continue # passer à la suivante commune si l'enregistrement existe déjà   
        return redirect('nouveau_description')        
    return render(request, 'accounts/nouveau_zone.html', {'btn_text': btn_text})




# Ce code semble être une vue dans un framework web tel que Django. Il récupère toutes les régions 
# disponibles à partir de la base de données et les renvoie au format JSON. 
# Chaque région est représentée sous la forme d'un dictionnaire avec ses identifiants et noms.
def get_regions(request):
    # Récupère toutes les régions depuis la base de données avec leurs identifiants
    regions = Region.objects.all().values_list('id', 'region')
    
    # Crée une liste de dictionnaires contenant les identifiants et les noms de régions
    regions_list = [{'id': id, 'region': region} for id, region in regions]
    
    # Retourne la liste des régions sous forme de réponse JSON
    return JsonResponse(regions_list, safe=False)


# Ce code Python  récupère les départements associés à une région spécifique à partir
# d'une requête GET.
# Ce code est conçu pour être utilisé dans une API qui répond aux demandes GET. 
# Si l'identifiant de la région est fourni dans la requête GET, il récupère les départements 
# associés à cette région depuis la base de données et les renvoie au format JSON. Si aucun identifiant 
# de région n'est fourni, il renvoie une réponse d'erreur avec un code de statut 400.
def get_departments(request):
    # Récupère l'identifiant de la région depuis les paramètres de la requête GET
    region_id = request.GET.get('region_id')
    
    # Vérifie si l'identifiant de la région a été fourni
    if region_id is not None:
        # Récupère les départements associés à l'identifiant de la région
        departments = Departement.objects.filter(region_id=region_id).values('id', 'departement')
        # Retourne les départements sous forme de réponse JSON
        return JsonResponse(list(departments), safe=False)
    else:
        # Si l'identifiant de la région est manquant, retourne une erreur avec un code de statut 400 (Bad Request)
        return JsonResponse({'error': 'Paramètre region_id manquant'}, status=400)



# Ce code est une vue Django qui récupère les communes en fonction
#  de l'identifiant du département fourni dans la requête GET. Il retourne 
# les données des communes sous forme de réponse JSON. Si aucun identifiant 
# de département n'est fourni, il retourne une liste vide.
def get_communes(request):
    # Récupération de l'identifiant du département à partir de la requête GET
    department_id = request.GET.get('department_id')
    
    # Vérification si un identifiant de département est fourni
    if department_id:
        # Filtrage des communes basé sur l'identifiant du département et récupération des données nécessaires
        communes = Commune.objects.filter(departement_id=department_id).values('id', 'commune', 'code_postal')
        
        # Conversion des objets QuerySet en liste pour la sérialisation en JSON
        communes_list = list(communes)
        
        # Retourne les données des communes sous forme de réponse JSON
        return JsonResponse(communes_list, safe=False)
    else:
        # Retourne une liste vide si aucun département n'est sélectionné
        return JsonResponse([], safe=False)


from django.contrib import auth
from django.shortcuts import redirect, render
from django.contrib import messages
from .models import Professeur, Eleve  # Importez les modèles Professeur et Eleve

def signin(request):
    user_nom = ""
    mot_pass = ""
    if request.method == 'POST' and 'btn_enr' in request.POST:
        user_nom = request.POST['user_nom']
        mot_pass = request.POST['mot_pass']
        user = auth.authenticate(username=user_nom, password=mot_pass)
        
        if user is not None:
            # Si la case souviens_toi n'est pas cochée, la session expire à la fermeture du navigateur
            if 'souviens_toi' not in request.POST:
                request.session.set_expiry(0)
            else:
                request.session.set_expiry(1209600)  # 2 semaines

            # Authentification réussie, le user est connecté
            auth.login(request, user)

            # Vérification si l'utilisateur est un professeur
            if Professeur.objects.filter(user=user).exists():
                return redirect('compte_prof')
            
            # Vérification si l'utilisateur est un élève
            elif Eleve.objects.filter(user=user).exists():
                return redirect('compte_eleve')
            
            # Si l'utilisateur n'est ni professeur ni élève
            else: # à gérer le cas des administrateurs plus tard
                return redirect('index')  # Redirection par défaut si aucun rôle trouvé
        else:
            messages.error(request, "Le nom de l'utilisateur ou le mot de passe est invalide")
            
    return render(request, 'accounts/signin.html', {'user_nom': user_nom, 'mot_pass': mot_pass})

    

# *********************** à réviser début  ******************************************
# ******************************************************************************


# Importation de la fonction config de decouple pour récupérer les variables d'environnement depuis un fichier .env

# Récupération de la clé d'API depuis le fichier .env en utilisant la fonction config
API_KEY = config('API_KEY')

# Clé d'API YouTube
api_key = API_KEY

# Création d'une instance de l'API YouTube Data
youtube = build('youtube', 'v3', developerKey=api_key)

def get_embed_code(video_id):
    # Appel à l'API pour récupérer les détails de la vidéo
    request = youtube.videos().list(
        part='player',
        id=video_id
    )
    response = request.execute()
    
    # Vérifier si la réponse contient des éléments
    if 'items' in response and response['items']:
        # Extrait le code d'intégration de la réponse
        embed_code = response['items'][0]['player']['embedHtml']
        return embed_code
    else:
        # Gérer le cas où la réponse est vide ou ne contient pas d'élément à l'index 0
        return "Aucun code d'intégration trouvé pour cette vidéo."
# *********************** à réviser    fin  ******************************************
# ******************************************************************************

def est_url_youtube(url):
    """
    Vérifie si l'URL donnée correspond à une vidéo YouTube.
    """
    # Modèle d'URL YouTube
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')

    # Vérifie si l'URL correspond au modèle YouTube
    match = re.match(youtube_regex, url)
    if match:
        return True
    else:
        return False


def nouveau_description(request):
    titre=""
    parcours=""
    pedagogie=""
    video=""
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin')

    teste = True
    if 'btn_enr' in request.POST:
        titre  = request.POST.get('titre', "")
        # teste sur la longueur du titre
        if len(titre)>255:
            messages.error(request, "Le titre de votre fichier ne doit pas dépasser 255 caractaires.")
            teste = False
        parcours  = request.POST.get('parcours', "")
        pedagogie  = request.POST.get('pedagogie', "")
        video = request.POST.get('video_youtube_url', "")      
        # Vérifier si l'URL est une vidéo YouTube
        if video and not est_url_youtube(video):
            messages.error(request, "L'URL de la vidéo n'est pas valide.")
            teste = False
        if teste:
            if not Pro_fichier.objects.filter(user=user).exists() :
                pro_fichier = Pro_fichier(user=user, titre_fiche=titre, parcours=parcours, pedagogie=pedagogie, video_youtube_url=video)
                pro_fichier.save()
                messages.success(request, "Enregistrement de la description détaillée est achevé.")
                return redirect('nouveau_fichier')  # Rediriger vers l'étape suivante
            else:
                # supprimer l'ancien enregistrement
                ancien_enregistrement = Pro_fichier.objects.get(user=user)
                ancien_enregistrement.delete()
                # Créez un nouveau Pro_fichier avec les données mises à jour
                pro_fichier = Pro_fichier(user=user, titre_fiche=titre, parcours=parcours, pedagogie=pedagogie, video_youtube_url=video)
                pro_fichier.save()
                messages.success(request, "Enregistrement de la description détaillée est modifié avec succés.")
                return redirect('nouveau_fichier')  # Rediriger vers l'étape suivante
    context={
        'titre': titre,
        'parcours': parcours,
        'pedagogie': pedagogie,
        'video': video,
    }
    return render(request, 'accounts/nouveau_description.html', context)

def nouveau_fichier(request):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin')

    email_prof = request.POST.get('email_user', "").strip()
    text_email = request.POST.get('text_email', "").strip()
    fichiers_list = request.FILES.getlist('fichiers_list', None)
    sujet = request.POST.get('sujet', '').strip()
    extensions_images = ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.raw', '.psd', '.ai',
                                '.exif', '.jfif', '.jpe', '.heif', '.heic']
    teste = True
    if fichiers_list:
        for fichier in fichiers_list:
            nom_fichier = fichier.name
            # Obtenez l'extension du fichier
            extension_fichier = os.path.splitext(nom_fichier)[1].lower()
            if not extension_fichier in extensions_images:
                messages.error(request, f"Le fichier '{nom_fichier}' n'est pas une image valide et n'a pas été enregistré.")
                messages.error(request, "Les extensions des fichiers acceptés sont: .jpg, .jpeg, .png, .bmp, .webp, .raw, .psd, .ai,.exif, .jfif, .jpe, .heif, .heic ")
                teste = False # si erreur l'enregistrement ne passera pas voire reste de code
    if 'btn_enr' in request.POST and teste:
        if text_email:
            if not email_prof:
                email_prof = user.email # si l'utilisateur n'a pas spécifié son email, l'email de l'utiluisateur déjà enregistré est pris par défaut
            #tester le format de l'email
            email_validator = EmailValidator() # Initialiser le validateur d'email
            # Validation de l'email_prof
            try:
                email_validator(email_prof)
            except ValidationError:
                email_prof = user.email # si le format de l'email est éronné on reprond l'email du user

            # Sélectionner le premier enregistrement des superusers qui est dans ce cas le destinataire de l'Email
            user_destinataire = User.objects.filter(is_staff=1, is_active=1, is_superuser=1).first()
            user_destinataire_id = user_destinataire.id
            
            # traitement de l'envoie de l'email
            # si le sujet de l'email n'est pas défini dans le GET alors sujet='Sujet non défini'
            if not sujet:  # Vérifie si sujet est nul ou une chaîne d'espaces après le strip
                sujet = "Sujet non défini"
            # on peut ajouter d'autres destinations: destinations = ['prosib25@gmail.com', 'autre_adresse_email']
            destinations = ['prosib25@gmail.com']
            # L'envoie de l'email n'est pas obligatoire
            # try:
            #     send_mail(
            #         sujet,
            #         text_email,
            #         email_prof,
            #         destinations,
            #         fail_silently=False,
            #     )
                
            #     # ajouter un teste pour voir si tous les enregistrement relatifs au professeur sous achevés
            # except Exception as e:
            #     messages.error(request, f"Une erreur s'est produite lors de l'envoi de l'email: {str(e)}")
            # messages.success(request, "L'email a été envoyé avec succès. ")
        
            email_telecharge = Email_telecharge(user=user, email_telecharge=email_prof, text_email=text_email, user_destinataire=user_destinataire_id, sujet=sujet)
            email_telecharge.save()
            messages.success(request, "Email enregistré")
            
            if fichiers_list:
                for fichier in fichiers_list:
                    nom_fichier = fichier.name
                    # Obtenez l'extension du fichier
                    extension_fichier = os.path.splitext(nom_fichier)[1].lower()
                    prof_doc_telecharge = Prof_doc_telecharge(user=user, doc_telecharge=fichier, email_telecharge=email_telecharge)
                    prof_doc_telecharge.save()
                return redirect('modifier_format_cours')
        else: messages.error(request, "Vous devez ajouter un texte pour votre email")
    return render(request, 'accounts/nouveau_fichier.html', {'text_email': text_email, 'email_prof': email_prof, 'sujet': sujet})


def votre_compte(request):
    # Récupérer l'utilisateur actuel
    user = request.user
    if user.is_authenticated:
        # messages.success(request, f"Vous etes connecté. {user.first_name}")
        # Vérifier si l'utilisateur a un profil de professeur associé
        if hasattr(user, 'professeur'):
            # Si tel est le cas, récupérer le profil du professeur
            professeur = Professeur.objects.get(user=user)
            # Extraire la photo du profil du professeur
            photo = professeur.photo
            first_name = user.first_name
            # Passer la photo à votre modèle de contexte
            context = {'photo': photo, 'first_name':first_name}
            return render(request, 'accounts/compte_prof.html', context)
        else: 
            if hasattr(user, 'eleve'):
                return render(request, 'eleves/compte_eleve.html')
    messages.error(request, "Vous devez être connecté pour effectuer cette action.")
    return redirect('signin')

def compte_prof(request):
    # Récupérer l'utilisateur actuel
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin')


    # Effacer tous les paramètres de session sauf l'utilisateur
    keys_to_keep = ['_auth_user_id', '_auth_user_backend', '_auth_user_hash']
    keys_to_delete = [key for key in request.session.keys() if key not in keys_to_keep]
    for key in keys_to_delete:
        del request.session[key]
        
    return render(request, 'accounts/compte_prof.html')

def logout(request):
    if request.user.is_authenticated:
        auth.logout(request)
        # messages.success(request, 'Vous etes déconnecté(e) de votre compte')
    return redirect('index')



def modifier_compte_prof(request):
    # paramètres par défaut
    teste = True
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin') 
    
    #Récupérer les anciennes données enregistrées
    professeur = Professeur.objects.get(user=user)
    username = user.username
    first_name = user.first_name
    last_name = user.last_name
    email = user.email
    civilite = professeur.civilite
    numero_telephone = professeur.numero_telephone
    date_naissance = professeur.date_naissance
    adresse = professeur.adresse

    # si le bouton enregister est cliqué
    if request.method == 'POST' and 'btn_enr' in request.POST:
        # récupérer les données du template
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        email = request.POST['email']
        civilite = request.POST['civilite']
        numero_telephone = request.POST['numero_telephone']
        date_naissance = request.POST['date_naissance']
        adresse = request.POST['adresse']


        if not first_name.strip() or not last_name.strip() or not email.strip() or not civilite.strip() or not numero_telephone.strip() or not date_naissance.strip() or not adresse.strip():
            messages.error(request, "Tous les champs ne peuvent pas être vide ou contenir uniquement des espaces.")
            teste = False

        # si l'email a été changé et que le nouveau email existe déjà
        if email != user.email and User.objects.filter(email=email).exists():
            messages.error(request, "L'email est déjà utilisé, donnez un autre email")
            teste = False

        # Vérifier le format de la date
        try:
                # si la convertion est réussie
                date_naissance_nouveau_01 = datetime.strptime(date_naissance, '%d/%m/%Y') # date_naissance_nouveau_01 est crée juste pour tester le format de la date
        except ValueError:
            messages.error(request, "Format de date de naissance invalide. Utilisez jj/mm/aaaa")
            date_naissance = professeur.date_naissance
            teste = False

        #tester le format de l'email
        email_validator = EmailValidator() # Initialiser le validateur d'email
        # Validation de l'email_prof
        try:
            email_validator(email)
        except ValidationError:
            messages.error(request, "Le format de l'email est incorrecte.")
            teste = False

        if teste: # si tous les données sont valides
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.save()

            # Mettre à jour les données du professeur 
            professeur.adresse = adresse
            professeur.numero_telephone = numero_telephone
            professeur.civilite = civilite
            professeur.set_date_naissance_from_str(date_naissance)
            # s'il y a un changement de photo d'identité
            if 'photo' in request.FILES: professeur.photo = request.FILES['photo']  
            professeur.save()
            # auth.login(request, user)
            messages.success(request, "Les informations ont été mises à jour avec succès.")
            return redirect('compte_prof')

    context = {'username':username,
        'first_name':first_name,
        'last_name':last_name,
        'email':email,
        'civilite':civilite,
        'numero_telephone':numero_telephone,
        'date_naissance':date_naissance,
        'adresse':adresse}
    return render(request, 'accounts/modifier_compte_prof.html', context)
    # voire l'interet de ce code alternative
    # # Rendre la réponse en utilisant le template 'pages/index.html'
    # response = render(request, 'accounts/modifier_compte_prof.html', context)
    # # Ajouter les en-têtes pour empêcher la mise en cache de la page
    # # Cela garantit que le navigateur récupère toujours les données les plus récentes
    # response['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # HTTP 1.1.
    # response['Pragma'] = 'no-cache'  # HTTP 1.0.
    # response['Expires'] = '0'  # Proxies.
    # # Retourner la réponse
    # return response



def modifier_format_cours(request):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin') 
    
    
    try:
        # Essayer de récupérer l'objet Format_cour de l'utilisateur
        format_cour = Format_cour.objects.get(user=user)
        # Préparer les données initiales pour le contexte
        initial_data = {
            'a_domicile': format_cour.a_domicile,
            'webcam': format_cour.webcam,
            'stage': format_cour.stage,
            'stage_webcam': format_cour.stage_webcam,
        }
    except Format_cour.DoesNotExist:
        # Si aucun Format_cour n'existe pour l'utilisateur, préparer les données initiales par défaut
        format_cour = None
        initial_data = {
            'a_domicile': False,
            'webcam': False,
            'stage': False,
            'stage_webcam': False,
        }

    # Vérifier si la requête est POST et si le bouton 'btn_enr' est soumis
    if request.method == 'POST' and 'btn_enr' in request.POST:
        # Liste des formats possibles
        formats = ['chk_a_domicile', 'chk_webcam', 'chk_stage', 'chk_stage_webcam']
        # Création d'un dictionnaire pour vérifier les formats cochés
        format_states = {format: request.POST.get(format) is not None for format in formats}

        # Vérifier qu'au moins un format est coché
        if not any(format_states.values()):
            messages.error(request, "Il faut au moins cocher une case d'un format de cours.")
            return render(request, 'accounts/modifier_format_cours.html', initial_data)

        # Mise à jour des formats si l'objet existe déjà
        if format_cour:
            format_cour.a_domicile = format_states['chk_a_domicile']
            format_cour.webcam = format_states['chk_webcam']
            format_cour.stage = format_states['chk_stage']
            format_cour.stage_webcam = format_states['chk_stage_webcam']
            format_cour.save()
        else:
            # Création d'un nouveau Format_cour si aucun n'existe
            format_cour = Format_cour(
                user=user,
                a_domicile=format_states['chk_a_domicile'],
                webcam=format_states['chk_webcam'],
                stage=format_states['chk_stage'],
                stage_webcam=format_states['chk_stage_webcam']
            )
            format_cour.save()

        # Suppression des enregistrements Prix_heure non utilisés
        if not format_cour.a_domicile:
            Prix_heure.objects.filter(user=user, format="Cours à domicile").delete()
        if not format_cour.webcam:
            Prix_heure.objects.filter(user=user, format="Cours par webcam").delete()
        if not format_cour.stage:
            Prix_heure.objects.filter(user=user, format="Stage pendant les vacances").delete()
        if not format_cour.stage_webcam:
            Prix_heure.objects.filter(user=user, format="Stage par webcam").delete()

        # Message de succès et redirection vers la page du compte utilisateur
        messages.success(request, "Les nouveaux formats des cours sont enregistrés. Vous devez réviser vos prix par heure pour chaque enregistrement nouveau.")
        return redirect('nouveau_prix_heure')

    # Rendre la page avec les données initiales
    return render(request, 'accounts/modifier_format_cours.html', initial_data)




def modifier_description(request):

    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin') 
    try:
        pro_fichier = Pro_fichier.objects.get(user=user)
        date_modif = pro_fichier.date_modif
        titre_fiche = pro_fichier.titre_fiche
        parcours = pro_fichier.parcours
        pedagogie = pro_fichier.pedagogie
        video_youtube_url = pro_fichier.video_youtube_url
        context = {
            'date_modif': date_modif,
            'titre_fiche': titre_fiche,
            'parcours': parcours,
            'pedagogie': pedagogie,
            'video_youtube_url': video_youtube_url,
        }
        if not (request.method == 'POST' and 'btn_enr' in request.POST):
            return render(request, 'accounts/modifier_description.html', context)
        if request.method == 'POST' and 'btn_enr' in request.POST:
            titre_fiche  = request.POST.get('titre_fiche')
            parcours  = request.POST.get('parcours')
            pedagogie  = request.POST.get('pedagogie')
            video_youtube_url = request.POST.get('video_youtube_url')
            # supprimer l'ancien enregistrement
            ancien_enregistrement = Pro_fichier.objects.get(user=user)
            ancien_enregistrement.delete()
            # Créez un nouveau Pro_fichier avec les données mises à jour
            pro_fichier = Pro_fichier(user=user, titre_fiche=titre_fiche, parcours=parcours, pedagogie=pedagogie, video_youtube_url=video_youtube_url)
            pro_fichier.save()
            messages.success(request, "Les nouvelles descriptions sont enregistrés")
            return redirect('compte_prof')
    except Pro_fichier.DoesNotExist:
        messages.error(request, "Les données des descriptions n'existent pas pour cet utilisateur. Vous devez ajouter vos descriptions avant")
        return redirect('nouveau_description')

    return render(request, 'accounts/modifier_description.html')


def modifier_diplome(request): # il faut refaire la logique d'enregistrement de ce view
   
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin') 

    teste = True
    diplome_cathegories = Diplome_cathegorie.objects.all()

    diplomes = Diplome.objects.filter(user=user)
    if not diplomes:
        messages.error(request, "Les données des diplômes n'existent pas pour cet utilisateur. Vous devez ajouter vos diplômes avant")
        teste = False

    for diplome in diplomes:
        diplome.obtenu = diplome.obtenu.strftime('%d/%m/%Y') # code correct
    
    context = {
        'diplome_cathegories': diplome_cathegories,
        'diplomes': diplomes,
    }

    if not (request.method == 'POST' and 'btn_enr' in request.POST):
        return render(request, 'accounts/modifier_diplome.html', context)

    if request.method == 'POST' and 'btn_enr' in request.POST:
        # Liste des diplômes dans le request dont le nom commence par: diplome_1
        diplome_keys = [key for key in request.POST.keys() if key.startswith('diplome_')]
        if not diplome_keys:
            messages.error(request, "Il faut donner au moins un diplôme  ")
            return render(request, 'accounts/modifier_diplome.html', context)
        
        # début de l'enregistrement
        # supprimer les anciens enregistrements
        diplomes.delete() # il faut sauvegarder une copi des enregistrement en cas d"echec d'enregistrement
        for diplome_key in diplome_keys:
            i = int(diplome_key.split('_')[1])
            diplome_key = f'diplome_{i}'
            date_obtenu_key = f'date_obtenu_{i}'
            principal_key = f'principal_{i}'
            intitule_key = f'intitule_{i}'
            if request.POST.get(diplome_key):
                diplome = request.POST.get(diplome_key)
                if not diplome.strip() or diplome == 'Autre':  # Vérifie si la chaîne est vide ou contient seulement des espaces ou = 'Autre'
                    messages.error(request, "Le diplôme ne peut pas être vide ou contenir uniquement des espaces. ou intitulé: Autre")
                    continue  # Move to the next iteration of the loop
                if len(diplome) > 100:
                    diplome = diplome[:100]  # Prendre seulement les 100 premiers caractères
                    messages.info(request, "Le diplôme a été tronqué aux 100 premiers caractères.")
                diplome_cathegorie = Diplome_cathegorie.objects.filter(dip_cathegorie=diplome)
                if not diplome_cathegorie.exists():
                    # Le diplôme n'existe pas, nous devons l'ajouter à la table Diplome_cathegorie
                    pays_default = Pays.objects.get(nom_pays='France')  # Remplacez 'Default' par le nom du pays par défaut
                    new_diplome_cathegorie = Diplome_cathegorie.objects.create(nom_pays=pays_default, dip_cathegorie=diplome)
                    new_diplome_cathegorie.save()
                
                # Le diplôme existe déjà dans la table Diplome_cathegorie
                # Requête pour récupérer l'objet Diplome_cathegorie
                diplome_obj = Diplome_cathegorie.objects.get(dip_cathegorie=diplome)
                # Récupérer l'ID de l'objet Diplome_cathegorie
                diplome_cathegorie_id = diplome_obj.id
                date_obtenu = request.POST.get(date_obtenu_key, None)
                if date_obtenu:
                    # tester le format des dates
                    try:
                        # si la convertion est réussie
                        date_obtenu_01 = datetime.strptime(date_obtenu, '%d/%m/%Y') # debut_01 juste pour le try seulement
                    except ValueError:
                        date_obtenu = datetime.now().strftime('%d/%m/%Y')  # à améliorer cette logique d'enregistrement
                if request.POST.get(principal_key, None) == "on":
                    principal = True
                else: principal = False
                intitule = request.POST.get(intitule_key, None)
                # Vérification si le diplôme n'existe pas déjà pour cet utilisateur
                if not Diplome.objects.filter(user=user, diplome_cathegorie_id=diplome_cathegorie_id, intitule=intitule).exists():
                    if not date_obtenu:
                        date_obtenu = datetime.now().strftime('%d/%m/%Y')  # Prendre la date du jour au format jj/mm/aaaa
                    diplome_instance = Diplome(user=user, diplome_cathegorie_id=diplome_cathegorie_id, intitule=intitule, principal=principal)
                    diplome_instance.set_date_obtenu_from_str(date_obtenu)
                    diplome_instance.save()
                    
                else: # si le diplome existe 
                    continue
        return redirect('compte_prof')

        

    return render(request, 'accounts/modifier_diplome.html', context)


def modifier_experience(request):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin') 

    # Récupération de toutes les catégories d'expérience
    experience_cathegories = Experience_cathegorie.objects.all()
    experiences = Experience.objects.filter(user=user)

    if experiences.exists(): # Si l'utilisateur a déjà des expériences enregistrées
        # Formatage des dates pour l'affichage
        for experience in experiences:
            if experience.debut: # non nécessaire mais par prudense / voire sinon,
                experience.debut = experience.debut.strftime('%d/%m/%Y')
            if experience.fin: # n'est pas nécessaire car la date peut etre nulle
                experience.fin = experience.fin.strftime('%d/%m/%Y')
            else:
                experience.fin = "" # que le champ reste vide au lieu de None

        # Préparation du contexte pour le rendu du template
        context = {
            'experience_cathegories': experience_cathegories,
            'experiences': experiences,
        }

        # Si le formulaire de modification est soumis
        if request.method == 'POST' and 'btn_enr' in request.POST:
            # liste des expérience dans le template
            experience_keys = [key for key in request.POST.keys() if key.startswith('experience_')]
            if not experience_keys:
                messages.error(request, "Il faut donner au moins une expérience.")
                return render(request, 'accounts/modifier_experience.html', context)
            # paramaitre pour tester si il y a eu un enregistrement au moins
            # pour éviter le cas d'effacer tous les anciens enregistrements sans enregistrer au moins un
            premier_nouveau_enregistrement = False
            
            # Boucle sur les expériences soumises via le formulaire
            for experience_key in experience_keys:
                # extraire l'indice i du template pour l'expérience 
                i = int(experience_key.split('_')[1])
                # définir les paramaitres de l'expérience selon leurs name
                principal_key = f'principal_{i}'
                experience_key = f'experience_{i}'
                date_debut_key = f'date_debut_{2*i-1}'
                date_fin_key = f'date_fin_{2*i}'
                act_key = f'act_{i}'
                comm_key = f'comm_{i}'

                # Récupération des données soumises dans le template de l'expérience
                type = request.POST.get(experience_key)
                if not type.strip():
                    continue # iniorer l'enregistrement
                if len(type) > 100:
                    type = type[:100]
                    messages.info(request, "Cette expérience a été tronquée aux 100 premiers caractères.")
                date_debut = request.POST.get(date_debut_key, None)
                # tester le format des dates, à améliorer cette logique d'enregistrement
                if date_debut:
                    try:
                        # si la convertion est réussie
                        date_debut_01 = datetime.strptime(date_debut, '%d/%m/%Y') # debut_01 juste pour le try seulement
                    except ValueError:
                        date_debut = datetime.now().strftime('%d/%m/%Y')
                
                date_fin = request.POST.get(date_fin_key, None)
                if date_fin:
                    try:
                        # si la convertion est réussie
                        date_fin_01 = datetime.strptime(date_fin, '%d/%m/%Y') # debut_01 juste pour le try seulement
                    except ValueError:
                        date_fin = None # date_fin = "" génère une erreur d'enregistrement
                # si 'principal_key' existe alors principale==on si non None
                principal = request.POST.get(principal_key, None) == "on"
                actuellement = request.POST.get(act_key, None) == "on"
                commentaire = request.POST.get(comm_key, None)

                # Si c'est le premier enregistrement, supprimer les anciennes expériences de l'utilisateur
                if not premier_nouveau_enregistrement:
                    experiences.delete()
                    premier_nouveau_enregistrement = True

                # Vérification de doublons et enregistrement des nouvelles expériences
                # remarque la suppression des anciens enregistrements est effectuée seulement avant le premier enregistrement
                # donc le premier enregistrement est obligatoirement effectué car il ne peut y avoire de doublant
                if not Experience.objects.filter(user=user, type=type, commentaire=commentaire).exists():
                    # if not date_debut: # voire si ce teste est nécessaire
                    #     date_debut = datetime.now().strftime('%d/%m/%Y')
                        
                    experience_instance = Experience(user=user, type=type, actuellement=actuellement, commentaire=commentaire, principal=principal)
                    experience_instance.set_date_debut_from_str(date_debut)
                    experience_instance.set_date_fin_from_str(date_fin)
                    experience_instance.save()
                else:
                    continue # ignorer l'enregistrement
            
            return redirect('compte_prof')

        return render(request, 'accounts/modifier_experience.html', context)

    # Si l'utilisateur n'a pas encore d'expériences enregistrées
    messages.error(request, "Les données des expériences n'existent pas pour cet utilisateur. Vous devez ajouter vos expériences avant.")
    return redirect('nouveau_experience')



def modifier_matiere(request):

    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin') 
    
    # Récupération de toutes les catégories de matières et niveaux
    matieres = Matiere.objects.all()
    niveaus = Niveau.objects.all()
    prof_mat_nivs = Prof_mat_niv.objects.filter(user=user)
    liste_mat_niv_anciens = []
    
    # Si l'utilisateur a déjà des matières enregistrées
    if prof_mat_nivs.exists():
        for prof_mat_niv in prof_mat_nivs: # creer la liste des anciens enregistrement
            matiere_ancien = prof_mat_niv.matiere.matiere
            niveau_ancien = prof_mat_niv.niveau.niveau
            principal_ancien = prof_mat_niv.principal
            coupe = (matiere_ancien, niveau_ancien, principal_ancien)
            liste_mat_niv_anciens.append(coupe)

        # Préparation du contexte pour le rendu du template
        context = {
            'prof_mat_nivs': prof_mat_nivs,
            'matieres': matieres,
            'niveaus': niveaus
        }

        # Si le formulaire de modification est soumis
        if request.method == 'POST' and 'btn_enr' in request.POST:
            # Liste des matières dans le template
            matiere_keys = [key for key in request.POST.keys() if key.startswith('matiere_')]
            if not matiere_keys:
                messages.error(request, "Vous devez garder au moins une matière.")
                return render(request, 'accounts/modifier_matiere.html', context)
            liste_mat_niv_modifs = [] # pour reconstruire les enregistrements modifier des prof_mat_niv
            for matiere_key in matiere_keys:
                # pour extraire du request les données des enregistrements
                i = int(matiere_key.split('_')[1])
                principal_key = f'principal_{i}'
                matiere_key = f'matiere_{i}'
                niveau_key = f'niveau_{i}'

                principal = request.POST.get(principal_key, False)
                matiere_name = request.POST.get(matiere_key, None)
                niveau_name = request.POST.get(niveau_key, None)
                principal_modif = True if principal == "on" else False

                # Récupération des objets Matiere et Niveau correspondants
                matiere_modif = Matiere.objects.get(matiere=matiere_name).matiere
                niveau_modif = Niveau.objects.get(niveau=niveau_name).niveau
                coupe = (matiere_modif, niveau_modif, principal_modif)
                liste_mat_niv_modifs.append(coupe)
            # Supprimer les anciens enregistrements de prof_mat_niv qui ne figurent pas dans les enregistrement modifiers
            liste_mat_niv_sup = []
            for matiere_ancien, niveau_ancien, principal_ancien in liste_mat_niv_anciens:
                existe = 0
                for matiere_modif, niveau_modif, principal_modif in liste_mat_niv_modifs:
                    if matiere_ancien == matiere_modif and niveau_ancien == niveau_modif:
                        # mettre à jour les anciens enregistrement de Prof_mat_niv
                        matiere_principal = Matiere.objects.get(matiere=matiere_ancien)
                        niveau_principal = Niveau.objects.get(niveau=niveau_ancien)
                        prof_mat_niv_principal = Prof_mat_niv.objects.filter(user=user, matiere=matiere_principal, niveau=niveau_principal)
                        prof_mat_niv_principal.update(principal=principal_modif)
                        existe = 1
                        break
                if  existe == 0:
                    matiere_sup = Matiere.objects.get(matiere=matiere_ancien)
                    niveau_sup = Niveau.objects.get(niveau=niveau_ancien)
                    couple = (matiere_sup, niveau_sup)
                    liste_mat_niv_sup.append(couple)
            for matiere_sup, niveau_sup in liste_mat_niv_sup:
                prof_mat_niv_sups = Prof_mat_niv.objects.filter(user=user, matiere=matiere_sup, niveau=niveau_sup)
                if prof_mat_niv_sups.exists():
                    for prof_mat_niv_sup in prof_mat_niv_sups:
                        # Supprimer les enregistrements de Prix_heure s'ils existent
                        Prix_heure.objects.filter(prof_mat_niv=prof_mat_niv_sup.id).delete()
                        # Supprimer les enregistrements de Prof_mat_niv
                        prof_mat_niv_sup.delete()
            
            # Ajouter les nouveau enregistrements de Prof_mat_niv
            j = 0 # conte nouveaux enregistrement
            for matiere_modif, niveau_modif, principal_modif in liste_mat_niv_modifs:
                exist = 0
                for matiere_ancien, niveau_ancien, principal_ancien in liste_mat_niv_anciens:
                    if matiere_ancien == matiere_modif and niveau_ancien == niveau_modif: 
                        exist = 1
                        break
                if exist == 1: continue # ne rien faire car l'enregistrement est déjà mis à jour
                else: # ajouter l'enregistrement
                    j = j +1
                    matiere_ajout = Matiere.objects.get(matiere=matiere_modif)
                    niveau_ajout = Niveau.objects.get(niveau=niveau_modif)
                    prof_mat_niv = Prof_mat_niv(user=user, matiere=matiere_ajout, niveau=niveau_ajout, principal=principal_modif)
                    prof_mat_niv.save()
            if j > 0:messages.info(request, f"Il y a {j} nouveau(x) enregistrement(s), vous devez réviser vos prix par heur pour chaque enregistrement")
            messages.success(request, "L'enregistrement est achevé avec succés. ")
            return redirect('compte_prof')

        # Rendu de la page de modification de matières avec le contexte
        return render(request, 'accounts/modifier_matiere.html', context)

    # Si l'utilisateur n'a pas encore de matières enregistrées
    messages.error(request, "Les données des matières n'existent pas pour cet utilisateur. Vous devez ajouter vos matières avant.")
    return redirect('nouveau_matiere')

def modifier_zone(request):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin') 


    # Récupération de toutes les prof_zones pour l'utilisateur connecté
    prof_zones = Prof_zone.objects.filter(user=request.user)

    # Si l'utilisateur a déjà des matières enregistrées
    if prof_zones.exists():
        # Construction de la liste des chaînes "région - département - commune"
        zone_lists = []
        for prof_zone in prof_zones:
            commune = prof_zone.commune
            departement = commune.departement
            region = departement.region
            zone_string = f"{region.region} - {departement.departement} -- {commune.commune}"
            zone_lists.append(zone_string)

        # Préparation du contexte pour le rendu du template
        context = {
            'zone_lists': zone_lists,
        }

        # messages.info(request, f"Nombre de zone : {len(zone_lists)}")

        # Si le formulaire de modification est soumis
        if request.method == 'POST' and 'btn_enr' in request.POST:
            # Liste des matières dans le template
            zone_keys = [key for key in request.POST.keys() if key.startswith('zone_')]
            # messages.info(request, f"Nombre de zone : {len(zone_keys)}")
            if not zone_keys:
                messages.error(request, "Vous avez supprimé toutes les zones.")
                prof_zones.delete()
                return redirect('compte_prof')
            prof_zones.delete()
            # Boucle sur les matières soumises via le formulaire
            for zone_key in zone_keys:
                i = int(zone_key.split('_')[1])
                zone_key = f'zone_{i}'
                zone_value = request.POST.get(zone_key, None)
                # Diviser la chaîne en deux parties en utilisant '--' comme séparateur
                parts = zone_value.split('-- ')
                # Vérifier s'il y a au moins deux parties après la division
                if len(parts) >= 2:
                    # Extraire la deuxième partie qui est celle juste après '--'
                    commune_nom = parts[1].strip()
                    # Récupération l'objets commune
                    commune_obj = Commune.objects.get(commune=commune_nom)
                    # Création de la relation Prof_zone
                    Prof_zone.objects.create(user=user, commune=commune_obj)
                    # messages.success(request, f"L'enregistrement de la zone '{commune_nom}' a réussi.")
                else: 
                    messages.info(request, f"Revoire le programmeur => erreur enregistrement zone d'activité: zone_value: {zone_value}")
            # Redirection vers la page du compte après l'enregistrement
            # messages.success(request, f"L'enregistrement des zones a réussi.")
            return redirect('compte_prof')

        # Rendu de la page de modification de matières avec le contexte
        return render(request, 'accounts/modifier_zone.html', context)

    # Si l'utilisateur n'a pas encore de matières enregistrées
    messages.error(request, "Les données des zones d'activités n'existent pas pour cet utilisateur. Vous devez ajouter vos zones avant.")
    return redirect('nouveau_zone')


def demande_cours_recu(request):
    # Vérification si l'utilisateur est connecté
    if not request.user.is_authenticated:
        messages.error(request, "Vous devez être connecté pour accéder à cette page.")
        return redirect('signin')
    
    user_id = request.user.id # ID prof
    
    emails = Email_telecharge.objects.filter(user_destinataire=user_id, suivi__isnull = True) # email destinés aux prof sans réponse
    
    if emails.count() == 0:
        messages.info(request, "Il n'y a pas d'Email nouvellement envoyé.")
        return redirect('compte_prof')
    # tri enregistrements par ordre décroissant des date_telechargement
    email_detailles = Email_detaille.objects.filter(email__in=emails).order_by('-email__date_telechargement')
    context = {'email_detailles': email_detailles}
    
    return render(request, 'accounts/demande_cours_recu.html', context)
    

def demande_cours_recu_eleve(request, email_id):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin')
    
    email = Email_telecharge.objects.filter(id=email_id).first() # récupérer l'email
    if not email: # teste pas nécessaire
        messages.info(request, "Il n'y a pas d'email envoyé.")
        return redirect('demande_cours_recu') # Rediriger vers la page précédente
    
    eleve = Eleve.objects.filter( user_id=email.user.id).first() # récupérer l'élève
    if not eleve:
        messages.error(request, "Il n'y a pas d'élève expéditeur d'email envoyé.")
        return redirect('compte_prof')

    mon_eleve_exists = Mes_eleves.objects.filter(eleve=eleve, user=user).exists() # Voire si c'est mon élève
    if mon_eleve_exists: mon_eleve_id= Mes_eleves.objects.filter(eleve=eleve, user=user).first().id # Récupérer l'ID de mon èmève
    context = {'email': email, 'email_id': email_id, 'mon_eleve_exists': mon_eleve_exists}
    
    # Initialiser le validateur d'email
    email_validator = EmailValidator()

    if 'btn_ignorer' in request.POST: # bouton Ignorer activé
        email.suivi = 'Mis à côté'
        email.date_suivi = date.today()
        email.save() 
        messages.success(request, "L'email est enregistré en tant qu'email ignoré.")
        return redirect('compte_prof') # Rediriger vers compte professeur

    if 'btn_confirmer' in request.POST: # bouton confirmer activé
        email_prof = user.email
        email_eleve = email.email_telecharge
        sujet = "Confirmation de réception"
        text_email = f"""
        J'ai bien reçu votre email
        Date de réception : {email.date_telechargement}
        Sujet de l'email : {email.sujet}
        Contenu de l'email :
        {email.text_email}
        """
        destinations = ['prosib25@gmail.com', email_eleve]

        # Validation de l'email_prof
        try:
            email_validator(email_prof)
        except ValidationError:
            messages.error(request, "L'adresse email du professeur est invalide.")
            return render(request, 'accounts/demande_cours_recu_eleve.html', context)

        # Validation des emails dans destinations
        for destination in destinations:
            try:
                email_validator(destination)
            except ValidationError:
                messages.error(request, f"L'adresse email du destinataire {destination} est invalide.")
                return render(request, 'accounts/demande_cours_recu_eleve.html', context)

        try:
            send_mail(sujet, text_email, email_prof, destinations, fail_silently=False)
            messages.success(request, "L'email a été envoyé avec succès.")
        except Exception as e:
            messages.error(request, f"Une erreur s'est produite lors de l'envoi de l'email : {str(e)}")

        email_telecharge = Email_telecharge(
            user=user,
            email_telecharge=email_prof,
            text_email=text_email,
            user_destinataire=email.user.id,
            sujet=sujet
        )
        email_telecharge.save()

        email.suivi = 'Réception confirmée'
        email.date_suivi = date.today()
        email.reponse_email_id = email_telecharge.id
        email.save() 

        messages.success(request, "Email enregistré")
        return redirect('compte_prof')

    if 'btn_repondre' in request.POST:
        return redirect('reponse_email', email_id=email_id) # Redirigze ver page  email_id est transmis à reponse_email
    
    if 'btn_historique' in request.POST: # bouton historique activé
        if email.reponse_email_id==None:
            messages.info(request, "Il n'y a pas de réponse à cet email")
            return render(request, 'accounts/demande_cours_recu_eleve.html', context) # rediriger vers la même page
        prof = Professeur.objects.filter( user_id=email.user.id).first() # récupérer l'élève
        if not prof:
            messages.error(request, "Il n'y a pas d'email envoyé.")
            return redirect('compte_prof')
        # rediriger vers la même page mais en changeant l'argument
        # il faut élaborer une page spéciale pour afficher l'historique des emails
        return redirect(reverse('demande_cours_recu_eleve', args=[email.reponse_email_id])) # -	ça marche très bien
    
    if 'btn_ajout_eleve' in request.POST: # bouton ajout élève activé
        return redirect('ajouter_mes_eleve', eleve_id=email.user.id) # Rediriger vers autre page
    
    if 'btn_voire_eleve' in request.POST: # bouton ajout élève activé
        return redirect('modifier_mes_eleve', mon_eleve_id=mon_eleve_id) # Rediriger vers autre page

    return render(request, 'accounts/demande_cours_recu_eleve.html', context) # Revenir à la même page, le context est nécessaire pout le template



def reponse_email(request, email_id): 
    email = Email_telecharge.objects.filter(id=email_id).first() # envoyé par l'élève
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin') 
    text_email = f"""
        Suite à votre email :
        Date de réception : {email.date_telechargement}
        Sujet de l'email : {email.sujet}
        Contenu de l'email :
        {email.text_email}
        ---------------------------
        En réponse à votre email, je vous adresse ce qui suit.
        """
    sujet = "Suite à votre email"
    email_prof = user.email
    context={'text_email': text_email, 'sujet': sujet, 'email_prof': email_prof}
    if 'btn_enr' in request.POST:
        
        text_email = request.POST.get('text_email', '').strip()
        sujet = request.POST.get('sujet', '').strip()
        email_prof = request.POST.get('email_adresse', '').strip() # la priorité est à l'email reçu du POST
        if not email_prof: # si l'email du POST est null ou vide
            email_prof = user.email 

        # Validation de l'email_prof
        email_validator = EmailValidator() #inicialisation de l'objet EmailValidator
        try:
            email_validator(email_prof)
        except ValidationError:
            messages.error(request, "L'adresse email du professeur est invalide.")
            context={'text_email': text_email, 'sujet': sujet, 'email_prof': email_prof}
            return render(request, 'accounts/reponse_email.html', context) # revenir à la même page

        sujet = request.POST.get('sujet', '').strip() 
        if not sujet:  
            sujet = "Suite à votre email"
        
        text_email =  request.POST['text_email']
        user_destinataire = email.user.id
        email_eleve = email.email_telecharge
        destinations = ['prosib25@gmail.com', email_eleve]  

        # Validation des emails dans destinations
        for destination in destinations:
            try:
                email_validator(destination)
            except ValidationError:
                messages.error(request, f"L'adresse email du destinataire {destination} est invalide.")
                # même s'il y a erreur l'enregistrement continu car l'envoi de l'email n'est pas obligatoire

        try:
            send_mail(
                sujet,
                text_email,
                email_prof,
                destinations,
                fail_silently=False,
            )
            messages.success(request, "La réponse à l'email a été envoyée avec succès.")
        except Exception as e:
            messages.error(request, f"Une erreur s'est produite lors de l'envoi de l'email : {str(e)}")
        
        # enregistrement de l'email
        email_telecharge = Email_telecharge(
            user=user, 
            email_telecharge=email_prof, 
            text_email=text_email, 
            user_destinataire=user_destinataire, 
            sujet=sujet
        )
        email_telecharge.save()
        # mise à jour de l'enregistrement de l'email envoyé par l'élève
        email_reponse_id = email_telecharge.id  
        email.suivi = 'Répondu'
        email.date_suivi = timezone.now()
        email.reponse_email_id = email_reponse_id
        email.save()  
        messages.success(request, "Email enregistré")

        # passer à historique_prof pour mettre à jour temps moyen de réponse en secondes
        date_email_eleve_telecharger = email.date_telechargement
        date_email_prof_reponse = email.date_suivi
        temps = (date_email_prof_reponse - date_email_eleve_telecharger).total_seconds()
        historique_prof , created = Historique_prof.objects.get_or_create(user=user)

        historique_prof.total_cumul_temps_reponse += temps
        historique_prof.nb_reponse_demande_cours += 1
        historique_prof.save()
        if historique_prof.total_cumul_temps_reponse and historique_prof.nb_reponse_demande_cours and historique_prof.nb_reponse_demande_cours>0:
            historique_prof.moyenne_temps_reponse = int(historique_prof.total_cumul_temps_reponse/historique_prof.nb_reponse_demande_cours)
            historique_prof.save()
        return redirect('compte_prof') # Rediriger vers compte_prof
    
    return render(request, 'accounts/reponse_email.html', context) # revenir sur la même page


def email_recu_prof(request):
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
    emails = get_emails({})

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
    return render(request, 'accounts/email_recu_prof.html', context)

def modifier_mot_pass(request):
    # Initialiser le dictionnaire de contexte avec des valeurs vides
    context = {
        'user_nom': "",
        'mot_pass': "",
        'nouveau_user_nom': "",
        'nouveau_mot_pass': "",
        'confirmer_mot_pass': "",
    }

    # Vérifier si la méthode de la requête est POST et si le bouton d'enregistrement a été cliqué
    if request.method == 'POST' and 'btn_enr' in request.POST:
        # Récupérer les données du formulaire depuis la requête POST
        user_nom = request.POST['user_nom']
        mot_pass = request.POST['mot_pass']
        nouveau_user_nom = request.POST['nouveau_user_nom']
        nouveau_mot_pass = request.POST['nouveau_mot_pass']
        confirmer_mot_pass = request.POST['confirmer_mot_pass']

        # Mettre à jour le contexte avec les données du formulaire
        context.update({
            'user_nom': user_nom,
            'mot_pass': mot_pass,
            'nouveau_user_nom': nouveau_user_nom,
            'nouveau_mot_pass': nouveau_mot_pass,
            'confirmer_mot_pass': confirmer_mot_pass,
        })

        # Authentifier l'utilisateur avec le nom d'utilisateur et le mot de passe fournis
        user = auth.authenticate(username=user_nom, password=mot_pass)
        
        if user is not None:  # Si l'authentification de l'utilisateur réussit
            # Vérifier que tous les champs nécessaires pour la modification sont remplis
            if all([nouveau_user_nom, nouveau_mot_pass, confirmer_mot_pass]):
                # Vérifier si le nouveau nom d'utilisateur est déjà pris
                if User.objects.filter(username=nouveau_user_nom).exists() and nouveau_user_nom != user_nom:
                    messages.error(request, "Le nom de l'utilisateur est déjà utilisé, donnez un autre nom.")
                # Vérifier que le nouveau mot de passe contient au moins 8 caractères
                elif len(nouveau_mot_pass) < 8:
                    messages.error(request, "Le nouveau mot de passe doit contenir au moins 8 caractères.")
                # Vérifier que le mot de passe n'a pas été compromis dans une violation de données
                elif is_password_compromised(nouveau_mot_pass):
                    messages.error(request, "Le nouveau mot de passe a été compromis lors d'une violation de données. Veuillez choisir un autre mot de passe.")
                # Vérifier que le mot de passe confirmé correspond au nouveau mot de passe
                elif nouveau_mot_pass != confirmer_mot_pass:
                    messages.error(request, "La confirmation du mot de passe n'est pas valide.")
                else:
                    # Mettre à jour le nom d'utilisateur et le mot de passe de l'utilisateur
                    user.username = nouveau_user_nom
                    user.password = make_password(nouveau_mot_pass)
                    user.save()
                    
                    # Déconnecter l'utilisateur après la modification du mot de passe
                    auth.logout(request)
                    
                    # Informer l'utilisateur que la modification du mot de passe a réussi
                    messages.success(request, "Votre mot de passe a été changé avec succès. Veuillez vous reconnecter.")
                    
                    # Rediriger l'utilisateur vers la page de connexion
                    return redirect('signin')
            else:
                messages.error(request, "Tous les champs obligatoires doivent être remplis.")
        else:
            messages.error(request, "Le nom de l'utilisateur ou le mot de passe est invalide.")

    # Rendre la page de modification du mot de passe avec le contexte actuel
    return render(request, 'accounts/modifier_mot_pass.html', context)



def nouveau_prix_heure(request):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin') 


    # Vérifie si l'utilisateur a défini un format de cours
    try:
        format_cour = Format_cour.objects.get(user=user)
    except Format_cour.DoesNotExist:
        messages.error(request, "Vous n'avez pas encore défini de format pour vos cours.")
        return redirect('compte_prof')

    # Vérifie si l'utilisateur a défini des matières et niveaux
    prof_mat_niv = Prof_mat_niv.objects.filter(user=user)
    if not prof_mat_niv:
        messages.error(request, "Vous n'avez pas encore défini de matière pour vos cours.")
        return redirect('compte_prof')

    # Prépare les formats de cours en fonction des choix de l'utilisateur
    formats = {
        'a_domicile': 'Cours à domicile',
        'webcam': 'Cours par webcam',
        'stage': 'Stage pendant les vacances',
        'stage_webcam': 'Stage par webcam'
    }
    selected_formats = {key: value for key, value in formats.items() if getattr(format_cour, key)}

    # Récupère les prix horaires existants
    prix_heure_qs = Prix_heure.objects.filter(user=user)
    liste_enregistrements = []

    # Prépare la liste des enregistrements pour le template
    for format_key, format_label in selected_formats.items():
        for prof_mat_niveau in prof_mat_niv:
            prix_heure = prix_heure_qs.filter(
                prof_mat_niv=prof_mat_niveau.id, format=format_label).first()
            prix_heure_value = str(prix_heure.prix_heure) if prix_heure else ""
            liste_enregistrements.append(
                (prof_mat_niveau.id, prof_mat_niveau.matiere, prof_mat_niveau.niveau, prix_heure_value, format_key)
            )

    context = {
        'liste_format': list(selected_formats.keys()),
        'liste_enregistrements': liste_enregistrements,
    }

    # Gère la soumission du formulaire pour enregistrer les prix horaires
    if request.method == 'POST' and 'btn_enr' in request.POST:
        liste_prix_mat_niv_for = []

        for prix_key, prix in request.POST.items():
            if prix_key.startswith('prix_heure-') and prix:
                try:
                    prix_dec = Decimal(prix[:-4]).quantize(Decimal('0.00'))
                except (InvalidOperation, ValueError):
                    messages.error(request, f"Erreur lors de la conversion du prix '{prix[:-4]}' en décimal.")
                    return render(request, 'accounts/nouveau_prix_heure.html', context)

                if prix_dec < 10:
                    messages.info(request, "Les prix inférieurs à 10 Euro sont ignorés.")
                    continue

                mat_niv_id_str, format_key = prix_key.split('-')[1].split('__')
                try:
                    mat_niv_id = int(mat_niv_id_str)
                except ValueError:
                    messages.error(request, f"Erreur lors de la conversion de l'ID '{mat_niv_id_str}' en entier.")
                    return render(request, 'accounts/nouveau_prix_heure.html', context)

                liste_prix_mat_niv_for.append((mat_niv_id, selected_formats[format_key], prix_dec))

        if not liste_prix_mat_niv_for:
            messages.error(request, "Vous devez fixer au moins un prix supérieur ou égal à 10 Euro.") # à réviser avec Hichem
            return render(request, 'accounts/nouveau_prix_heure.html', context)

        # Remplace les anciens prix horaires par les nouveaux
        Prix_heure.objects.filter(user=user).delete()
        Prix_heure.objects.bulk_create([
            Prix_heure(user=user, prof_mat_niv_id=mat_niv_id, format=format_label, prix_heure=prix_dec)
            for mat_niv_id, format_label, prix_dec in liste_prix_mat_niv_for
        ])

        messages.success(request, "Enregistrement achevé.")
        return redirect('compte_prof') # ça marche très bien

    return render(request, 'accounts/nouveau_prix_heure.html', context)


def ajouter_mes_eleve(request, eleve_id):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin') 
    # Récupérer l'élève et le parent correspondant à l'ID spécifié
    eleve = get_object_or_404(Eleve, user_id=eleve_id)
    # parent = get_object_or_404(Parent, user_id=eleve_id) # à revoire si c'est pas nécessaire
    parent = Parent.objects.filter(user_id=eleve_id).first()
    # Vérifier si l'élève existe déjà dans la table Mes_eleves
    if Mes_eleves.objects.filter(eleve=eleve, user=user).exists():
        messages.error(request, "L'élève est déjà dans la liste des élèves inscrits")
        return redirect('compte_prof')

    # Préparer le contexte pour la vue
    context = {
        'eleve': eleve,
        'parent': parent,
        'date_actuelle': timezone.now().date(),  # Obtenir la date actuelle
    }

    # Vérifier si le bouton d'enregistrement est cliqué
    # Vérifier si le bouton d'enregistrement est cliqué
    if 'btn_enr' in request.POST:
        # Ajouter l'élève à la liste des élèves inscrits
        remarque = request.POST.get('remarque', None)
        Mes_eleves.objects.create(user=request.user, eleve=eleve, is_active=True, remarque=remarque)
        messages.success(request, "L'élève est ajouté à la liste des élèves inscrits")
        
        # Rediriger vers la vue `ajouter_cours` avec l'ID de l'élève
        return redirect('ajouter_cours')

    # Rendre le template pour ajouter un élève
    return render(request, 'accounts/ajouter_mes_eleve.html', context)

def modifier_mes_eleve(request, mon_eleve_id):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin') 
    # Récupérer l'élève et le parent correspondant à l'ID spécifié
    mon_eleve = Mes_eleves.objects.filter(id=mon_eleve_id).first()
    # Vérifier si l'élève existe déjà dans la table Mes_eleves
    if not mon_eleve:
        messages.error(request, "L'élève n'est pas dans la liste des élèves inscrits")
        return redirect('compte_prof')
    eleve = get_object_or_404(Eleve, id=mon_eleve.eleve_id) # en d'erreur un message systhème est généré
    # parent = get_object_or_404(Parent, user_id=eleve.user.id) # à éviter car l'enregistrement n'est pas obligatoire
    parent = Parent.objects.filter(user_id=eleve.user.id).first() # car il peut ne pas y avoire de parent
    
    # Préparer le contexte pour la vue
    context = {
        'eleve': eleve,
        'parent': parent,
        'date_actuelle': timezone.now().date(),  # Obtenir la date actuelle
        'mon_eleve': mon_eleve,
    }

    # Vérifier si le bouton d'enregistrement est cliqué
    if 'btn_enr' in request.POST:
        # pour désactiver mon_eleve il faut qu'il n'a pas 
        #  une demande de règlement en attente ou en cours ou contester
        if mon_eleve.is_active and not 'is_active' in request.POST: # si l'élève à été déactivé
            demande_paiements = Demande_paiement.objects.filter(user=user, mon_eleve=mon_eleve)
            for demande_paiement in demande_paiements: # voire s'il y a une demande de réglement pour l'élève
                if demande_paiement.statut_demande in ['En attente','En cours','Contester']: # la désactivation est refusée
                    messages.error(request, "L'élève ne peut ëtre désactivé, car il a au moins une demande de paiement En attente ou En cours ou Contester")
                    return render(request, 'accounts/modifier_mes_eleve.html', context)
            # Désactiver l'élève
            mon_eleve.is_active = 'is_active' in request.POST
            mon_eleve.remarque = request.POST.get('remarque', None)
            mon_eleve.save()

            # on passe à la désactivation de tous les cours liés à mon_eleve
            cours_mon_eleves = Cours.objects.filter(user=user, mon_eleve=mon_eleve)
            for cours_mon_eleve in cours_mon_eleves:
                cours_mon_eleve.is_active = False
                cours_mon_eleve.save()
            messages.success(request, "L'enregistrement de mon élève est mis à jour avec désactivation de tous les cours liés")
            return redirect('modifier_mes_eleve', mon_eleve_id=mon_eleve_id )
                
        else:  # sauvegarder l'enregistrement mon_eleve sans exception
            mon_eleve.is_active = 'is_active' in request.POST
            mon_eleve.remarque = remarque = request.POST.get('remarque', None)
            mon_eleve.save()
            messages.success(request, "L'enregistrement de mon élève est mis à jour.")
            return redirect('modifier_mes_eleve', mon_eleve_id=mon_eleve_id )
        
    return render(request, 'accounts/modifier_mes_eleve.html', context)


def obtenir_parametres_cours(request):
    response_data = {}

    # Vérifiez uniquement si la méthode est POST
    if request.method == "POST":
        user = request.user
        professur_user_id = user.id

        # Extraction et validation du paramètre 'eleve'
        eleve = request.POST.get('eleve')
        match = re.match(r'\[(\d+)\]', eleve)
        if not match:
            return JsonResponse({"error": "Format d'élève invalide."}, status=400)

        eleve_id = int(match.group(1))

        try:
            # Vérification de l'existence de l'élève dans `Mes_eleves`
            mon_eleve = get_object_or_404(Mes_eleves, pk=eleve_id, user=request.user, is_active=True)
            eleve_user = get_object_or_404(Eleve, id=mon_eleve.eleve_id)

            # Récupération de l'ID de l'email téléchargé et d'Email_detaille associé
            dernier_email_telecharge_id = Email_telecharge.objects.filter(
                user_id=eleve_user.user_id, user_destinataire=professur_user_id
            ).values_list('id', flat=True).first()

            if not dernier_email_telecharge_id:
                return JsonResponse({"error": "Aucun email téléchargé trouvé pour cet élève."}, status=404)

            # Récupération des détails de cours depuis `Email_detaille`
            email_detaille = Email_detaille.objects.filter(email_id=dernier_email_telecharge_id).first()
            if not email_detaille:
                return JsonResponse({"error": "Aucun Email_detaille associé trouvé."}, status=404)

            # Mapping et récupération des valeurs `format`, `matiere`, `niveau`, `prix_heure`
            format_cle = {
                'a_domicile': 'Cours à domicile',
                'webcam': 'Cours par webcam',
                'stage': 'Stage pendant les vacances',
                'stage_webcam': 'Stage par webcam'
            }.get(email_detaille.format_cours, "")

            # Récupération de `matiere_id` et `niveau_id`
            matiere_id = Matiere.objects.filter(matiere=email_detaille.matiere).values_list('id', flat=True).first()
            niveau_id = Niveau.objects.filter(niveau=email_detaille.niveau).values_list('id', flat=True).first()

            # Vérification des valeurs récupérées
            if not matiere_id or not niveau_id:
                return JsonResponse({"error": "Matière ou niveau non trouvé."}, status=404)

            # Récupération ou création de `Prof_mat_niv`
            prof_mat_niv = Prof_mat_niv.objects.filter(
                user_id=professur_user_id, matiere_id=matiere_id, niveau_id=niveau_id
            ).first()
            
            if not prof_mat_niv:
                return JsonResponse({"error": "Professeur, matière ou niveau introuvable."}, status=404)

            # Récupération du prix par heure
            prix_heure = Prix_heure.objects.filter(
                user_id=professur_user_id, prof_mat_niv_id=prof_mat_niv.id, format=format_cle
            ).values_list('prix_heure', flat=True).first()
            prix_heure = str(prix_heure) if prix_heure else ""

            # Création du dictionnaire de réponse
            para_defaut_cours = {
                "format": format_cle,
                "matiere": email_detaille.matiere,
                "niveau": email_detaille.niveau,
                "prix_heure": prix_heure
            }
            
            response_data['para_defaut_cours'] = para_defaut_cours
            return JsonResponse(response_data)

        except ObjectDoesNotExist:
            return JsonResponse({"error": "Élève non valide sélectionné."}, status=400)

    return JsonResponse({"error": "Requête invalide."}, status=400)





def ajouter_cours(request):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin')
    professur_user_id = user.id
    
    # Récupération des matières et niveaux pour le formulaire
    matieres = Matiere.objects.all()
    niveaux = Niveau.objects.all()

    # Obtenir les élèves actifs de l'utilisateur actuel
    mes_eleves = Mes_eleves.objects.filter(user=user, is_active=True).select_related('user', 'eleve').annotate(
        eleve_nom=Concat(
            Value('['), F('id'), Value('] '), 
            F('eleve__user__last_name'), Value(' '), 
            F('eleve__user__first_name'), 
            Value(', Téléphone: '), F('eleve__numero_telephone'),
            Value(', adresse: '), F('eleve__adresse'),
            output_field=CharField()
        )
    ).values_list('eleve_nom', flat=True)
    # Contexte de la page à renvoyer au template
    context = {
        'matieres': matieres,
        'niveaux': niveaux,
        'mes_eleves': mes_eleves,
    }

    # Vérification si la requête est un POST avec le bouton 'Enregistrer' cliqué
    if request.method == 'POST' and 'btn_enr' in request.POST:
        eleve = request.POST.get('eleve')
        format = request.POST.get('format')
        matiere = request.POST.get('matiere')
        niveau = request.POST.get('niveau')
        prix_heure = request.POST.get('prix_heure')

        # Mise à jour du contexte avec les valeurs soumises
        context.update({
            'eleve': eleve,
            'format': format,
            'matiere': matiere,
            'niveau': niveau,
            'prix_heure': prix_heure,
        })

        # Vérification que tous les champs requis sont remplis
        if not all([eleve, format, matiere, niveau, prix_heure]):
            messages.error(request, "Il faut remplir tous les champs")
            return render(request, 'accounts/ajouter_cours.html', context)
        
        # Extraction de l'ID de l'élève à partir de la chaîne sélectionnée
        match = re.match(r'\[(\d+)\]', eleve)
        if not match:
            messages.error(request, "Format d'élève invalide.")
            return render(request, 'accounts/ajouter_cours.html', context)

        eleve_id = int(match.group(1))
        try:
            # Vérification de l'existence de l'élève
            mon_eleve = Mes_eleves.objects.get(pk=eleve_id, user=user, is_active=True)
        except ObjectDoesNotExist:
            messages.error(request, f'Élève non valide sélectionné. eleve_id= {eleve_id}')
            return render(request, 'accounts/ajouter_cours.html', context)
        

        # Extraction et conversion du prix en décimal
        try:
            prix_dec = Decimal(prix_heure[:-4]).quantize(Decimal('0.00'))
        except (InvalidOperation, ValueError):
            messages.error(request, f"Erreur lors de la conversion du prix '{prix_heure[:-4]}' en décimal. Contactez le programmeur.")
            return render(request, 'accounts/ajouter_cours.html', context)
        
        is_active = 'is_active' in request.POST
        
        # Création et enregistrement du cours
        cours = Cours(
            user=user,
            mon_eleve=mon_eleve,
            format_cours=format,
            matiere=matiere,
            niveau=niveau,
            prix_heure=prix_dec,
            is_active=is_active
        )
        cours.save()

        messages.success(request, "L'enregistrement du cours est effectué.")
        return redirect('ajouter_horaire', cours_id=cours.id)
    
    # Affichage du formulaire
    return render(request, 'accounts/ajouter_cours.html', context)

from django.utils.dateparse import parse_date
from datetime import datetime

def ajouter_horaire(request, cours_id): # Ajouter des séance de cours près défini
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin')

    # Récupérer le cours actif associé à l'ID fourni
    mon_cours = get_object_or_404(Cours, id=cours_id, is_active=True)
    mon_eleve_id = mon_cours.mon_eleve.eleve.id

    # Récupérer l'élève associé au cours pour le professeur actuel
    mon_eleve = Mes_eleves.objects.filter(
        user=user, is_active=True, eleve_id=mon_eleve_id
    ).select_related('eleve').first()

    # Vérifier que l'élève existe
    if not mon_eleve:
        messages.error(request, "Aucun élève trouvé pour ce cours.")
        return redirect('compte_prof')

    # Formatage des dates de modification
    maj_eleve_format = mon_eleve.date_modification.strftime('%d/%m/%y')
    maj_cours_format = mon_cours.date_modification.strftime('%d/%m/%y')

    # Annoter l'élève avec les détails de contact formatés
    mon_eleve = Mes_eleves.objects.filter(id=mon_eleve.id).annotate(
        eleve_nom=Concat(
            Value(f'[Màj le: {maj_eleve_format}], '),
            F('eleve__user__last_name'), Value(' '), F('eleve__user__first_name'),
            Value(', Téléphone: '), F('eleve__numero_telephone'),
            Value(', Adresse: '), F('eleve__adresse'),
            output_field=CharField()
        )
    ).first()

    # Annoter le cours avec les détails formatés
    detaille_cours = Cours.objects.filter(id=cours_id).annotate(
        eleve_cours=Concat(
            Value(f'[Màj le: {maj_cours_format}], '),
            Value('Format du cours: '), F('format_cours'), 
            Value(', Matière: '), F('matiere'),
            Value(', Niveau: '), F('niveau'),
            Value(", Prix de l'heure: "), F('prix_heure'), Value(" €"),
            output_field=CharField()
        )
    ).first()

    # Vérifier que les détails du cours existent
    if not detaille_cours:
        messages.error(request, "Aucun détail de cours trouvé.")
        return redirect('compte_prof')

    # Initialiser les horaires par défaut
    horaires = [{'date': '', 'debut': '', 'fin': '', 'contenu': '', 'statut': 'En attente'} for _ in range(4)]

    if request.method == 'POST' and 'btn_enr' in request.POST:
        valid_entries = 0
        valide_heure = True
        valide_format = True

        # Parcourir les 4 horaires possibles pour validation et ajout
        horaires_recup=[]
        for i in range(1, 5):
            date = request.POST.get(f'date{i}', '')
            debut = request.POST.get(f'debut{i}', '')
            fin = request.POST.get(f'fin{i}', '')
            contenu = request.POST.get(f'contenu{i}', '')
            statut = request.POST.get(f'statut{i}', 'En attente')
            horaires_recup.append({'date': date, 'debut': debut, 'fin': fin, 'contenu': contenu, 'statut': statut})

            # testes de validation
            if date and debut and fin:
                valid_entries += 1
                # tester le format des dates, à améliorer cette logique d'enregistrement

                try:
                    # si la convertion est réussie
                    date_01 = datetime.strptime(date, '%d/%m/%Y') # date_01 juste pour le try seulement
                    debut_01 = datetime.strptime(debut, '%H:%M')
                    fin_01 = datetime.strptime(fin, '%H:%M')
                except ValueError:
                    valide_format = False
                if valide_format:
                    if datetime.strptime(debut, '%H:%M') >= datetime.strptime(fin, '%H:%M')  : valide_heure = False

        horaires = horaires_recup # pour remaitre au template les anciens données si l'enregistrement n'est pas réuci
        # Si aucun horaire n'est valide, afficher un message d'erreur
        if valid_entries == 0:
            messages.error(request, "Veuillez remplir au moins les champs date, début, fin, et statut pour une ligne.")
        if not valide_heure :
            messages.error(request, "L'heure de début doit être inférieur à l'heure de fin.")
        if not valide_format :
            messages.error(request, "Le format de l'heure ou de la date est non valide,<br> format date doit être: JJ/MM/AA et l'heure HH:MM.")
         
        if valid_entries != 0 and valide_heure and valide_format:
            # Enregistrer les horaires valides
            for horaire in horaires:
                if horaire['date'] and horaire['debut'] and horaire['fin']: #éviter les lignes vide
                    seance = Horaire(
                        cours=mon_cours,
                        contenu=horaire['contenu'],
                        statut_cours=horaire['statut'],
                    )
                    seance.set_date_obtenu_from_str(horaire['date'])
                    seance.set_heure_debut_from_str(horaire['debut'])
                    seance.set_heure_fin_from_str(horaire['fin'])
                    seance.calculer_duree()
                    seance.save()

            messages.success(request, "Enregistrement réussi.")
            # Réinitialiser les horaires par défaut pour efacer les ancien données puisque l'enregistrement est réuci
            horaires = [{'date': '', 'debut': '', 'fin': '', 'contenu': '', 'statut': 'En attente'} for _ in range(4)]

    # Gestion de la suppression d'un horaire
    sup_enr_keys = [key for key in request.POST.keys() if key.startswith('btn_sup_')]
    if sup_enr_keys:
        horaire_id = int(sup_enr_keys[0].split('btn_sup_')[1])
        try:
            horaire_to_delete = Horaire.objects.get(id=horaire_id)
            horaire_to_delete.delete()
            messages.success(request, f"Horaire avec ID {horaire_id} supprimé avec succès.")
        except Horaire.DoesNotExist:
            messages.error(request, f"Horaire avec ID {horaire_id} non trouvé.")

    # Récupérer les horaires enregistrés pour ce cours avec la logique de 'statut_reglement'
    enr_horaires = [
        {
            'date': enr.date_cours.strftime('%d/%m/%Y'),
            'debut': enr.heure_debut,
            'fin': enr.heure_fin,
            'contenu': enr.contenu,
            'statut': enr.statut_cours,
            'payment_id': enr.payment_id,
            'demande_paiement_id': enr.demande_paiement_id,
            'statut_reglement': (
                                    'Réglé' if enr.payment_id else
                                    'Règlement en cours' if enr.demande_paiement_id else
                                    'Non réglé'
                                ),
            'id': enr.id
        }
        for enr in Horaire.objects.filter(cours=mon_cours)
    ]


    # Contexte pour le rendu du template
    context = {
        'mon_eleve': mon_eleve,
        'detaille_cours': detaille_cours,
        'horaires': horaires,
        'enr_horaires': enr_horaires,
    }
    return render(request, 'accounts/ajouter_horaire.html', context)

def modifier_cours(request, cours_id):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin') 
    mon_cours = Cours.objects.get(id=cours_id)
    is_activ_first = mon_cours.is_active
    prix_heure = str(mon_cours.prix_heure)  # pour que le masque de saisie puisse l'interpréter correctement
    eleve = mon_cours.mon_eleve.eleve
    
    
    # Récupération des matières et niveaux pour le formulaire
    matieres = Matiere.objects.all()
    niveaux = Niveau.objects.all()

    # Contexte de la page à renvoyer au template
    context = {
        'matieres': matieres,
        'niveaux': niveaux,
        'mon_cours': mon_cours,
        'eleve': eleve,
        'prix_heure': prix_heure,
    }

    # Vérification si la requête est un POST avec le bouton 'Enregistrer' cliqué
    if request.method == 'POST' and 'btn_enr' in request.POST:
        format = request.POST.get('format')
        matiere = request.POST.get('matiere')
        niveau = request.POST.get('niveau')
        prix_heure = request.POST.get('prix_heure')
        prix_dec = Decimal(prix_heure[:-4]).quantize(Decimal('0.00'))
        mon_cours.prix_heure = prix_dec
        mon_cours.format_cours = format
        mon_cours.matiere = matiere
        mon_cours.niveau = niveau
        is_activ_last = 'is_active' in request.POST

        if is_activ_first and not is_activ_last:
            # Récupérer tous les statuts des demandes de paiement liés au cours
            details_demande_paiement = Detail_demande_paiement.objects.filter(cours=mon_cours)
            Statut_demandes = [
                detail.demande_paiement.statut_demande 
                for detail in details_demande_paiement
            ]

            # Vérification des statuts
            for statut in Statut_demandes:
                if statut not in ['Annuler', 'Réaliser']:
                    messages.error(request, "Au moins une demande de paiement liée à ce cours est en attente ou en cours, ce qui empêche sa désactivation.")
                    return render(request, 'accounts/modifier_cours.html', context)

            # Si tous les statuts sont valides, désactiver le cours
            mon_cours.is_active = is_activ_last
            mon_cours.save()
            return redirect('modifier_cours', cours_id=cours_id)

        if not is_activ_first and is_activ_last:
            mes_eleves = Mes_eleves.objects.get(eleve=eleve, user=user)
            if not mes_eleves.is_active:
                messages.error(request, "L'élève lié au cours est inactif, donc le cours ne peut être activé.")
                return render(request, 'accounts/modifier_cours.html', context)

        mon_cours.is_active = is_activ_last
        mon_cours.save()
        return redirect('modifier_cours', cours_id=cours_id)

    # Affichage du formulaire
    return render(request, 'accounts/modifier_cours.html', context)



def liste_mes_eleve(request):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin') 
    is_active = True # par défaut
    if 'btn_active' in request.POST: is_active = True
    if 'btn_non_active' in request.POST: is_active = False
    # Récupérer les informations des élèves actifs associés à l'utilisateur connecté
    mes_eleves = Mes_eleves.objects.filter(user=user, is_active=is_active)
    

    # Si aucun élève n'est trouvé, renvoyer un message d'erreur
    if not mes_eleves.exists():
        messages.error(request, "Aucun élève trouvé pour ce cours.")
        return redirect('compte_prof')  # Redirection vers la vue de compte du professeur

    # Si la requête est de type POST, traiter les actions des boutons
    if request.method == 'POST':
        # Recherche des clés commençant par 'btn_cours_' dans les données POST
        cours_keys = [key for key in request.POST.keys() if key.startswith('btn_cours_')]
        if cours_keys:
            # Prendre le premier bouton cliqué correspondant à un cours
            btn_key = cours_keys[0]
            # Extraire l'ID de l'élève à partir de la clé du bouton
            mon_eleve_id = int(btn_key.split('btn_cours_')[1])

            try:
                # Récupérer l'élève en utilisant l'ID extrait
                mon_eleve = Mes_eleves.objects.get(id=mon_eleve_id)
                
                # Filtrer les cours associés à cet élève
                cours = Cours.objects.filter(mon_eleve=mon_eleve)
                
                if not cours.exists():
                    messages.error(request, f"Il n'y a pas de cours pour l'élève {mon_eleve.eleve.user.last_name}.")
                    return redirect('compte_prof')  # Redirection si aucun cours n'est trouvé

                # Redirection vers la vue 'cours_mon_eleve' avec l'ID de l'élève
                return redirect('cours_mon_eleve', eleve_id=mon_eleve_id)

            except Mes_eleves.DoesNotExist:
                # Message d'erreur si l'élève n'est pas trouvé
                messages.error(request, "Élève non trouvé.")
                return redirect('compte_prof')

        # Recherche des clés commençant par 'btn_plus_' pour gérer une autre action
        reglement_keys = [key for key in request.POST.keys() if key.startswith('btn_reglement_')]
        if reglement_keys:
            # Prendre le premier bouton cliqué correspondant à une demande de règlement
            btn_key = reglement_keys[0]
            # Extraire l'ID de l'élève
            mon_eleve_id = int(btn_key.split('btn_reglement_')[1])
            # Redirection vers la vue 'demande_reglement' avec l'ID de l'élève
            return redirect('demande_reglement', eleve_id=mon_eleve_id)
        # Recherche des clés commençant par 'btn_eleve_' pour gérer une autre action
        mon_eleve_keys = [key for key in request.POST.keys() if key.startswith('btn_eleve_')]
        if mon_eleve_keys:
            # Prendre le premier bouton cliqué correspondant à une demande de règlement
            btn_key = mon_eleve_keys[0]
            # Extraire l'ID de l'élève
            mon_eleve_id = int(btn_key.split('btn_eleve_')[1])
            # Redirection vers la vue 'demande_reglement' avec l'ID de l'élève
            return redirect('modifier_mes_eleve', eleve_id=mon_eleve_id)

    # Passer les informations des élèves au contexte du template
    context = {
        'mes_eleves': mes_eleves,
        'is_active': is_active,
    }
    return render(request, 'accounts/liste_mes_eleve.html', context)


def cours_mon_eleve(request, eleve_id):
    """
    Affiche les cours associés à un élève spécifique et gère la redirection vers les horaires du cours.
    """

    # Récupère l'utilisateur actuel
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin')
    
    if 'btn_non_active' in request.POST:
        request.session['is_active'] = False
    if 'btn_active' in request.POST:
        request.session['is_active'] = True
    
    # Récupère l'élève correspondant à l'ID fourni. Si l'élève n'existe pas ou n'est pas actif, renvoie une erreur 404.
    mon_eleve = get_object_or_404(Mes_eleves, id=eleve_id, is_active=True)
    
    # Récupère tous les cours actifs associés à cet élève
    mes_cours = Cours.objects.filter(mon_eleve=mon_eleve, is_active=request.session.get('is_active', True))

    # Si aucun cours n'est trouvé pour cet élève, affiche un message d'erreur et redirige vers la page 'compte_prof'
    if not mes_cours.exists():
        messages.error(request, "Aucun cours trouvé pour cet élève.")
        return redirect('compte_prof')
    
    # Gestion des soumissions du formulaire
    if request.method == 'POST':
        # Récupère toutes les clés du formulaire POST qui commencent par 'btn_horaire_'
        mon_cours_keys = [key for key in request.POST.keys() if key.startswith('btn_horaire_')]
        
        if mon_cours_keys:
            # On prend la première clé trouvée
            btn_key = mon_cours_keys[0]
            # Extrait l'ID du cours de la clé
            cours_id = int(btn_key.split('btn_horaire_')[1])
            
            try:
                # Récupère le cours correspondant à l'ID fourni
                mon_cours = Cours.objects.get(id=cours_id, is_active=request.session.get('is_active', True))
                
                # Redirige vers la vue 'horaire_cours_mon_eleve' en passant l'ID du cours
                return redirect('horaire_cours_mon_eleve', cours_id=cours_id)
            
            except Cours.DoesNotExist:
                # Si le cours n'existe pas, affiche un message d'erreur et redirige vers la page 'compte_prof'
                messages.error(request, "Cours non trouvé.")
                return redirect('compte_prof')  # Remplacez 'compte_prof' par la vue de redirection appropriée

    # Prépare le contexte avec les cours de l'élève et les informations de l'élève
    context = {
        'mes_cours': mes_cours,
        'mon_eleve': mon_eleve,
    }
    
    # Rend le template 'cours_mon_eleve' avec le contexte préparé
    return render(request, 'accounts/cours_mon_eleve.html', context)

def horaire_cours_mon_eleve(request, cours_id):
    mon_cours = Cours.objects.get(id=cours_id)
    
    # Gestion des requêtes POST
    if request.method == 'POST':
        # Gestion de l'ajout d'un horaire
        if 'btn_ajout' in request.POST:
            return redirect('ajouter_horaire', cours_id=cours_id)
        
        # Gestion de la modification du prix de l'heure
        if 'btn_prix' in request.POST:
            prix_heure = request.POST.get('prix_heure', None)
            prix_str = prix_heure[:-4] if prix_heure else None
            if prix_str and prix_str != '0':
                prix_heure_dec = Decimal(prix_str).quantize(Decimal('0.00'))
            else:
                prix_heure_dec = mon_cours.prix_heure
            mon_cours.prix_heure = prix_heure_dec
            mon_cours.save()
            messages.success(request, "Le prix de l'heure est modifié avec succès.")
            return redirect('horaire_cours_mon_eleve', cours_id=cours_id )

        # Gestion de la modification du prix de l'heure
        if 'btn_activer' in request.POST:
            
            if mon_cours.is_active:  
                
                # if is_activ_first and not is_activ_last:
                # Récupérer tous les statuts des demandes de paiement liés au cours
                details_demande_paiement = Detail_demande_paiement.objects.filter(cours=mon_cours)
                Statut_demandes = [
                    detail.demande_paiement.statut_demande 
                    for detail in details_demande_paiement
                ]
                teste = True
                # Vérification des statuts
                for statut in Statut_demandes:
                    if statut not in ['Annuler', 'Réaliser']:
                        messages.error(request, "Au moins une demande de paiement liée à ce cours est en attente ou en cours, ce qui empêche sa désactivation.")
                        teste = False
                        break

                # Si tous les statuts sont valides, désactiver le cours
                if teste:
                    mon_cours.is_active = False
                    mon_cours.save()
                    
        
            else: mon_cours.is_active = True
            mon_cours.save()
            if not  mon_cours.is_active: messages.info(request, "Le cours est désactivé.")
            else: messages.info(request, "Le cours est activé.")
           

        # Gestion de la suppression d'un horaire
        sup_enr_keys = [key for key in request.POST.keys() if key.startswith('btn_sup_')]
        if sup_enr_keys:
            btn_key = sup_enr_keys[0]
            horaire_id = int(btn_key.split('btn_sup_')[1])
            try:
                horaire_to_delete = Horaire.objects.get(id=horaire_id)
                horaire_to_delete.delete()
                messages.success(request, f"Horaire avec ID {horaire_id} supprimé avec succès.")
            except Horaire.DoesNotExist:
                messages.error(request, f"Horaire avec ID {horaire_id} non trouvé.")
        
        # Gestion de la modification d'un horaire
        modif_enr_keys = [key for key in request.POST.keys() if key.startswith('btn_modif_')]
        if modif_enr_keys:
            btn_key = modif_enr_keys[0]
            horaire_id = int(btn_key.split('btn_modif_')[1])
            try:
                horaire_enr = Horaire.objects.get(id=horaire_id)
                date_cours = request.POST.get(f'date_{horaire_id}', horaire_enr.date_cours.strftime('%d/%m/%Y'))
                heure_debut = request.POST.get(f'debut_{horaire_id}', horaire_enr.heure_debut)
                heure_fin = request.POST.get(f'fin_{horaire_id}', horaire_enr.heure_fin)
                contenu = request.POST.get(f'contenu_{horaire_id}', horaire_enr.contenu)
                statut_cours = request.POST.get(f'statut_{horaire_id}', horaire_enr.statut_cours)
                
                # Validation des heures
                if date_cours and heure_debut and heure_fin:
                    heure_debut_conv = datetime.strptime(heure_debut, '%H:%M')
                    heure_fin_conv = datetime.strptime(heure_fin, '%H:%M')
                    if heure_debut_conv >= heure_fin_conv:
                        messages.error(request, f"Début de la séance {heure_debut} doit être inférieur à fin de la séance {heure_fin}.")
                        return render(request, 'accounts/horaire_cours_mon_eleve.html', {
                            'mon_cours': mon_cours,
                            'mon_eleve': mon_eleve,
                            'enr_horaires': enr_horaires,
                        })
                
                # Mise à jour de l'horaire
                horaire_enr.set_date_obtenu_from_str(date_cours)
                horaire_enr.set_heure_debut_from_str(heure_debut)
                horaire_enr.set_heure_fin_from_str(heure_fin)
                horaire_enr.contenu = contenu
                horaire_enr.statut_cours = statut_cours
                horaire_enr.calculer_duree()
                horaire_enr.save()
                messages.success(request, f"Horaire avec ID {horaire_id} modifié avec succès.")
                
            except Horaire.DoesNotExist:
                messages.error(request, f"Horaire avec ID {horaire_id} non trouvé.")
    """
    Gère les opérations de suppression, modification, et ajout des horaires pour un cours spécifique.
    """

    # Initialiser les variables nécessaires
    mon_cours = get_object_or_404(Cours, id=cours_id)
    mon_eleve = get_object_or_404(Mes_eleves, id=mon_cours.mon_eleve_id, is_active=True)
    
    # Récupère tous les horaires associés au cours
    enr_horaires = []
    enrs = Horaire.objects.filter(cours=mon_cours)
    for enr in enrs:
        # Déterminer le statut du règlement
        if enr.payment_id:
            statut_reglement = 'Réglé'
        elif enr.demande_paiement_id:
            statut_reglement = 'Règlement en cours'
        else:
            statut_reglement = 'Non réglé'
        
        # Ajouter l'horaire à la liste avec les informations et le statut de règlement
        enr_horaires.append({
            'date': enr.date_cours.strftime('%d/%m/%Y'),  # Formatage de la date
            'debut': enr.heure_debut,                      # Heure de début
            'fin': enr.heure_fin,                          # Heure de fin
            'contenu': enr.contenu,                        # Contenu du cours
            'statut': enr.statut_cours,                    # Statut du cours
            'id': enr.id,                                  # ID de l'horaire
            'statut_reglement': statut_reglement,          # Statut du règlement
        })
    # Prépare le contexte pour le rendu de la vue
    context = {
        'mon_cours': mon_cours,
        'mon_eleve': mon_eleve,
        'enr_horaires': enr_horaires,
    }
    
    # Renvoie le template avec le contexte préparé
    return render(request, 'accounts/horaire_cours_mon_eleve.html', context)


def liste_seance_cours(request):
    """
    Affiche la liste des séances de cours en attente pour l'utilisateur actuel
    et gère la redirection vers la page de détail d'une séance spécifique si demandé.
    """
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin')   # Récupère l'utilisateur actuel
    is_active = True # par défaut
    if 'btn_active' in request.POST: is_active = True
    if 'btn_non_active' in request.POST: is_active = False

    # Filtre les horaires en attente associés aux cours actifs pour l'utilisateur actuel
    liste_horaires = Horaire.objects.filter(
        statut_cours="En attente",
        cours__is_active=is_active,
        cours__mon_eleve__is_active=True,
        cours__user=user  # Assure que les cours appartiennent à l'utilisateur (professeur) actuel
    ).order_by('date_cours', 'heure_debut')

    # Vérifie si un bouton de détail a été activé
    detaille_enr_keys = [key for key in request.POST.keys() if key.startswith('btn_detaille_')]
    if detaille_enr_keys:
        btn_key = detaille_enr_keys[0]  # Récupère la clé du bouton activé
        horaire_id = int(btn_key.split('btn_detaille_')[1])  # Extrait l'ID de l'horaire de la clé
        try:
            # Récupère l'horaire correspondant à l'ID
            horaire_enr = Horaire.objects.get(id=horaire_id)
            cours_id = horaire_enr.cours_id  # Récupère l'ID du cours associé à l'horaire
            # Redirige vers la page de détail de l'horaire
            return redirect('horaire_cours_mon_eleve', cours_id=cours_id)
        except Horaire.DoesNotExist:
            # Affiche un message d'erreur si l'horaire n'existe pas
            messages.error(request, f"Horaire avec ID {horaire_id} non trouvé.")

    # Rende la vue avec la liste des horaires en attente
    return render(request, 'accounts/liste_seance_cours.html', {'liste_horaires': liste_horaires, 'is_active': is_active})



def demande_reglement(request, eleve_id):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin') 
    
    # Récupérer l'élève actif pour l'utilisateur actuel
    mon_eleve = get_object_or_404(Mes_eleves, id=eleve_id, user=user, is_active=True)
    
    # Récupérer tous les cours actifs associés à cet élève
    mes_cours = Cours.objects.filter(mon_eleve_id=eleve_id, is_active=True)
    
    # Préparer la liste des horaires pour chaque cours
    enr_horaires = [
        {
            'cours_id': mon_cours.id,
            'date': enr.date_cours.strftime('%d/%m/%Y'),
            'debut': enr.heure_debut,
            'fin': enr.heure_fin,
            'contenu': enr.contenu,
            'statut': enr.statut_cours,
            'id': enr.id,
            'payment_id': enr.payment_id,
            'demande_paiement_id': enr.demande_paiement_id,
        }
        for mon_cours in mes_cours
        for enr in Horaire.objects.filter(cours=mon_cours)
    ]

    # Contexte pour le rendu du template
    context = {
        'mon_eleve': mon_eleve,
        'mes_cours': mes_cours,
        'enr_horaires': enr_horaires,
    }

    # Gestion du formulaire de demande de règlement
    if request.method == 'POST' and 'btn_reglement' in request.POST:
        # Récupérer les horaires sélectionnés à partir des cases cochées
        chk_keys = [key for key in request.POST.keys() if key.startswith('chk_')]
        if chk_keys:
            # Extraire les IDs des horaires sélectionnés
            selected_horaires = [int(chk_key.split('chk_')[1]) for chk_key in chk_keys]
            request.session['selected_horaires'] = selected_horaires
            # for id in selected_horaires:
            #     messages.info(request, f"id= {id} ")
            return redirect('declaration_cours', eleve_id=eleve_id)
        else:
            messages.error(request, "Pour déclarer un cours et demander le paiement, vous devez cocher au moins une case active")

    # Rendre le template avec le contexte
    return render(request, 'accounts/demande_reglement.html', context)




def declaration_cours(request, eleve_id):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin') 
    professeur = Professeur(user=user)
    
    # Récupérer l'élève actif associé à l'utilisateur
    mon_eleve = get_object_or_404(Mes_eleves, id=eleve_id, user=user, is_active=True) # de la table Mes_eleves
    eleve = get_object_or_404(Eleve, id=mon_eleve.eleve.id) # de la table eleve
    
    # Récupérer le parent de l'élève, s'il existe
    parent = getattr(eleve.user, 'parent', None)

    # Récupérer tous les cours actifs associés à cet élève
    cours_actifs = Cours.objects.filter(mon_eleve=mon_eleve, is_active=True)
    
    # Obtenir les horaires sélectionnés depuis la session
    selected_horaires = request.session.get('selected_horaires', [])
    # for id in selected_horaires:
    #     messages.info(request, f"id= {id} ")
    
    montant_total = Decimal('0.00')  # Initialiser le montant total

    if selected_horaires:
        # Récupérer les horaires associés aux cours actifs et calculer le montant pour chaque horaire
        horaires_groupes = Horaire.objects.filter(id__in=selected_horaires, cours__in=cours_actifs)\
            .values('date_cours', 'heure_debut', 'heure_fin', 'cours__matiere', 'duree', 'cours__prix_heure', 'statut_cours', 'contenu', 'id')\
            .annotate(
                montant=ExpressionWrapper(
                    F('duree') * F('cours__prix_heure'),
                    output_field=fields.DecimalField(decimal_places=2, max_digits=10)
                )
            )\
            .order_by('date_cours')
        # for hor in horaires_groupes:
        #     messages.info(request, f"hor.id = {hor['id']}")
        # Calculer la somme des montants
        montant_total = horaires_groupes.aggregate(
            total_montant=Sum('montant')
        )['total_montant'] or Decimal('0.00')

        # Arrondir le montant total à deux chiffres après la virgule
        montant_total = montant_total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        # Passer les informations au contexte
        context = {
            'mon_eleve': mon_eleve,
            'cours_actifs': cours_actifs,
            'horaires_groupes': horaires_groupes,
            'montant_total': montant_total,
            'parent': parent,
            'professeur': professeur,
        }
        if request.method == 'POST' and 'btn_declaration' in request.POST:
            # Validation des données
            if not montant_total or montant_total <= 0:
                messages.error(request, "Une erreur s'est produite lors du calcul du montant total à régler. Veuillez contacter le programmeur.")
                return render(request, 'accounts/declaration_cours.html', context)
            
            # pas besion car les données, les données existent déjà dans la session, et dans horaires_groupes, en plus le code est faux car il ne tient compte que d'un seule enregistrement
            # Vérification de l'existance des enregistrements horaires (pas besion)
            matiere_keys = [key for key in request.POST if key.startswith('matiere_')]
            for matiere_key in matiere_keys:
                try:
                    horaire_id = int(matiere_key.split('matiere_')[1])
                    horaire = Horaire.objects.get(id=horaire_id)
                except (ValueError, Horaire.DoesNotExist):
                    messages.error(request, "Une erreur s'est produite lors de la récupération des enregistrements horaires. Veuillez contacter le programmeur.")
                    return render(request, 'accounts/declaration_cours.html', context)
            
            # Envoi de l'email si nécessaire
            sujet = request.POST.get('sujet', 'Demande de règlement de cours')
            text_email = request.POST.get('text_email', None)
            if sujet or text_email:
                email_prof = professeur.user.email
                destinations = ['prosib25@gmail.com', eleve.user.email]
                if parent and parent.email_parent:
                    destinations.append(parent.email_parent)

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
                        email_prof,
                        destinations,
                        fail_silently=False,
                    )
                    messages.success(request, "L'email de la demande de règlement a été envoyé avec succès.")
                except Exception as e:
                    messages.error(request, f"Une erreur s'est produite lors de l'envoi de l'email : {str(e)}")
                
                # Enregistrement de l'email envoyé
                email_telecharge = Email_telecharge(
                    user=user, email_telecharge=email_prof, text_email=text_email,
                    user_destinataire=eleve.user.id, sujet=sujet
                )
                email_telecharge.save()

            # Enregistrement de la demande de paiement
            demande_paiement = Demande_paiement(
                user=user, mon_eleve=mon_eleve, eleve=eleve, montant=montant_total, email=email_telecharge.id if email_telecharge else None
            )
            demande_paiement.save()

            # Enregistrement des détails de la demande de paiement
            for matiere_key in matiere_keys: # pas besion car les enregistrements existent dans la session et dans horaires_groupes
                horaire_id = int(matiere_key.split('matiere_')[1])
                # messages.info(request, f"horaire_id = {horaire_id} ")
                horaire = Horaire.objects.get(id=horaire_id)
                detail_demande_paiement = Detail_demande_paiement(
                    demande_paiement=demande_paiement, cours=horaire.cours, 
                    prix_heure=horaire.cours.prix_heure, horaire=horaire
                )
                detail_demande_paiement.save()

                # Mettre à jour l'état de l'horaire avec l'ID de la demande de paiement
                horaire.demande_paiement_id = demande_paiement.id
                horaire.save()

            messages.success(request, "La demande de règlement et ses détails ont été enregistrés avec succès.")
            
            # Nettoyage de la session
            request.session.pop('selected_horaires', None)
            return redirect('compte_prof')
    
    else:
        messages.error(request, 'Le cours est déjà déclaré')
        return redirect('compte_prof')
    

    # Passer les informations au contexte
    context = {
        'mon_eleve': mon_eleve,
        'cours_actifs': cours_actifs,
        'horaires_groupes': horaires_groupes,
        'montant_total': montant_total,
        'parent': parent,
        'professeur': professeur,
    }
    
    return render(request, 'accounts/declaration_cours.html', context)



def liste_declaration_cours(request):
    # Obtenir l'utilisateur actuel
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin')
    statut_demande = 'En cours'
    if 'btn_en_cours' in request.POST: statut_demande = 'En cours'
    if 'btn_attente' in request.POST: statut_demande = 'En attente'
    if 'btn_contester' in request.POST: statut_demande = 'Contester'
    if 'btn_annuler' in request.POST: statut_demande = 'Annuler'
    if 'btn_regler' in request.POST: statut_demande = 'Réaliser'
    # Filtrer les demandes de paiement associées à l'utilisateur, en excluant celles qui sont annulées
    demande_paiements = Demande_paiement.objects.filter(user=user, statut_demande=statut_demande)

    if 'btn_tous' in request.POST: demande_paiements = Demande_paiement.objects.filter(user=user)
    
    # Construire la liste des cours déclarés avec les détails nécessaires
    cours_declares = [
        {
            'id': enr.id,
            'date_modification': enr.date_modification.strftime('%d/%m/%Y'),
            'mon_eleve': enr.mon_eleve,
            'montant': enr.montant,
            'statut_demande': enr.statut_demande,
            'vue_le': enr.vue_le,
            'email_eleve': enr.email_eleve,
        }
        for enr in demande_paiements
    ]

    # Gérer les soumissions POST, en particulier pour le bouton "détaille"
    if request.method == 'POST':
        # Rechercher la clé correspondant à l'un des boutons de détail soumis
        detaille_enr_key = next((key for key in request.POST if key.startswith('btn_detaille_')), None)
        if detaille_enr_key:
            # Extraire l'ID de la demande de paiement à partir de la clé
            demande_paiement_id = int(detaille_enr_key.split('btn_detaille_')[1])
            try:
                # Récupérer la demande de paiement correspondante
                demande_enr = Demande_paiement.objects.get(id=demande_paiement_id)
                # Rediriger vers la vue détaillée de la demande de règlement
                return redirect('detaille_demande_reglement', demande_paiement_id=demande_enr.id)
            except Demande_paiement.DoesNotExist:
                # Afficher un message d'erreur si la demande n'existe pas
                messages.error(request, f"La demande de paiement avec l'ID={demande_paiement_id} n'a pas été trouvée.")

    # Passer les cours déclarés au template pour l'affichage
    context = {'cours_declares': cours_declares}
    return render(request, 'accounts/liste_declaration_cours.html', context)


def detaille_demande_reglement(request, demande_paiement_id):
    # Récupérer la demande de paiement et les objets associés
    demande_paiement = get_object_or_404(Demande_paiement, id=demande_paiement_id)
    eleve = demande_paiement.eleve
    parent = getattr(eleve.user, 'parent', None)

    # Récupérer les détails de la demande de paiement et les cours déclarés
    detail_demande_paiements = Detail_demande_paiement.objects.filter(demande_paiement=demande_paiement)
    cours_declares = {enr.cours for enr in detail_demande_paiements}

    # Récupérer les emails
    email = Email_telecharge.objects.filter(id=demande_paiement.email).first()
    email_eleve = Email_telecharge.objects.filter(id=demande_paiement.email_eleve).first()

    # Préparer le contexte pour le rendu du template
    context = {
        'demande_paiement': demande_paiement,
        'eleve': eleve,
        'parent': parent,
        'cours_declares': [{'cours': cours} for cours in cours_declares],
        'detaille_declares': [{'enr': enr} for enr in detail_demande_paiements],
        'email': email,
        'email_eleve': email_eleve,
    }

    # Gestion de l'envoi d'un email de rappel
    if request.method == 'POST' and 'btn_rappelle' in request.POST:
        if email:  # Vérifier si l'email existe
            request.session['email_telecharge_id'] = email.id
            return redirect('envoie_email', destinataire_id=eleve.user.id)
        messages.error(request, "L'email lié à à la demande de paiement n'a pas été trouvée.")
        return render(request, 'accounts/detaille_demande_reglement.html', context)
        
    # Gestion de la réponse à l'email de élève
    if request.method == 'POST' and 'btn_repondre' in request.POST:
        if email_eleve:  # Vérifier si l'email de l'élève existe
            request.session['email_telecharge_id'] = email_eleve.id
            return redirect('envoie_email', destinataire_id=eleve.user.id)
        messages.error(request, "La réponse de l'élève n'a pas été trouvée.")
        return render(request, 'accounts/detaille_demande_reglement.html', context)

    # Gestion de l'annulation de la demande de paiement
    if request.method == 'POST' and 'btn_annuler' in request.POST:
        if demande_paiement.statut_demande in ['En attente', 'Contester'] and not demande_paiement.payment_id:
            # # Vérification des horaires pour annulation
            # for enr in detail_demande_paiements:
            #     horaire = Horaire.objects.filter(id=enr.horaire.id).first()
            #     if  horaire.payment_id:
            #         messages.error(
            #             request,
            #             f"L'annulation ne peut pas être effectuée : un horaire ne satisfait pas les conditions.<br>"
            #             f" Horaire_demande paiement : {horaire.payment_id}"
            #         )
            #         return render(request, 'accounts/detaille_demande_reglement.html', context)

            # Annuler la demande de paiement et les horaires associés
            demande_paiement.statut_demande = Demande_paiement.ANNULER
            demande_paiement.save()

            for enr in detail_demande_paiements:
                horaire = Horaire.objects.filter(id=enr.horaire.id).first()
                horaire.statut_cours = Horaire.ANNULER
                horaire.save()

            messages.success(request, 'La demande de paiement a été annulée.')
        else:
            messages.error(request, "La demande de paiement est déjà réglée ou ne peut être annulée.")

        return render(request, 'accounts/detaille_demande_reglement.html', context)

    # Affichage du template
    return render(request, 'accounts/detaille_demande_reglement.html', context)



def envoie_email(request, destinataire_id):
    if not request.user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   
    user = request.user
    # Vérifier si l'utilisateur a un profil de professeur associé
    if not hasattr(user, 'professeur'):
        messages.error(request, "Vous n'etes pas connecté en tant que prof")
        return redirect('signin') 
    # Récupère le destinataire en utilisant l'ID fourni, renvoie une erreur 404 s'il n'existe pas
    destinataire = get_object_or_404(User, id=destinataire_id)
    
    # Récupère l'ID de l'email à partir de la session
    email_id = request.session.get('email_telecharge_id')
    email = Email_telecharge.objects.filter(id=email_id).first()

    # Si un email est trouvé, initialise le sujet et le texte de l'email, sinon utilise des valeurs par défaut
    if email:
        sujet = email.sujet or "Email de rappel"
        text_email = email.text_email
    else:
        sujet, text_email = "Email de rappel", ""

    # Récupère l'adresse email du professeur depuis le formulaire ou utilise celle de l'utilisateur connecté
    email_prof = request.POST.get('email_adresse', user.email).strip()

    # Vérifie si la méthode est POST et que le bouton d'enregistrement a été cliqué
    if request.method == 'POST' and 'btn_enr' in request.POST:
        # Met à jour le sujet de l'email ou utilise une valeur par défaut
        sujet = request.POST.get('sujet', sujet).strip() or "Email de rappel"
        # Met à jour le texte de l'email
        text_email = request.POST.get('text_email', text_email).strip()

        # Récupère l'adresse email de l'élève
        email_eleve = destinataire.email
        # Récupère l'adresse email du parent s'il existe
        email_parent = Parent.objects.filter(user=destinataire).first()
        
        # Initialise la liste des destinataires avec l'email de l'élève et un email par défaut
        destinations = [email_eleve, 'prosib25@gmail.com']
        if email_parent:
            # Ajoute l'email du parent à la liste des destinataires si disponible
            destinations.append(email_parent.email_parent)
            
        # Valider l'adresse e-mail du professeur
        try:
            validate_email(email_prof)
        except ValidationError:
            messages.error(request, "L'adresse e-mail du professeur n'est pas valide.")
            return render(request, 'accounts/envoie_email.html', {
                'email_prof': email_prof,
                'sujet': sujet,
                'text_email': text_email,
            })

        # Valider les adresses e-mail des destinataires
        for email in destinations:
            try:
                validate_email(email)
            except ValidationError:
                messages.error(request, f"L'adresse e-mail du destinataire {email} n'est pas valide.")
                return render(request, 'accounts/envoie_email.html', {
                    'email_prof': email_prof,
                    'sujet': sujet,
                    'text_email': text_email,
                })

        try:
            # Envoie l'email à tous les destinataires
            send_mail(sujet, text_email, email_prof, destinations, fail_silently=False)
            # Message de succès si l'email a été envoyé
            messages.success(request, "L'email a été envoyé avec succès.")
        except Exception as e:
            # Message d'erreur si l'envoi échoue
            messages.error(request, f"Erreur lors de l'envoi de l'email : {str(e)}")

        # Enregistre l'email dans la base de données
        Email_telecharge.objects.create(
            user=user,
            email_telecharge=email_prof,
            text_email=text_email,
            user_destinataire=destinataire.id,
            sujet=sujet
        )
        messages.success(request, "Email enregistré")
        # Pour supprimer uniquement 'email_telecharge_id' de la session 
        request.session.pop('email_telecharge_id', None)
        # Redirige l'utilisateur vers la page du compte professeur
        return redirect('compte_prof')

    # Passe les données au template pour affichage
    context = {
        'email_prof': email_prof,
        'sujet': sujet,
        'text_email': text_email,
    }
    return render(request, 'accounts/envoie_email.html', context)


def temoignage_mes_eleves(request):
    # Récupération de l'utilisateur connecté (professeur)
    user_prof = request.user
    # Filtrer les témoignages liés au professeur connecté
    temoignages = Temoignage.objects.filter(user_prof=user_prof)
    # Récupérer les élèves associés à ces témoignages
    user_eleves = [temoignage.user_eleve for temoignage in temoignages]
    if request.method == 'POST':
        # Rechercher la clé correspondant à l'un des boutons de détail soumis
        detaille_enr_key = next((key for key in request.POST if key.startswith('btn_detaille_')), None)
        if detaille_enr_key:
            # Extraire l'ID de l'élève à partir de la clé
            eleve_id = int(detaille_enr_key.split('btn_detaille_')[1])
            # Trouver un témoignage associé à cet élève et au professeur connecté
            temoignage_enr = Temoignage.objects.filter(user_eleve__id=eleve_id, user_prof=user_prof).first()
            if temoignage_enr:
                # Rediriger vers la vue temoignage_detaille
                return redirect('temoignage_detaille', temoignage_id=temoignage_enr.id)
            else:
                # Afficher un message d'erreur si le témoignage n'existe pas
                messages.error(request, f"Le témoignage pour l'élève avec l'ID={eleve_id} n'a pas été trouvé.")

    return render(request, 'accounts/temoignage_mes_eleves.html', {'user_eleves': user_eleves})


def temoignage_detaille(request, temoignage_id):
    # Récupération de l'utilisateur connecté (professeur)
    user_prof = request.user

    # Récupérer le témoignage spécifique ou renvoyer une erreur 404 si non trouvé
    temoignage = get_object_or_404(Temoignage, id=temoignage_id, user_prof=user_prof)
    
    if request.method == 'POST':
        if 'btn_enr' in request.POST:
            # Mettre à jour le texte du professeur à partir du POST
            temoignage.text_prof = request.POST.get('text_prof', '')
            temoignage.save()
            messages.success(request, "Le témoignage a été mis à jour.")
            return redirect('temoignage_mes_eleves')
    
    return render(request, 'accounts/temoignage_detaille.html', {'temoignage': temoignage})
