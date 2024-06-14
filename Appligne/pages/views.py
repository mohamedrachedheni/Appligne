from django.shortcuts import render
from accounts.models import Professeur, Prof_zone, Departement, Matiere, Niveau, Region
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404 #dans le cas ou l' id du professeur ne correspond pas à un enregistrement
from django.contrib.auth.models import User
from accounts.models import Pro_fichier, Prof_doc_telecharge, Email_telecharge, Prix_heure, Prof_mat_niv
from django.contrib import messages
# La fonction render renvoie une instance de HttpResponse contenant le contenu 
#HTML rendu du template spécifié, donc vous n'avez pas besoin de gérer HttpResponse 
#explicitement dans ce cas.
# Cependant, si vous avez besoin de créer une réponse HTTP personna
# lisée pour une raison quelconque (par exemple, pour envoyer une réponse JSON brute), 
# alors vous devez importer HttpResponse ou toute autre classe de réponse appropriée depuis django.http.
from django.http import HttpResponse
from accounts.models import Professeur
import os
from django.core.mail import send_mail
from django.db.models import OuterRef, Subquery, DecimalField

# Create your views here.



def liste_prof(request):

    radio_name = "a_domicile" # valeur par défaut des paramètres de recherches si la page est activée par son url
    radio_name_text = "Cours à domicile"
    matiere_defaut = "Maths"
    niveau_defaut = "Terminale Générale"
    region_defaut = "ILE-DE-FRANCE"
    departement_defaut = "PARIS"

    # Récupère toutes les matières, niveaux, régions et départements pour les champs liste de valeurs
    matieres = Matiere.objects.all()
    niveaux = Niveau.objects.all()
    regions = Region.objects.filter(nom_pays__nom_pays='France')
    departements = Departement.objects.filter(region__region=region_defaut)
    
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

    # --------------------début Pagination-----------------------
    # Nombre d'éléments par page
    elements_par_page = 4

    # Créer un objet Paginator
    paginator = Paginator(professeurs, elements_par_page)

    # par défaut la page=1 est affichée
    page = request.GET.get('page', 1)

    # cette ligne de code permet de paginer la liste des professeurs et de récupérer la sous-liste correspondant à la page spécifiée,
    professeurs = paginator.get_page(page)
    # ----------------Fin pagination----------------------

    context = {
        'professeurs': professeurs,
        'matieres': matieres,
        'niveaux': niveaux,
        'regions': regions,
        'departements': departements,
        'radio_name': radio_name,
        'matiere_defaut': matiere_defaut,
        'niveau_defaut': niveau_defaut,
        'region_defaut': region_defaut,
        'departement_defaut': departement_defaut,
    }

    if request.method == 'POST' and not 'btn_rechercher' in request.POST: # si la page et actiée mais la recherche non
        # celà se produit lorsque avec JS pour actualiser laliste deroulente Région suite au changement de l'option 
        # sélectionnéée dans la liste déroulente département
        matiere_defaut = request.POST['matiere'] # les derniers paramètres sélectionnés
        niveau_defaut = request.POST['niveau']
        region_defaut = request.POST['region']

        if request.POST.get('a_domicile', None):
            radio_name = "a_domicile"
        if request.POST.get('webcam', None):
            radio_name = "webcam"
        if request.POST.get('stage', None):
            radio_name = "stage"
        if request.POST.get('stage_webcam', None):
            radio_name = "stage_webcam"

        departements = Departement.objects.filter(region__region=region_defaut) # la nouvelle liste des départements pour la liste déroulente département
        departement_defaut = Departement.objects.filter(region__region=region_defaut).first() # le premier de la liste des départements pour le champ input
        context.update({ # pour metre à jour les éléments susseptibles d'etre modifiés
            'departements': departements, # liste data
            'radio_name': radio_name,
            'matiere_defaut': matiere_defaut,
            'niveau_defaut': niveau_defaut,
            'region_defaut': region_defaut,
            'departement_defaut': departement_defaut, # paramètre du champ input
        })

    if request.method == 'POST' and 'btn_rechercher' in request.POST: # bouton recherche activé
        matiere_defaut = request.POST['matiere'] # derniers paramètres sélectionnés
        niveau_defaut = request.POST['niveau']
        region_defaut = request.POST['region']
        departement_defaut = request.POST['departement']

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

        request.session['matiere_defaut'] = matiere_defaut
        request.session['niveau_defaut'] = niveau_defaut
        request.session['departement_defaut'] = departement_defaut
        request.session['radio_name'] = radio_name
        request.session['radio_name_text'] = radio_name_text    
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
        # début pagination
        elements_par_page = 4 # 4 enregistrement par page
        paginator = Paginator(professeurs, elements_par_page)
        page = request.GET.get('page', 1) # par défaut la page=1 est affichée
        professeurs = paginator.get_page(page)
        # fin pagination

        context.update({
            'professeurs': professeurs, # data
            'radio_name': radio_name, # paramètres de recherche
            'radio_name_text': radio_name_text,
            'matiere_defaut': matiere_defaut,
            'niveau_defaut': niveau_defaut,
            'region_defaut': region_defaut,
            'departement_defaut': departement_defaut,
        })
        return render(request, 'pages/liste_prof.html', context)

    return render(request, 'pages/liste_prof.html', context)


def profil_prof(request, id_user):
    user = get_object_or_404(User, id=id_user)
    
    # Utilisez prefetch_related avec distinct pour précharger les départements et éviter les répétitions
    prof_zones = Prof_zone.objects.filter(user=user).select_related('commune__departement')
    
    # Récupérer les départements distincts à partir des prof_zones: c'est un regroupement des valeur departement
    departements_distincts = Departement.objects.filter(id__in=prof_zones.values_list('commune__departement_id', flat=True)).distinct()
    
    # Déterminer prix_heure selon les paramètres de recherche dans la session
    niveau = request.session.get('niveau_defaut', None)
    if niveau is not None:
        niveau_id = Niveau.objects.get(niveau=niveau)
    else:
        niveau_id = None

    matiere = request.session.get('matiere_defaut', None)
    if matiere is not None:
        matiere_id = Matiere.objects.get(matiere=matiere)
    else:
        matiere_id = None

    if niveau_id and matiere_id:
        prof_mat_niv = Prof_mat_niv.objects.get(user=user, matiere=matiere_id, niveau=niveau_id)
        
        format = request.session.get('radio_name', None)
        if format == "a_domicile":
            format_cour = "Cours à domicile"
        elif format == "webcam":
            format_cour = "Cours par webcam"
        elif format == "stage":
            format_cour = "Stage pendant les vacances"
        else:
            format_cour = "Stage par webcam"
        
        prix_heure_obj = Prix_heure.objects.filter(user=user, format=format_cour, prof_mat_niv=prof_mat_niv).first()
        prix_heure = str(prix_heure_obj.prix_heure) if prix_heure_obj else 'N/A'
    else:
        prix_heure = 'N/A'

    context = {
        'user': user,
        'departements_distincts': departements_distincts,
        'prix_heure': prix_heure
    }
    return render(request, 'pages/profil_prof.html', context)

def index(request):
    # les paramètres par défaut pour les champs de recherche prof
    radio_name = "a_domicile"
    radio_name_text = "Cours à domicile" # pour le filtre de Prix_heure
    matiere_defaut = "Maths"
    niveau_defaut = "Terminale Générale"
    region_defaut = "ILE-DE-FRANCE"
    departement_defaut = "PARIS"

    # Récupère toutes les matières, niveaux, régions et départements pour les listes déroulentes
    matieres = Matiere.objects.all()
    niveaux = Niveau.objects.all()
    regions = Region.objects.filter(nom_pays__nom_pays='France')
    departements = Departement.objects.filter(region__region=region_defaut)

    context = {
        'matieres': matieres,
        'niveaux': niveaux,
        'regions': regions,
        'departements': departements,
        'radio_name': radio_name,
        'matiere_defaut': matiere_defaut,
        'niveau_defaut': niveau_defaut,
        'region_defaut': region_defaut,
        'departement_defaut': departement_defaut,
    }

    if request.method == 'POST' and not 'btn_rechercher' in request.POST: # si la page et actiée mais la recherche non
        # messages.info(request, "OK")
        # celà se produit lorsque avec JS pour actualiser laliste deroulente Région suite au changement de l'option 
        # sélectionnéée dans la liste déroulente département
        matiere_defaut = request.POST['matiere'] # les derniers paramètres sélectionnés
        niveau_defaut = request.POST['niveau']
        region_defaut = request.POST['region']

        if request.POST.get('a_domicile', None):
            radio_name = "a_domicile"
        if request.POST.get('webcam', None):
            radio_name = "webcam"
        if request.POST.get('stage', None):
            radio_name = "stage"
        if request.POST.get('stage_webcam', None):
            radio_name = "stage_webcam"

        departements = Departement.objects.filter(region__region=region_defaut) # la nouvelle liste des départements pour la liste déroulente département
        departement_defaut = Departement.objects.filter(region__region=region_defaut).first() # le premier de la liste des départements pour le champ input
        context.update({ # pour metre à jour les éléments susseptibles d'etre modifiés
            'departements': departements, # liste data
            'radio_name': radio_name,
            'matiere_defaut': matiere_defaut,
            'niveau_defaut': niveau_defaut,
            'region_defaut': region_defaut,
            'departement_defaut': departement_defaut, # paramètre du champ input
        })
        
    if request.method == 'POST' and 'btn_rechercher' in request.POST: # bouton recherche activé
        matiere_defaut = request.POST['matiere'] # derniers paramètres sélectionnés
        niveau_defaut = request.POST['niveau']
        region_defaut = request.POST['region']
        departement_defaut = request.POST['departement']

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

        request.session['matiere_defaut'] = matiere_defaut
        request.session['niveau_defaut'] = niveau_defaut
        request.session['departement_defaut'] = departement_defaut
        request.session['radio_name'] = radio_name
        request.session['radio_name_text'] = radio_name_text
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
        # début pagination
        elements_par_page = 4 # 4 enregistrement par page
        paginator = Paginator(professeurs, elements_par_page)
        page = request.GET.get('page', 1) # par défaut la page=1 est affichée
        professeurs = paginator.get_page(page)
        # fin pagination

        context.update({
            'professeurs': professeurs, # data
            'radio_name': radio_name, # paramètres de recherche
            'radio_name_text': radio_name_text,
            'matiere_defaut': matiere_defaut,
            'niveau_defaut': niveau_defaut,
            'region_defaut': region_defaut,
            'departement_defaut': departement_defaut,
        })
        return render(request, 'pages/liste_prof.html', context)

    return render(request, 'pages/index.html', context)

# destiné au email envoyées par les visiteur qui n'ont pas encore de compte
def nous_contacter(request):
    # Sélectionnez le premier utilisateur qui est superuser, staff et actif
    # par defaux pour eviter erreur de la base de donnée user-id can not be null
    # car le visiteur n'a pas de compt user
    # user = User.objects.filter(is_superuser=True, is_staff=True, is_active=True).first()
    if request.method == 'POST' and 'btn_enr' in request.POST:
        email = request.POST.get('email_user')
        text_email = request.POST.get('text_email')
        if text_email:
            # messages.error(request, "Teste 01 ")
            if not email:
                messages.error(request, "Vous devez indiquer votre email ")
                return render(request, 'pages/nous_contacter.html')
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
            try:
                send_mail(
                    sujet,
                    text_email,
                    email,
                    destinations,
                    fail_silently=False,
                )
                # ajouter un teste pour voir si tous les enregistrement relatifs au professeur sous achevés
            except Exception as e:
                messages.error(request, f"Une erreur s'est produite lors de l'envoi de l'email: {str(e)}")
            
            messages.success(request, "L'email a été envoyé avec succès. ")
            email_telecharge = Email_telecharge( email_telecharge=email, text_email=text_email, user_destinataire=user_destinataire_id, sujet=sujet)
            # messages.error(request, "Teste 04 ")
            email_telecharge.save()
            messages.success(request, "Email enregistré")
    return render(request, 'pages/nous_contacter.html')
