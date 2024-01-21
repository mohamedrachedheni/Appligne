from django.shortcuts import render
from accounts.models import Professeur
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404 #dans le cas ou l' id du professeur ne correspond pas à un enregistrement
from django.contrib.auth.models import User 

#pas besion de cette ligne suivante
from django.http import HttpResponse

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
    user = get_object_or_404(User.objects.prefetch_related(
        'prof_zone_set__commune__departement',  # Préchargez la relation département depuis prof_zone
        'prof_zone_set',
        'experience_set',
        'prof_mat_niv_set',
        'prof_zone_set',
        'diplome_set',
        'pro_fichier',
        'professeur',
        'format_cour'
    ), id=id_user)

    context = {'user': user}
    return render(request, 'pages/profil_prof.html', context)


def index(request):
    # render indique que la page consernee se trouve dans templates
    return render(request , 'pages/index.html')

def about(request):
    return render(request , 'pages/about.html')

def contact(request):
    return render(request , 'pages/contact.html')