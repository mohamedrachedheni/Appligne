from django.shortcuts import render
from accounts.models import Professeur, Prof_zone, Departement, Matiere, Niveau, Region
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404 #dans le cas ou l' id du professeur ne correspond pas à un enregistrement
from django.contrib.auth.models import User
from accounts.models import Pro_fichier
from django.contrib import messages
# La fonction render renvoie une instance de HttpResponse contenant le contenu 
#HTML rendu du template spécifié, donc vous n'avez pas besoin de gérer HttpResponse 
#explicitement dans ce cas.
# Cependant, si vous avez besoin de créer une réponse HTTP personna
# lisée pour une raison quelconque (par exemple, pour envoyer une réponse JSON brute), 
# alors vous devez importer HttpResponse ou toute autre classe de réponse appropriée depuis django.http.
from django.http import HttpResponse
from accounts.models import Professeur

# Create your views here.

def liste_prof(request):
    #prefetch_related résout ce problème en effectuant une requête SQL plus complexe en une seule fois,
    # récupérant tous les objets liés nécessaires et les organisant ensuite 
    #correctement dans la structure d'objets Python.
    
    # Utilisez filter au lieu de all pour exclure les utilisateurs sans enregistrement dans Professeur
    professeurs = User.objects.filter(professeur__isnull=False).prefetch_related(
        'experience_set',
        'prof_mat_niv_set',
        'diplome_set',
        'professeur',
        'pro_fichier'
    ).distinct().order_by('id')

    # Nombre d'éléments par page
    elements_par_page = 4

    # Créer un objet Paginator
    paginator = Paginator(professeurs, elements_par_page)

    # par défaut la page=1 est affichée
    page = request.GET.get('page', 1)
    #cette ligne de code permet de paginer la liste des professeurs et de récupérer la sous-liste correspondant à la page spécifiée,
    #professeurs = paginator.page(page)
    professeurs = paginator.get_page(page)

    context = {'professeurs': professeurs}
    return render(request, 'pages/liste_prof.html', context)


def profil_prof(request, id_user):
    user = get_object_or_404(User, id=id_user)
    
    # Utilisez prefetch_related avec distinct pour précharger les départements et éviter les répétitions
    prof_zones = Prof_zone.objects.filter(user=user).select_related('commune__departement')
    
    # Récupérer les départements distincts à partir des prof_zones
    departements_distincts = Departement.objects.filter(id__in=prof_zones.values_list('commune__departement_id', flat=True)).distinct()
    
    context = {'user': user, 'departements_distincts': departements_distincts}
    return render(request, 'pages/profil_prof.html', context)




def index(request):
    radio_name = "a_domicile"
    matiere_defaut = "Maths"
    niveau_defaut = "Terminale Générale"
    region_defaut = "ILE-DE-FRANCE"
    departement_defaut = "PARIS"

    # Récupère toutes les matières, niveaux, régions et départements
    matieres = Matiere.objects.all()
    niveaux = Niveau.objects.all()
    regions = Region.objects.filter(nom_pays__nom_pays='France')
    departements = Departement.objects.filter(region__region=region_defaut)
    # departements = "Paris"
    context={
        'matieres':matieres,
        'niveaux':niveaux,
        'regions':regions,
        'departements':departements,
        'radio_name':radio_name,
        'matiere_defaut':matiere_defaut,
        'niveau_defaut':niveau_defaut,
        'region_defaut':region_defaut,
        'departement_defaut':departement_defaut,
    }

    if request.method == 'POST' and not 'btn_rechercher' in request.POST:
        matiere_defaut = request.POST['matiere']
        niveau_defaut = request.POST['niveau']
        region_defaut = request.POST['region']

        # Vérifie quel type de cours a été sélectionné (à domicile, en ligne, stage, etc.)
        if request.POST.get('a_domicile', None): 
            radio_name = "a_domicile"
        if request.POST.get('webcam', None): 
            radio_name = "webcam"
        if request.POST.get('stage', None): 
            radio_name = "stage"
        if request.POST.get('stage_webcam', None): 
            radio_name = "stage_webcam"

        departements = Departement.objects.filter(region__region=region_defaut)
        departement_defaut = Departement.objects.filter(region__region=region_defaut).first()
        context={
        'matieres':matieres,
        'niveaux':niveaux,
        'regions':regions,
        'departements':departements,
        'radio_name':radio_name,
        'matiere_defaut':matiere_defaut,
        'niveau_defaut':niveau_defaut,
        'region_defaut':region_defaut,
        'departement_defaut':departement_defaut,
        }
    if request.method == 'POST' and 'btn_rechercher' in request.POST:
        matiere_defaut = request.POST['matiere']
        niveau_defaut = request.POST['niveau']
        region_defaut = request.POST['region']
        departement_defaut = request.POST['departement']
        # Vérifie quel type de cours a été sélectionné (à domicile, en ligne, stage, etc.)
        if request.POST.get('a_domicile', None): 
            radio_name = "a_domicile"
        if request.POST.get('webcam', None): 
            radio_name = "webcam"
        if request.POST.get('stage', None): 
            radio_name = "stage"
        if request.POST.get('stage_webcam', None): 
            radio_name = "stage_webcam"
        
        # Stocke les choix de l'élève dans la session
        request.session['matiere_defaut'] = matiere_defaut
        request.session['niveau_defaut'] = niveau_defaut
        request.session['departement_defaut'] = departement_defaut
        request.session['radio_name'] = radio_name

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

        # Nombre d'éléments par page
        elements_par_page = 4

        # Créer un objet Paginator
        paginator = Paginator(professeurs, elements_par_page)

        # par défaut la page=1 est affichée
        page = request.GET.get('page', 1)
        #cette ligne de code permet de paginer la liste des professeurs et de récupérer la sous-liste correspondant à la page spécifiée,
        #professeurs = paginator.page(page)
        professeurs = paginator.get_page(page)

        context = {'professeurs': professeurs}
        return render(request, 'pages/liste_prof.html', context)

    return render(request, 'pages/index.html', context)



def about(request):
    return render(request , 'pages/about.html')

def contact(request):
    return render(request , 'pages/contact.html')