from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Professeur, Diplome, Experience, Format_cour, Matiere  , Niveau, Prof_mat_niv, Departement, Region, Commune, Prof_zone, Pro_fichier, Prof_doc_telecharge, Diplome_cathegorie, Pays, Experience_cathegorie, Matiere_cathegorie, Email_telecharge, Email_suivi, Email_detaille, Prix_heure
import re
from django.contrib import auth
# from django.shortcuts import get_object_or_404 #dans le cas ou l' id du professeur ne correspond pas à un enregistrement
import json
# from django.urls import reverse
from django.shortcuts import HttpResponseRedirect
from datetime import date, datetime
# from django.utils.timezone import now
from django.http import JsonResponse
from django.core.mail import send_mail
import os
import requests # pour utiliser des API (voire nouveau_compte_prof, mot de passe)
import hashlib # convertir le suffixe en une chaîne d'octets
# image par défaut
from django.conf import settings
from django.core.files.base import ContentFile
import locale
from django.utils import formats
from django.contrib.auth.hashers import make_password, check_password
from decimal import Decimal, InvalidOperation






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

# Test de la fonction is_password_compromised
# password_test = "password12345"
# print(is_password_compromised(password_test), "zzzzzzzzzzzzzzzzzzzzzzzzzzz")



def nouveau_compte_prof(request):
    # Récupérer l'utilisateur actuel
    user = request.user
    photo = None
    first_name = "xxx"
    if user.is_authenticated:
        # # messages.info(request, f"Vous etes connecté. {user.first_name}")
        # Vérifier si l'utilisateur a un profil de professeur associé
        if hasattr(user, 'professeur'):
            # Si tel est le cas, récupérer le profil du professeur
            professeur = Professeur.objects.get(user=user)
            # Extraire la photo du profil du professeur
            photo = professeur.photo
            first_name = user.first_name
            # Passer la photo à votre modèle de contexte
            context = {'photo': photo, 'first_name':first_name}
            # on ne peut pas revenir à nouveau_compte_prof.html les coordonnées sont enregistrées
            return render(request, 'accounts/compte_prof.html', context)

    if request.method == 'POST' and 'btn_enr' in request.POST :
        # definir les variable pour les champs
        user_nom = None
        mot_pass = None
        conf_mot_pass = None
        civilite = None
        prenom = None
        nom = None
        adresse = None
        email = None
        phone = None
        date_naiss = None
        photo = None
        is_added = None
        
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
        # le paramaitre de redirect est url et de render est template
        if 'mot_pass' in request.POST: mot_pass = request.POST['mot_pass']# Vérifier la longueur du mot de passe
        else: messages.error(request, "Erreur liée au mot de passe")
        if 'conf_mot_pass' in request.POST and mot_pass == request.POST['conf_mot_pass']: conf_mot_pass = request.POST['conf_mot_pass']
        else: messages.error(request, "Erreur liée à la confirmatio du mot de passe")
        if 'civilite' in request.POST: civilite = request.POST['civilite']
        else: messages.error(request, "Erreur liée à la civilité")
        if 'prenom' in request.POST: prenom = request.POST['prenom'] 
        else: messages.error(request, "Erreur liée au prénom")
        if 'nom' in request.POST: nom = request.POST['nom']
        else: messages.error(request, "Erreur liée au nom")
        if 'adresse' in request.POST: adresse = request.POST['adresse']
        else: messages.error(request, "Erreur liée à l'adresse")
        if 'email' in request.POST: email = request.POST['email']
        else: messages.error(request, "Erreur liée à l'email")
        if 'phone' in request.POST: phone = request.POST['phone']
        else: messages.error(request, "Erreur liée au numéro du téléphone")
        if 'date_naiss' in request.POST: 
            date_naiss = request.POST['date_naiss']
            # convertissons une chaîne de caractères en un objet de type datetime
            # pour que pickadate peut la récupérer par le context en cas d'erreur
            date_naiss = datetime.strptime(date_naiss, '%d/%m/%Y') 
        else: messages.error(request, "Erreur liée à la date de naissance")
        if 'photo' in request.FILES: photo = request.FILES['photo']
        else:
            # Charger le fichier par défaut s'il n'y a pas d'image téléchargée
            default_photo_path = os.path.join(settings.BASE_DIR, 'static/img/favicon.png')
            try:
                with open(default_photo_path, 'rb') as f:
                    photo_data = f.read()
                    # Créer un objet ContentFile avec les données du fichier par défaut
                    photo_file = ContentFile(photo_data, name='favicon.png')
                    photo=photo_file  # Enregistrer le fichier dans le champ photo
            except IOError:
                messages.error(request, "Fichier par défaut introuvable")
        # pas de message d'erreur pour photo car c'est un champ non obligatoire
        context= {
        'user_nom':user_nom,
        'mot_pass':mot_pass,
        'conf_mot_pass':conf_mot_pass,
        'civilite':civilite,
        'prenom':prenom,
        'nom':nom,
        'adresse':adresse,
        'email':email,
        'phone':phone,
        'date_naiss':date_naiss,
        # erreur: l'adresse du photo n'est pas récupérée ??
        'photo':photo,
        'is_added':is_added,
        }
        
        if user_nom and mot_pass and conf_mot_pass and civilite and prenom and nom and adresse and email and phone and date_naiss:
            if User.objects.filter(username=user_nom).exists():
                messages.error(request, "Le nom de l'utilisateur est déjà utilisé, donnez un autre nom.")
                return render(request, 'accounts/nouveau_compte_prof.html', context)
            else:
                if User.objects.filter(email=email).exists():
                    messages.error(request, "L'email est déjà utilisé, donnez un autre email")
                    return render(request, 'accounts/nouveau_compte_prof.html', context)
                else:
                    if not prenom.strip() or not nom.strip() or not adresse.strip() or not user_nom.strip():
                        messages.error(request, "Le prénom, le nom , l'adresse et le nom de l'utilisateur ne peuvent pas être vide ou contenir uniquement des espaces.")
                        return render(request, 'accounts/nouveau_compte_prof.html', context)
                    else:
                        if len(mot_pass) < 8:
                            messages.error(request, "Le mot de passe doit contenir au moins 8 caractères.")
                            return render(request, 'accounts/nouveau_compte_prof.html', context)
                        
                        else:
                            # Vérifier si le mot de passe est compromis en appelant la fonction is_password_compromised
                            if is_password_compromised(mot_pass):
                                # Afficher un message d'erreur si le mot de passe est compromis
                                messages.error(request, f"Le mot de passe que vous avez choisi a été compromis lors d'une violation de données. Veuillez choisir un mot de passe différentde: {mot_pass}")
                                # à faire: introduire une boite de dialogue pour confirmer ou refuser
                                return render(request, 'accounts/nouveau_compte_prof.html', context)
                            else:
                                # définir un forma pour l'email
                                patt = "^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$"
                                # si le format de l'email est correcte
                                if re.match(patt, email):
                                    # ajouter le user
                                    user = User.objects.create_user(first_name=prenom, last_name=nom, email=email, username=user_nom, password=mot_pass, is_active=True)
                                    user.save()
                                    
                                    # ajouter professeur (user du model professeur = user sauvegardé)
                                    professeur = Professeur(user=user, adresse=adresse, numero_telephone=phone, civilite=civilite, photo=photo)
                                    professeur.set_date_naissance_from_str(request.POST['date_naiss']) # car la fonction attend une chaine de caractaires et non pas un objet de type datetime
                                    professeur.save()
                                    auth.login(request, user)
                                    is_added = True

                                    # Récupérer l'utilisateur actuel
                                    user = request.user
                                    photo = None
                                    first_name = "xxx"
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
                                    context = {'photo': photo, 'first_name':first_name, 'is_added':is_added}
                                    messages.success(request, "L'enregistrement de vos coordonnées est réussi, passez à l'étape suivante")
                                    diplome_cathegories = Diplome_cathegorie.objects.all()
                                    return render(request, 'accounts/nouveau_diplome.html', {'photo': photo, 'first_name':first_name, 'diplome_cathegories':diplome_cathegories})

                                else:
                                    messages.error(request, "Le format de l'email est incorrecte.")
                                    return render(request, 'accounts/nouveau_compte_prof.html', context)
        else: messages.error(request, "Les champs obligatoires ne doivent pas être vides")

        # pour conserver les données si il y a erreur
        return render(request, 'accounts/nouveau_compte_prof.html', context)
    else:
        # Rendre la réponse en utilisant le template 'pages/index.html'
        response = render(request, 'accounts/nouveau_compte_prof.html')
        # Ajouter les en-têtes pour empêcher la mise en cache de la page
        # Cela garantit que le navigateur récupère toujours les données les plus récentes
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # HTTP 1.1.
        response['Pragma'] = 'no-cache'  # HTTP 1.0.
        response['Expires'] = '0'  # Proxies.
        # Retourner la réponse
        return response


def nouveau_diplome(request):
    # Récupérer l'utilisateur actuel
    user = request.user
    photo = None
    first_name = "xxx"
    diplome_cathegories = Diplome_cathegorie.objects.all()
    
    if user.is_authenticated:
        # messages.info(request, f"Vous etes connecté. {user.first_name}")
        # Vérifier si l'utilisateur a un profil de professeur associé
        if hasattr(user, 'professeur'):
            # Si tel est le cas, récupérer le profil du professeur
            # messages.info(request, "if hasattr(user, 'professeur'):")
            professeur = Professeur.objects.get(user=user)
            # Extraire la photo du profil du professeur
            photo = professeur.photo
            first_name = user.first_name
            # Passer la photo à votre modèle de contexte
            context = {'photo': photo, 'first_name':first_name, 'diplome_cathegories': diplome_cathegories}
            if not request.method == 'POST' or not 'btn_enr' in request.POST:
                return render(request, 'accounts/nouveau_diplome.html', context)
        if request.method == 'POST' and 'btn_enr' in request.POST:
                
            # Récupérer l'ID de l'utilisateur actuellement connecté
            user_id = request.user.id
            # s'il y a un utilisateur connecté à son compte
            if user_id is not None:
                try:
                    user = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    messages.error(request, "Utilisateur non trouvé.")
                    return render(request, 'accounts/nouveau_diplome.html', context)
                # Liste des diplômes dans le request dont le nom commence par: diplome_
                diplome_keys = [key for key in request.POST.keys() if key.startswith('diplome_')]
                if not diplome_keys:
                    messages.error(request, "Il faut donner au moins un diplôme")
                    return render(request, 'accounts/nouveau_diplome.html', context)
                else:
                    #messages.info(request, f"Nombre de diplômes : {len(diplome_keys)}")
                    # recupérer les données de chaque diplome et les enregistrer
                    # il faut réviser cette procédure (à première vu le JS de reordonner() est correcte)
                    for i in range(1, len(diplome_keys) + 1):
                        # Récupération des valeurs du formulaire
                        diplome_key = f'diplome_{i}'
                        date_obtenu_key = f'date_obtenu_{i}'
                        principal_key = f'principal_{i}'
                        intitule_key = f'intitule_{i}'
                        autre_diplome_key = f'autre_diplome_{i}'
                        #print("diplome_key= ", diplome_key, "date_obtenu_key= ", date_obtenu_key, "principal_key= ", principal_key, "intitule_key= ", intitule_key, "########################")
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
                                        # messages.success(request, f"Le diplôme '{autre_diplome}' a été ajouté au Diplome_cathegorie pour le pays France.")
                                        diplome = autre_diplome
                                    else:
                                        diplome = autre_diplome
                                        # messages.warning(request, f"Le diplôme '{autre_diplome}' existe déjà dans la catégorie 'Autre' pour le pays France.")
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
                            #print("diplome= ", diplome, "date_obtenu= ", date_obtenu, "principal= ", principal, "intitule= ",intitule)

                             # Vérification si le diplôme n'existe pas déjà pour cet utilisateur
                            if not Diplome.objects.filter(user=user, diplome_cathegorie_id=diplome_cathegorie_id, intitule=intitule).exists():
                                if date_obtenu:
                                    diplome_instance = Diplome(user=user, diplome_cathegorie_id=diplome_cathegorie_id, intitule=intitule, principal=principal)
                                    diplome_instance.set_date_obtenu_from_str(date_obtenu)
                                    diplome_instance.save()
                                    #messages.success(request, f"L'enregistrement des diplômes est réussi, passez à l'étape suivante {i}")
                                    
                                else:
                                    messages.error(request, f"Erreur liée à la date d'obtention du diplôme {i}")
                                    return render(request, 'accounts/nouveau_diplome.html', context)
                            else:  messages.warning(request, f"Le diplôme '{diplome}' : '{intitule}' , existe déjà pour cet utilisateur.")
                        else:
                            # erreur à dépasser
                            messages.error(request, f"Erreur liée au diplôme {i}")
                # Rendre la réponse en utilisant le template 'pages/index.html'
                response = render(request, 'accounts/nouveau_experience.html', context)
                # Ajouter les en-têtes pour empêcher la mise en cache de la page
                # Cela garantit que le navigateur récupère toujours les données les plus récentes
                response['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # HTTP 1.1.
                response['Pragma'] = 'no-cache'  # HTTP 1.0.
                response['Expires'] = '0'  # Proxies.
                # Retourner la réponse
                return response
    else:
        messages.error(request, "Il n'y a pas d'utilisateur connecté à son compte.")
        return render(request, 'pages/index.html')


def nouveau_experience(request):
    # Récupérer l'utilisateur actuel
    user = request.user
    photo = None
    first_name = "xxx"
    
    if user.is_authenticated:
        # messages.info(request, f"Vous etes connecté. {user.first_name}")
        # Vérifier si l'utilisateur a un profil de professeur associé
        if hasattr(user, 'professeur'):
            # Si tel est le cas, récupérer le profil du professeur
            # messages.info(request, "if hasattr(user, 'professeur'):")
            professeur = Professeur.objects.get(user=user)
            # Extraire la photo du profil du professeur
            photo = professeur.photo
            first_name = user.first_name
            # Passer la photo à votre modèle de contexte
            context = {'photo': photo, 'first_name':first_name}
            if not request.method == 'POST' or not 'btn_enr' in request.POST:
                return render(request, 'accounts/nouveau_experience.html', context)
    if request.method == 'POST' and 'btn_enr' in request.POST:
        # Récupérer l'ID de l'utilisateur actuellement connecté
        user_id = request.user.id
        # s'il y a un utilisateur connecté à son compte
        if user_id is not None:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                messages.error(request, "Utilisateur non trouvé.")
                return redirect('nouveau_experience')
            
            # Liste des expériences dans le request dont le nom commence par: type_
            type_keys = [key for key in request.POST.keys() if key.startswith('type_')]
            if not type_keys: # s'il n'y a pas d'expérience sélectionnée
                messages.error(request, "Il faut donner au moins une expérience, sinon sélectionnez Débutant(e)")
                return redirect('nouveau_experience')
            else: # s'il y a au mois une expérience sélectionnée
                # messages.success(request, f"Nombre d expérience : {len(type_keys)}")
                # recupérer les données de chaque expérience et les enregistrer
                # dans le JS de la page il faut que la fonc
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
                    #print("diplome_key= ", type_key, "date_obtenu_key= ", date_debut_key, "date_fin_key= ", date_fin_key, "principal_key= ", principal_key, "actuellement_key= ", actuellement_key, "Commentaire_key= ", Commentaire_key, "########################")
                    if request.POST.get(type_key): # car dans le JS de la page on a réodonner les ID
                        type = request.POST.get(type_key)
                        debut = request.POST.get(date_debut_key, None)
                        fin = request.POST.get(date_fin_key, None)
                        commentaire = request.POST.get(Commentaire_key, None)
                        if request.POST.get(principal_key, None) == "on":
                            principal = True
                        else: principal = False
                        if request.POST.get(actuellement_key, None) == "on":
                            actuellement = True
                        else: actuellement = False
                        #print("diplome_key= ", type, "date_obtenu_key= ", debut, "date_fin_key= ", fin, "principal_key= ", principal, "actuellement_key= ", actuellement, "Commentaire_key= ", commentaire , "*****************")
                        # Vérification si le type d'expérience n'existe pas déjà pour cet utilisateur
                        if not Experience.objects.filter(user=user, type=type, commentaire=commentaire).exists():
                            if debut:
                                experience_instance = Experience(user=user, type=type, commentaire=commentaire, principal=principal, actuellement=actuellement)
                                experience_instance.set_date_debut_from_str(debut)
                                experience_instance.set_date_fin_from_str(fin)
                                experience_instance.save()
                                # messages.success(request, f"L'enregistrement de l'éxpérence {type} : {commentaire} est réussi. {i}")
                            else: # on peut définir par défaut date début ou rendre date début non obligatoire
                                debut = datetime.now().strftime('%d/%m/%Y')
                                experience_instance = Experience(user=user, type=type, commentaire=commentaire, principal=principal, actuellement=actuellement)
                                experience_instance.set_date_debut_from_str(debut)
                                experience_instance.set_date_fin_from_str(fin)
                                experience_instance.save()
                                # messages.success(request, f"L'enregistrement de l'éxpérence {type} : {commentaire} est réussi. {i}")
                                # messages.error(request, f"Erreur liée à la date du début de l'éxpériencr {type} : {commentaire} ")
                                return redirect('nouveau_experience')
                        else: 
                            # on passe au type d'expérience suivant s'il y en a
                            # messages.warning(request, f"Le type d'expérience '{type}' : '{commentaire}' , existe déjà pour cet utilisateur.")
                            continue
                    else: # revoire ce cas: s'il y a des div avec des type défini et des div sans type défini alors quoi faire
                        # il vaut mieux ignorer l'enregistrement avec un message d'information
                        # messages.warning(request, f"Vous n'avez pas défini d'expérience,dans ce cas l'enregistrement est ignoré")
                        continue
                return redirect('modifier_format_cours')
        else:
            messages.error(request, "Il n'y a pas d'utilisateur connecté à son compte.")
            return redirect('nouveau_experience')
    return render(request, 'accounts/nouveau_experience.html')



def nouveau_matiere(request):
    # Récupérer l'utilisateur actuel
    user = request.user
    photo = None
    first_name = "xxx"
    
    if user.is_authenticated:
        # messages.info(request, f"Vous etes connecté. {user.first_name}")
        # Vérifier si l'utilisateur a un profil de professeur associé
        if hasattr(user, 'professeur'):
            # Si tel est le cas, récupérer le profil du professeur
            # messages.info(request, "if hasattr(user, 'professeur'):")
            professeur = Professeur.objects.get(user=user)
            # Extraire la photo du profil du professeur
            photo = professeur.photo
            first_name = user.first_name
            # Passer la photo à votre modèle de contexte
            context = {'photo': photo, 'first_name':first_name}
            if not request.method == 'POST' or not 'btn_enr' in request.POST:
                return render(request, 'accounts/nouveau_matiere.html', context)
    # Vérifie si la méthode de la requête est POST et si le bouton 'btn_enr' a été soumis
    if request.method == 'POST' and 'btn_enr' in request.POST:
        # Récupérer l'ID de l'utilisateur actuellement connecté
        user_id = request.user.id
        # Vérifier si un utilisateur est connecté à son compte
        if user_id is not None:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                messages.error(request, "Utilisateur non trouvé.")
                return redirect('nouveau_matiere')

            # Récupérer les listes de matières et de niveaux sélectionnés dans le formulaire
            liste_matieres = [key for key in request.POST.keys() if key.startswith('matiere_')]
            liste_niveaux = [key for key in request.POST.keys() if key.startswith('niveau_chx_')]
            
            # Vérifier si au moins une matière et ses niveaux correspondants ont été sélectionnés
            if not liste_matieres or not liste_niveaux:
                messages.error(request, "Il faut sélectionner au moins une matière à enseigner et les niveaux correspondants")
                return redirect('nouveau_matiere')

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
                    return redirect('nouveau_matiere')
                
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
                        return redirect('nouveau_matiere')
                
                # Sauvegarder les enregistrements Prof_mat_niv pour chaque niveau sélectionné
                for niveau_id in niveaux_id:
                    
                    # pour les filtres on utilise la valeur des ID (matiere_id ; niveau_id))
                    # si l'enregistrement n'existe pas
                    if not Prof_mat_niv.objects.filter(user=user, matiere=matiere_id, niveau=niveau_id).exists():
                        niveau_obj = Niveau.objects.get(id=niveau_id)
                        # pour l'enregistrement on utilise les objets liés aux ID (matiere_obj ; niveau_obj)
                        prof_mat_niv = Prof_mat_niv(user=user, matiere=matiere_obj, niveau=niveau_obj, principal=principal)
                        prof_mat_niv.save()
                        # messages.success(request, f"Enregistrement de: Principal = '{principal}'; Matière = '{matiere}';  Niveau = '{niveau_id}' effectué avec succès.")
                    else:
                        continue # passer au suivant niveau si l'enregistrement existe déjà
            # Rediriger vers une autre page après traitement
            messages.success(request, " L'enregistrement des matières et des niveaux sélectionnés est achevé avec succès")
            return redirect('nouveau_zone')
        
        # Si aucun utilisateur connecté n'est trouvé
        else:
            messages.error(request, "Vous devez être connecté pour effectuer cette action.")
            return redirect('nouveau_matiere')

    # Si la méthode HTTP n'est pas POST
    else:
        # Afficher le formulaire de sélection de matières
        return render(request, 'accounts/nouveau_matiere.html')

    
def nouveau_zone(request):
    # Récupérer l'utilisateur actuel
    user = request.user
    photo = None
    first_name = "xxx"
    btn_text = "Enregistrez les zones"  # Texte par défaut du bouton
    
    if user.is_authenticated:
        # messages.info(request, f"Vous etes connecté. {user.first_name}")
        # Vérifier si l'utilisateur a un profil de professeur associé
        if hasattr(user, 'professeur'):
            # Si tel est le cas, récupérer le profil du professeur
            # messages.info(request, "if hasattr(user, 'professeur'):")
            professeur = Professeur.objects.get(user=user)
            # Extraire la photo du profil du professeur
            photo = professeur.photo
            first_name = user.first_name
            # Passer la photo à votre modèle de contexte
            context = {'photo': photo, 'first_name':first_name, 'btn_text': btn_text}
            if not request.method == 'POST' or not 'btn_enr' in request.POST:
                return render(request, 'accounts/nouveau_zone.html', context)
    btn_text = "Enregistrez les zones"  # Texte par défaut du bouton
    if request.method == 'POST' and 'btn_enr' in request.POST:
        user_id = request.user.id
        if user_id is not None:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                messages.error(request, "Utilisateur non trouvé.")
                return redirect('nouveau_zone')
            # Récupérer les listes des communes du GET sélectionnées dans le deuxième select name="communes_chx"
            liste_communes = request.POST.getlist('communes_chx')
            if not liste_communes:
                messages.error(request, "Pas de commune")
                return redirect('nouveau_zone')
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
                    # messages.success(request, f"Enregistrement de la Commune  = '{commune_text}' effectué avec succès.")
                    # Modifier le texte du bouton après l'enregistrement réussi
                    btn_text = "Ajoutez d'autres zones"
                else:
                    # messages.info(request, f"Enregistrement de la Commune  = '{commune_text}' éxiste déjà.")
                    continue # passer à la suivante commune si l'enregistrement existe déjà   
            return render(request, 'accounts/nouveau_zone.html', {'btn_text': btn_text})        
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


def signin(request):
    user_nom = ""
    mot_pass = ""
    if request.method == 'POST' and 'btn_enr' in request.POST:
        user_nom = request.POST['user_nom']
        mot_pass = request.POST['mot_pass']
        user = auth.authenticate(username=user_nom, password=mot_pass)
        #print(user_nom,mot_pass,user,"*************************") pour tester le résultat dans la console
        if user is not None:
            # si la case souvients_toi n'est pas cochée
            if 'souviens_toi' not in request.POST:
                # par défaut request.session.set_expiry(1)
                # au prochain chargement de la page signin le user n'est pas logged in
                request.session.set_expiry(0)
            else:
                request.session.set_expiry(1209600)  # 2 semaines
            # au prochain chargement de la page signin le user est logged in
            # le user est connecté
            auth.login(request, user)
            return render(request, 'accounts/signin.html')
        else:
            messages.error(request, "Le nom de l'utilisateur ou le mot de passe est invalide")
    return render(request, 'accounts/signin.html', {'user_nom':user_nom, 'mot_pass':mot_pass})
    

# *********************** à réviser début  ******************************************
# ******************************************************************************
from googleapiclient.discovery import build
from decouple import config

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
    # Récupérer l'utilisateur actuel
    user = request.user
    photo = None
    first_name = "xxx"
    
    if user.is_authenticated:
        # messages.info(request, f"Vous etes connecté. {user.first_name}")
        # Vérifier si l'utilisateur a un profil de professeur associé
        if hasattr(user, 'professeur'):
            # Si tel est le cas, récupérer le profil du professeur
            # messages.info(request, "if hasattr(user, 'professeur'):")
            professeur = Professeur.objects.get(user=user)
            # Extraire la photo du profil du professeur
            photo = professeur.photo
            first_name = user.first_name
            # Passer la photo à votre modèle de contexte
            context = {'photo': photo, 'first_name':first_name}
            if not request.method == 'POST' or not 'btn_enr' in request.POST:
                return render(request, 'accounts/nouveau_description.html', context)
    if request.method == 'POST' and 'btn_enr' in request.POST:
        # en cas d'erreur il faut conserver les données déjà sésies (à faire)
        user_id = request.user.id
        if user_id is not None:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                messages.error(request, "Utilisateur non trouvé.")
                return redirect('nouveau_description')
            #messages.info(request, "info 1")
            titre  = request.POST.get('titre')
            # teste sur la longueur du titre
            if len(titre)>255:
                messages.error(request, "Le titre de votre fichier ne doit pas dépasser 255 caractaires.")
                return redirect('nouveau_description')  # Rediriger si le titre n'est pas valide
            #messages.info(request, "info 2")
            parcours  = request.POST.get('parcours')
            pedagogie  = request.POST.get('pedagogie')
            video = request.POST.get('video_youtube_url')      
            # Vérifier si l'URL est une vidéo YouTube
            if video and not est_url_youtube(video):
                messages.error(request, "L'URL de la vidéo n'est pas valide.")
                return redirect('nouveau_description')
            #messages.info(request, "info 3")
            if not Pro_fichier.objects.filter(user=user).exists():
                
                # messages.success(request, f"url_video = '{video}'  / url_API = '{video}'.")
                pro_fichier = Pro_fichier(user=user, titre_fiche=titre, parcours=parcours, pedagogie=pedagogie, video_youtube_url=video)
                pro_fichier.save()
                messages.success(request, "Enregistrement de la description détaillée est achevé.")
                return redirect('nouveau_fichier')  # Rediriger vers l'étape suivante
            else:   
                # ouvrir la boite de dialogue à faire une recherche
                #return render(request, 'accounts/nouveau_description.html', {'show_modal': True, 'parcours': parcours,
                
                # supprimer l'ancien enregistrement
                ancien_enregistrement = Pro_fichier.objects.get(user=user)
                ancien_enregistrement.delete()
                # Créez un nouveau Pro_fichier avec les données mises à jour
                pro_fichier = Pro_fichier(user=user, titre_fiche=titre, parcours=parcours, pedagogie=pedagogie, video_youtube_url=video)
                pro_fichier.save()
                #messages.info(request, "info 4")
                messages.success(request, "Enregistrement de la description détaillée est modifié avec succé.")
                return redirect('nouveau_fichier')  # Rediriger vers l'étape suivante
    #messages.info(request, "info 5")
    return render(request, 'accounts/nouveau_description.html')

def nouveau_fichier(request):
    # Récupérer l'utilisateur actuel
    user = request.user
    photo = None
    first_name = "xxx"
    
    if user.is_authenticated:
        # # messages.info(request, f"Vous etes connecté. {user.first_name}")
        # Vérifier si l'utilisateur a un profil de professeur associé
        if hasattr(user, 'professeur'):
            # Si tel est le cas, récupérer le profil du professeur
            # # messages.info(request, "if hasattr(user, 'professeur'):")
            professeur = Professeur.objects.get(user=user)
            # Extraire la photo du profil du professeur
            photo = professeur.photo
            first_name = user.first_name
            # Passer la photo à votre modèle de contexte
            context = {'photo': photo, 'first_name':first_name}
            if not request.method == 'POST' or not 'btn_enr' in request.POST:
                return render(request, 'accounts/nouveau_fichier.html', context)
    if not user.is_authenticated:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('nouveau_description')
    
    email_user = user.email
    
    if request.method == 'POST' and 'btn_enr' in request.POST:
        email_prof = request.POST.get('email_user')
        text_email = request.POST.get('text_email')
        
        fichiers_list = request.FILES.getlist('fichiers_list')

        extensions_images = ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.raw', '.psd', '.ai',
                             '.exif', '.jfif', '.jpe', '.heif', '.heic']

        if fichiers_list:
            for fichier in fichiers_list:
                nom_fichier = fichier.name
                # Obtenez l'extension du fichier
                extension_fichier = os.path.splitext(nom_fichier)[1].lower()
                #messages.info(request, f"L extension_fichier = '{extension_fichier}' nom du fichier = '{nom_fichier}' ")
                if extension_fichier in extensions_images:
                    prof_doc_telecharge = Prof_doc_telecharge(user=user, doc_telecharge=fichier)
                    prof_doc_telecharge.save()
                else:
                    messages.error(request, f"Le fichier '{nom_fichier}' n'est pas une image valide et n'a pas été enregistré.")
                    messages.error(request, "Les extensions des fichiers acceptés sont: .jpg, .jpeg, .png, .bmp, .webp, .raw, .psd, .ai,.exif, .jfif, .jpe, .heif, .heic ")

        if text_email:
            # messages.error(request, "Teste 01 ")
            if not email_prof:
                #messages.error(request, "Teste 02 ")
                # si l'utilisateur n'a pas spécifié son email, l'email de l'utiluisateur déjà enregistré est pris par défaut
                email_prof = email_user
            # messages.error(request, "Teste 03 ")
            # Sélectionner le premier enregistrement des superusers qui est dans ce cas le destinataire de l'Email
            user_destinataire = User.objects.filter(is_staff=1, is_active=1, is_superuser=1).first()
            user_destinataire_id = user_destinataire.id
            
            # traitement de l'envoie de l'email
            # si le sujet de l'email n'est pas défini dans le GET alors sujet='Sujet non défini'
            sujet = request.POST.get('sujet', '').strip()  # Obtient la valeur de 'sujet' ou une chaîne vide
            if not sujet:  # Vérifie si sujet est nul ou une chaîne d'espaces après le strip
                sujet = "Sujet non défini"
            # messages.error(request, f"Teste 02 sujet= {sujet} ")
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
    return render(request, 'accounts/nouveau_fichier.html', {'email_user': email_user})


def votre_compte(request):
    # Récupérer l'utilisateur actuel
    user = request.user
    photo = None
    first_name = "xxx"
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
    user = request.user
    if user.is_authenticated and hasattr(user, 'professeur'):
        return render(request, 'accounts/compte_prof.html')
    return redirect('index')

def logout(request):
    if request.user.is_authenticated:
        auth.logout(request)
        # messages.success(request, 'Vous etes déconnecté(e) de votre compte')
    return redirect('index')

# def compte_prof_copy(request):
#     return render(request, 'accounts/compte_prof_copy.html')


def modifier_compte_prof(request):
    # Récupérer l'utilisateur actuel
    user = request.user
    username = None
    first_name = None
    last_name = None
    email = None
    civilite = None
    numero_telephone = None
    date_naissance = None
    adresse = None
    photo = None
    photo_nouveau = None
    if user.is_authenticated:
        # # messages.info(request, f"Vous etes connecté. {user.first_name}")
        # Vérifier si l'utilisateur a un profil de professeur associé
        if hasattr(user, 'professeur'):
            # Si tel est le cas, récupérer le profil du professeur
            # # messages.info(request, "if hasattr(user, 'professeur'):")
            professeur = Professeur.objects.get(user=user)
            # Extraire les données
            username = user.username
            first_name = user.first_name
            last_name = user.last_name
            email = user.email
            civilite = professeur.civilite
            numero_telephone = professeur.numero_telephone
            date_naissance = professeur.date_naissance
            adresse = professeur.adresse
            photo = professeur.photo
            # Passer les doànnées à votre modèle de contexte
            context = {'username':username,
                       'first_name':first_name,
                       'last_name':last_name,
                       'email':email,
                       'civilite':civilite,
                       'numero_telephone':numero_telephone,
                       'date_naissance':date_naissance,
                       'adresse':adresse,
                       'photo': photo,}
            # la page est activée sans enregistrement
            if not request.method == 'POST' or not 'btn_enr' in request.POST:
                return render(request, 'accounts/modifier_compte_prof.html', context)

            # si le bouton enregister est cliqué
            if request.method == 'POST' and 'btn_enr' in request.POST:
                username_nouveau = request.POST['username']
                first_name_nouveau = request.POST['first_name']
                last_name_nouveau = request.POST['last_name']
                email_nouveau = request.POST['email']
                civilite_nouveau = request.POST['civilite']
                numero_telephone_nouveau = request.POST['numero_telephone']
                date_naissance_nouveau = request.POST['date_naissance']
                adresse_nouveau = request.POST['adresse']
                #photo_nouveau = request.FILES['photo']
                context = {'username':username_nouveau,
                       'first_name':first_name_nouveau,
                       'last_name':last_name_nouveau,
                       'email':email_nouveau,
                       'civilite':civilite_nouveau,
                       'numero_telephone':numero_telephone_nouveau,
                       'date_naissance':date_naissance_nouveau,
                       'adresse':adresse_nouveau,
                       'photo': photo,}
                if not username_nouveau.strip() or not first_name_nouveau.strip() or not last_name_nouveau.strip() or not email_nouveau.strip() or not civilite_nouveau.strip() or not numero_telephone_nouveau.strip() or not date_naissance_nouveau.strip() or not adresse_nouveau.strip():
                    messages.error(request, "Tous les champs ne peuvent pas être vide ou contenir uniquement des espaces.")
                    return render(request, 'accounts/modifier_compte_prof.html', context)
                
                # si le nom de l'utilisateur a été changé et qu'il éxiste déjà
                if username_nouveau != username and User.objects.filter(username=username_nouveau).exists():
                    messages.error(request, "Le nom de l'utilisateur est déjà utilisé, donnez un autre nom.")
                    return render(request, 'accounts/modifier_compte_prof.html', context)

                # si l'email a été changé et que le nouveau email existe déjà
                if email_nouveau != email and User.objects.filter(email=email_nouveau).exists():
                    messages.error(request, "L'email est déjà utilisé, donnez un autre email")
                    return render(request, 'accounts/modifier_compte_prof.html', context)

                # Vérifier le format de la date
                try:
                        # si la convertion est réussie
                        date_naissance_01 = datetime.strptime(date_naissance_nouveau, '%d/%m/%Y')
                        # messages.info(request, f"Format de date de naissance est correcte {date_naissance_01}")
                except ValueError:
                    messages.error(request, "Format de date de naissance invalide. Utilisez jj/mm/aaaa")
                    return render(request, 'accounts/modifier_compte_prof.html', context)
                
                # définir un forma pour l'email
                patt = "^\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$"
                # si le format de l'email est correcte
                if re.match(patt, email_nouveau):
                    # Mettre à jour les données de l'utilisateur
                    user.username = username_nouveau
                    user.first_name = first_name_nouveau
                    user.last_name = last_name_nouveau
                    user.email = email_nouveau
                    user.save()

                    # Mettre à jour les données du professeur
                    professeur.adresse = adresse_nouveau
                    professeur.numero_telephone = numero_telephone_nouveau
                    professeur.civilite = civilite_nouveau
                    professeur.set_date_naissance_from_str(date_naissance_nouveau)
                    # s'il y a un changement de photo d'identité
                    if 'photo' in request.FILES: professeur.photo = request.FILES['photo']  
                    professeur.save()
                    # auth.login(request, user)
                    messages.success(request, "Les informations ont été mises à jour avec succès.")
                    return redirect('votre_compte')
                else:
                    messages.error(request, "Le format de l'email est incorrecte.")
                    # Rendre la réponse en utilisant le template 'pages/index.html'
                    response = render(request, 'accounts/modifier_compte_prof.html', context)
                    # Ajouter les en-têtes pour empêcher la mise en cache de la page
                    # Cela garantit que le navigateur récupère toujours les données les plus récentes
                    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # HTTP 1.1.
                    response['Pragma'] = 'no-cache'  # HTTP 1.0.
                    response['Expires'] = '0'  # Proxies.
                    # Retourner la réponse
                    return response
        else:
            messages.error(request, "Vous n'etes pas connecté en tant que prof")
            return redirect('signin') 

    else:
        messages.error(request, "Pas d'utilisateur connecté.")
        return redirect('signin')   


def modifier_format_cours(request):
    # Vérification si l'utilisateur est authentifié
    if not request.user.is_authenticated:
        messages.error(request, "Vous devez être connecté pour accéder à cette page.")
        return redirect('signin')
    
    user = request.user
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
        return redirect('votre_compte')

    # Rendre la page avec les données initiales
    return render(request, 'accounts/modifier_format_cours.html', initial_data)




def modifier_description(request):
    if request.user.is_authenticated:
        user = request.user
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
                return redirect('votre_compte')
        except Pro_fichier.DoesNotExist:
            messages.error(request, "Les données des descriptions n'existent pas pour cet utilisateur. Vous devez ajouter vos descriptions avant")
            return redirect('nouveau_description')
    else:
        messages.error(request, "Vous devez être connecté pour accéder à cette page.")
        return redirect('signin')
    return render(request, 'accounts/modifier_description.html')


def modifier_diplome(request):
    diplome_cathegories = Diplome_cathegorie.objects.all()
    if request.user.is_authenticated:
        user = request.user
        try:
            diplomes = Diplome.objects.filter(user=user)
            # Conversion de la date dans le bon format
            for diplome in diplomes:
                diplome.obtenu = diplome.obtenu.strftime('%d/%m/%Y')
            
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
                # messages.info(request, f"Nombre de diplômes : {len(diplome_keys)}")
                # début de l'enregistrement
                # supprimer les anciens enregistrements
                diplomes.delete()
                for diplome_key in diplome_keys:
                    # messages.info(request, f"Nombre de diplômes : {diplome_key}")
                    i = int(diplome_key.split('_')[1])
                    diplome_key = f'diplome_{i}'
                    date_obtenu_key = f'date_obtenu_{i}'
                    principal_key = f'principal_{i}'
                    intitule_key = f'intitule_{i}'
                    if request.POST.get(diplome_key):
                        diplome = request.POST.get(diplome_key)
                        # messages.info(request, f"diplôme : {diplome}")
                        if not diplome.strip() or diplome == 'Autre':  # Vérifie si la chaîne est vide ou contient seulement des espaces ou = 'Autre'
                            messages.error(request, "Le diplôme ne peut pas être vide ou contenir uniquement des espaces. ou intitulé: Autre")
                            continue  # Move to the next iteration of the loop
                        if len(diplome) > 100:
                            diplome = diplome[:100]  # Prendre seulement les 100 premiers caractères
                            messages.info(request, "Le diplôme a été tronqué aux 100 premiers caractères.")
                        diplome_cathegorie = Diplome_cathegorie.objects.filter(dip_cathegorie=diplome)
                        if not diplome_cathegorie.exists():
                            # messages.info(request, f"diplôme : {diplome}")
                            # Le diplôme n'existe pas, nous devons l'ajouter à la table Diplome_cathegorie
                            pays_default = Pays.objects.get(nom_pays='France')  # Remplacez 'Default' par le nom du pays par défaut
                            new_diplome_cathegorie = Diplome_cathegorie.objects.create(nom_pays=pays_default, dip_cathegorie=diplome)
                            new_diplome_cathegorie.save()
                            # messages.info(request, f"Le diplôme '{diplome}' a été ajouté à la catégorie de diplômes.")
                        
                        # Le diplôme existe déjà dans la table Diplome_cathegorie
                        # messages.warning(request, "Début enregistrement")
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
                            if not date_obtenu:
                                date_obtenu = datetime.now().strftime('%d/%m/%Y')  # Prendre la date du jour au format jj/mm/aaaa
                                # messages.info(request, f"La date d'obtention du diplôme: {diplome} est convertie à la date du jour par défaut")
                            diplome_instance = Diplome(user=user, diplome_cathegorie_id=diplome_cathegorie_id, intitule=intitule, principal=principal)
                            diplome_instance.set_date_obtenu_from_str(date_obtenu)
                            diplome_instance.save()
                            # messages.success(request, f"L'enregistrement du diplôme: {diplome},  est réussi, passez à l'étape suivante ")
                            
                        else: 
                            # messages.warning(request, f"Le diplôme '{diplome}' : '{intitule}' , existe déjà pour cet utilisateur.")
                            continue
                return redirect('votre_compte')
        except Diplome.DoesNotExist:
            messages.error(request, "Les données des diplômes n'existent pas pour cet utilisateur. Vous devez ajouter vos diplômes avant")
            return redirect('nouveau_diplome')
    else:
        messages.error(request, "Vous devez être connecté pour accéder à cette page.")
        return redirect('signin')
    return render(request, 'accounts/modifier_diplome.html', context)


def modifier_experience(request):
    # Vérification si l'utilisateur est connecté
    if not request.user.is_authenticated:
        messages.error(request, "Vous devez être connecté pour accéder à cette page.")
        return redirect('signin')

    # Récupération de toutes les catégories d'expérience
    experience_cathegories = Experience_cathegorie.objects.all()
    user = request.user
    experiences = Experience.objects.filter(user=user)

    # Si l'utilisateur a déjà des expériences enregistrées
    if experiences.exists():
        # messages.info(request, f"Nombre d'expériences: {len(experiences)}")
        
        # Formatage des dates pour l'affichage
        for experience in experiences:
            if experience.debut: # non nécessaire mais par prudense
                experience.debut = experience.debut.strftime('%d/%m/%Y')
            if experience.fin: # nécessaire car la date peut etre nulle
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
            # messages.info(request, f"Nombre d'expériences : {len(experience_keys)}")
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
                    # messages.info(request, "Cette expérience ne peut pas être vide ou contenir uniquement des espaces.")
                    continue
                if len(type) > 100:
                    type = type[:100]
                    messages.info(request, "Cette expérience a été tronquée aux 100 premiers caractères.")
                date_debut = request.POST.get(date_debut_key, None)
                date_fin = request.POST.get(date_fin_key, None)
                # si 'principal_key' existe alors principale==on si non None
                principal = request.POST.get(principal_key, None) == "on"
                actuellement = request.POST.get(act_key, None) == "on"
                commentaire = request.POST.get(comm_key, None)

                # Si c'est le premier enregistrement, supprimer les anciennes expériences de l'utilisateur
                if not premier_nouveau_enregistrement:
                    # messages.warning(request, "Début enregistrement")
                    experiences.delete()
                    premier_nouveau_enregistrement = True

                # Vérification de doublons et enregistrement des nouvelles expériences
                # remarque la suppression des anciens enregistrements est effectuée seulement avant le premier enregistrement
                # donc le premier enregistrement est obligatoirement effectué car il ne peut y avoire de doublant
                if not Experience.objects.filter(user=user, type=type, commentaire=commentaire).exists():
                    if not date_debut:
                        date_debut = datetime.now().strftime('%d/%m/%Y')
                        # messages.info(request, f"La date de début de l'expérience {type} est convertie à la date du jour par défaut")
                    experience_instance = Experience(user=user, type=type, actuellement=actuellement, commentaire=commentaire, principal=principal)
                    experience_instance.set_date_debut_from_str(date_debut)
                    experience_instance.set_date_fin_from_str(date_fin)
                    experience_instance.save()
                    # messages.success(request, f"L'enregistrement de cette expérience {type} a réussi.")
                else:
                    # messages.warning(request, f"Cette expérience '{type}' : '{commentaire}' existe déjà pour cet utilisateur.")
                    continue
            
            # Redirection vers la page du compte après l'enregistrement
            return redirect('votre_compte')

        # Rendu de la page de modification d'expérience avec le contexte
        return render(request, 'accounts/modifier_experience.html', context)

    # Si l'utilisateur n'a pas encore d'expériences enregistrées
    messages.error(request, "Les données des expériences n'existent pas pour cet utilisateur. Vous devez ajouter vos expériences avant.")
    return redirect('nouveau_experience')



def modifier_matiere(request):
    # Vérification si l'utilisateur est connecté
    if not request.user.is_authenticated:
        messages.error(request, "Vous devez être connecté pour accéder à cette page.")
        return redirect('signin')

    # Récupération de toutes les catégories de matières et niveaux
    matieres = Matiere.objects.all()
    niveaus = Niveau.objects.all()
    user = request.user
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
            messages.success(request, "L'enregistrement est achevé avec succé. ")
            return redirect('votre_compte')

        # Rendu de la page de modification de matières avec le contexte
        return render(request, 'accounts/modifier_matiere.html', context)

    # Si l'utilisateur n'a pas encore de matières enregistrées
    messages.error(request, "Les données des matières n'existent pas pour cet utilisateur. Vous devez ajouter vos matières avant.")
    return redirect('nouveau_matiere')

def modifier_zone(request):
    user = request.user
    # Vérification si l'utilisateur est connecté
    if not request.user.is_authenticated:
        messages.error(request, "Vous devez être connecté pour accéder à cette page.")
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
                return redirect('votre_compte')
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
            return redirect('votre_compte')

        # Rendu de la page de modification de matières avec le contexte
        return render(request, 'accounts/modifier_zone.html', context)

    # Si l'utilisateur n'a pas encore de matières enregistrées
    messages.error(request, "Les données des zones d'activités n'existent pas pour cet utilisateur. Vous devez ajouter vos zones avant.")
    return redirect('nouveau_zone')

# def creer_compte_client(request):
#     return render(request, 'accounts/creer_compte_client.html')



def demande_cours_recu(request):
    # Vérification si l'utilisateur est connecté
    if not request.user.is_authenticated:
        messages.error(request, "Vous devez être connecté pour accéder à cette page.")
        return redirect('signin')
    
    user_id = request.user.id
    
    emails = Email_telecharge.objects.filter(user_destinataire=user_id)
    
    if not emails:
        messages.info(request, "Il n'y a pas d'Email envoyé.")
        return redirect('votre_compte')
    
    email_detailles = Email_detaille.objects.filter(email__in=emails)
    
    context = {
        
        'email_detailles': email_detailles
    }
    
    return render(request, 'accounts/demande_cours_recu.html', context)
    
    # # Liste des diplômes dans le request dont le nom commence par:'btn_detaiile_' 
    # btn_detaiile_keys = [key for key in request.POST.keys() if key.startswith('btn_detaiile_')]






def demande_cours_recu_eleve(request, email_id):
    user = request.user
    user_id = user.id
    # messages.success(request, f"Teste 01. user_id= {user_id}")

    if not user.is_authenticated:
        messages.error(request, "Vous devez être connecté pour accéder à cette page.")
        return redirect('signin')

    email = Email_telecharge.objects.filter(id=email_id).first()
    
    context = {
            'email': email,
            'email_id': email_id,
        }

    if not email:
        messages.info(request, "Il n'y a pas d'email envoyé.")
        return redirect('demande_cours_recu')

    if request.method != 'POST':
        
        return render(request, 'accounts/demande_cours_recu_eleve.html', context)
    # messages.success(request, "Teste 01.")
    if 'btn_ignorer' in request.POST:
        # messages.success(request, "Teste 02.")
        Email_suivi.objects.create(user=user, email=email, suivi="Ignorer")
        messages.success(request, "L'email est enregistré en tant qu'email ignoré.")
        return redirect('compte_prof')

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
        # messages.success(request, f"L'email_eleve: {email_eleve}.")
        destinations = ['prosib25@gmail.com', email_eleve]  # Change it to actual destinations
        # L'envoie de l'email n'est pas obligatoire
        # try:
        #     send_mail(
        #         sujet,
        #         text_email,
        #         email_prof,
        #         destinations,
        #         fail_silently=False,
        #     )  
        # except Exception as e:
        #     messages.error(request, f"Une erreur s'est produite lors de l'envoi de l'email : {str(e)}")
        # messages.success(request, "L'email a été envoyé avec succès.")
        email_telecharge = Email_telecharge(user=user, email_telecharge=email_prof, text_email=text_email, user_destinataire=eleve_id, sujet=sujet )
        # messages.error(request, "Teste 04 ")
        email_telecharge.save()
        Email_suivi.objects.create(user=user, email=email_telecharge, suivi="Réception confirmée", reponse_email_id=email_id)
        messages.success(request, "Email enregistré")
        return redirect('compte_prof')
    if 'btn_repondre' in request.POST:
        # messages.success(request, "Teste 04.")
        email_prof = user.email
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
            'email_prof':email_prof, 
            'email_id': email_id }
        return render(request, 'accounts/reponse_email.html'  , context)


    # Si aucun des cas ci-dessus n'est satisfait, il est recommandé de renvoyer une réponse HTTP par défaut.
    return redirect('compte_prof')



def reponse_email(request, email_id): # email_id est envoyé par le template demande_cours_recu_eleve.html
    if request.method == 'POST' and 'btn_enr' in request.POST:
        user = request.user
        email = Email_telecharge.objects.filter(id=email_id).first()
        # messages.success(request, "Teste 03.")

        email_prof = request.POST.get('email_adresse', '').strip()
        if not email_prof: email_prof = user.email

        # si le sujet de l'email n'est pas défini dans le GET alors sujet='Sujet non défini'
        sujet = request.POST.get('sujet', '').strip()  # Obtient la valeur de 'sujet' ou une chaîne vide
        if not sujet:  # Vérifie si sujet est nul ou une chaîne d'espaces après le strip
            sujet = "Suite à votre email"
        
        text_email =  request.POST['text_email']
        user_destinataire = email.user.id
        email_eleve = email.email_telecharge
        # messages.success(request, f"L'email_eleve: {email_eleve}.")
        destinations = ['prosib25@gmail.com', email_eleve]  # Change it to actual destinations
        # L'envoie de l'email n'est pas obligatoire
        # try:
        #     send_mail(
        #         sujet,
        #         text_email,
        #         email_prof,
        #         destinations,
        #         fail_silently=False,
        #     )
        # except Exception as e:
        #     messages.error(request, f"Une erreur s'est produite lors de l'envoi de l'email : {str(e)}")
        # messages.success(request, "La réponse à l'email est envoyée avec succé.")

        email_telecharge = Email_telecharge(user=user, email_telecharge=email_prof, text_email=text_email, user_destinataire=user_destinataire, sujet=sujet )
        # messages.error(request, "Teste 04 ")
        email_telecharge.save()        
        Email_suivi.objects.create(user=user, email=email_telecharge, suivi="Répondre", reponse_email_id=email_id)
        messages.success(request, "Email enregistré")
        return redirect('compte_prof')
    return redirect('reponse_email')

def email_recu_prof(request):
    # messages.error(request, "Test 01")
    # Vérification si l'utilisateur est connecté
    if not request.user.is_authenticated:
        messages.error(request, "Vous devez être connecté pour accéder à cette page.")
        return redirect('signin')
    
    user_id = request.user.id
    # recupérer les email destinés au user
    emails = Email_telecharge.objects.filter(user_destinataire=user_id)
    
    if not emails:
        messages.info(request, "Il n'y a pas d'Email envoyé à votre compte.")
        return redirect('votre_compte')
    
    
    context = {
        
        'emails': emails
    }
    
    return render(request, 'accounts/email_recu_prof.html', context)


def modifier_mot_pass(request):
    # Initialize the context dictionary with empty values
    context = {
        'user_nom': "",
        'mot_pass': "",
        'nouveau_user_nom': "",
        'nouveau_mot_pass': "",
        'confirmer_mot_pass': "",
    }

    # Check if the request method is POST and the save button was clicked
    if request.method == 'POST' and 'btn_enr' in request.POST:
        # Retrieve form data from the POST request
        user_nom = request.POST['user_nom']
        mot_pass = request.POST['mot_pass']
        nouveau_user_nom = request.POST['nouveau_user_nom']
        nouveau_mot_pass = request.POST['nouveau_mot_pass']
        confirmer_mot_pass = request.POST['confirmer_mot_pass']

        # Update the context with the retrieved form data
        context.update({
            'user_nom': user_nom,
            'mot_pass': mot_pass,
            'nouveau_user_nom': nouveau_user_nom,
            'nouveau_mot_pass': nouveau_mot_pass,
            'confirmer_mot_pass': confirmer_mot_pass,
        })

        # Authenticate the user with the provided username and password
        user = auth.authenticate(username=user_nom, password=mot_pass)
        
        # If user authentication is successful
        if user is not None:
            # Check if all new credential fields are filled
            if nouveau_user_nom and nouveau_mot_pass and confirmer_mot_pass:
                # Check if the new username is already taken by another user
                if User.objects.filter(username=nouveau_user_nom).exists() and nouveau_user_nom != user_nom:
                    messages.error(request, "Le nom de l'utilisateur est déjà utilisé, donnez un autre nom.")
                # Check if the new password is at least 8 characters long
                elif len(nouveau_mot_pass) < 8:
                    messages.error(request, "Le nouveau mot de passe doit contenir au moins 8 caractères.")
                # Check if the new password has been compromised in a data breach
                elif is_password_compromised(nouveau_mot_pass):
                    messages.error(request, "Le nouveau mot de passe a été compromis lors d'une violation de données. Veuillez choisir un autre mot de passe.")
                # Check if the new password matches the confirmation password
                elif nouveau_mot_pass != confirmer_mot_pass:
                    messages.error(request, "La confirmation du mot de passe n'est pas valide.")
                else:
                    # Update the user's username and password
                    user.username = nouveau_user_nom
                    user.password = make_password(nouveau_mot_pass)
                    user.save()
                    
                    # Log the user out after the password change
                    auth.logout(request)
                    
                    # Inform the user that the password has been successfully changed
                    messages.success(request, "Votre mot de passe a été changé avec succès. Veuillez vous reconnecter.")
                    
                    # Redirect the user to the sign-in page
                    return redirect('signin')
            else:
                # If not all required fields are filled, show an error message
                messages.error(request, "Tous les champs obligatoires doivent être remplis.")
        else:
            # If user authentication fails, show an error message
            messages.error(request, "Le nom de l'utilisateur ou le mot de passe est invalide.")

    # Render the password modification page with the current context
    return render(request, 'accounts/modifier_mot_pass.html', context)


def nouveau_prix_heure(request):
    user = request.user
    
    try:
        format_cour = Format_cour.objects.get(user=user)
    except Format_cour.DoesNotExist:
        messages.error(request, "Vous n'avez pas encore défini de format pour vos cours.")
        return redirect('compte_prof')
    
    
    prof_mat_niv = Prof_mat_niv.objects.filter(user=user) # les choix prés défini des matières et des niveaux
    if not prof_mat_niv:
        messages.error(request, "Vous n'avez pas encore défini de matière pour vos cours.")
        return redirect('compte_prof')
    
    liste_format = [] # utilisé dans la difinition des key des name des balises input des prix avec id des prof_mat_niv et la sélection des prix dans le template
    liste_format_text = [] # utilisé dans la fonction prix_heure_instance

    if format_cour.a_domicile:
        liste_format.append('a_domicile')
        liste_format_text.append('Cours à domicile')
    if format_cour.webcam:
        liste_format.append('webcam')
        liste_format_text.append('Cours par webcam')
    if format_cour.stage:
        liste_format.append('stage')
        liste_format_text.append('Stage pendant les vacances')
    if format_cour.stage_webcam:
        liste_format.append('stage_webcam')
        liste_format_text.append('Stage par webcam')
    
    prix_heure_qs = Prix_heure.objects.filter(user=user) # anciens enregistrement des prix_heure
    
    liste_enregistrements = [] # pour charger les matière, les niveaux, les format cours et les prix s'ils existent et définir les keys des name
    
    for format_item in liste_format_text:
        for prof_mat_niveau in prof_mat_niv:
            id = prof_mat_niveau.id
            matiere = prof_mat_niveau.matiere
            niveau = prof_mat_niveau.niveau
            prix_heure = ""
            prix_heure_instance = prix_heure_qs.filter(prof_mat_niv=id, format=format_item).first() # car format=format_item teste le texte du champ liste de choix format
            if prix_heure_instance: # si le prix_heure est déjà défini
                prix_heure = str(prix_heure_instance.prix_heure)
            #format_key utilisé pour la sélection par format des couples dans le boucle des prix dans le template 
            if format_item=="Cours à domicile": format_key="a_domicile"
            elif format_item=="Cours par webcam": format_key="webcam"
            elif format_item=="Stage pendant les vacances": format_key="stage"
            else: format_key="stage_webcam"
            
            couple = (id, matiere, niveau, prix_heure, format_key) # un couple pour chaque cas dans le template
            liste_enregistrements.append(couple)
    
    context = {
        'liste_format': liste_format,
        'liste_enregistrements': liste_enregistrements,
    }

    if request.method == 'POST' and 'btn_enr' in request.POST:
        # name="prix_heure-{{id}}__{{ format }}" avec format=format_key et le id pour individualiser name
        prix_keys = [key for key in request.POST.keys() if key.startswith('prix_heure-')]
        liste_prix_mat_niv_for = []
        
        for prix_key in prix_keys:
            prix = request.POST[prix_key]
            if not prix:
                continue
            prix_str = prix[:-4] # car le prix a pour masque 99,99 E/h
            try:
                prix_dec = Decimal(prix_str).quantize(Decimal('0.00'))
            except (InvalidOperation, ValueError):
                messages.error(request, f"Erreur lors de la conversion du prix '{prix_str}' en décimal, voir le programmeur")
                return render(request, 'accounts/nouveau_prix_heure.html', context)
            if prix_dec < 10:
                messages.info(request, "Les prix inférieurs à 10 Euro sont ignorés")
                continue

            mat_niv_id_str = prix_key.split('-')[1].split('__')[0] # extraire id du prix_key entre (- et __)
            try:
                mat_niv_id = int(mat_niv_id_str)
            except ValueError:
                messages.error(request, f"Erreur lors de la conversion de l'ID '{mat_niv_id_str}' en entier, voir le programmeur")
                return render(request, 'accounts/nouveau_prix_heure.html', context)

            format = prix_key.split('__')[1] # pour extraire le format du prix_key après (__)
            
            if format == "a_domicile":
                format_cour = "Cours à domicile"
            elif format == "webcam":
                format_cour = "Cours par webcam"
            elif format == "stage":
                format_cour = "Stage pendant les vacances"
            else:
                format_cour = "Stage par webcam"
            
            # stoquer les données reçues du POST das une liste de triplés
            prix_mat_niv_for = (mat_niv_id, format_cour, prix_dec)
            liste_prix_mat_niv_for.append(prix_mat_niv_for)

        if not liste_prix_mat_niv_for:
            messages.error(request, "Vous devez fixer au moins un prix supérieur ou égal à 10 Euro.")
            messages.info(request, "Les prix inférieurs à 10 Euro sont ignorés")
            return render(request, 'accounts/nouveau_prix_heure.html', context)
        
        Prix_heure.objects.filter(user=user).delete() # supprimer les anciens enregistrement
        
        for mat_niv_id, format_cour, prix_dec in liste_prix_mat_niv_for: # enregistrer les nouvaux enregistrements
            nouveau_enregistrement = Prix_heure(user=user, prof_mat_niv_id=mat_niv_id, format=format_cour, prix_heure=prix_dec)
            nouveau_enregistrement.save()
        
        messages.success(request, "Enregistrement achevé")
        return redirect('nouveau_prix_heure')
    
    return render(request, 'accounts/nouveau_prix_heure.html', context)


