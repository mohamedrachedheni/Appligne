from django.shortcuts import render
from accounts.models import Professeur
from django.core.paginator import Paginator

#pas besion de cette ligne suivante
from django.http import HttpResponse

# Create your views here.

def liste_prof(request):
    #prefetch_related résout ce problème en effectuant une requête SQL plus complexe en une seule fois,
    # récupérant tous les objets liés nécessaires et les organisant ensuite 
    #correctement dans la structure d'objets Python.
    professeurs = Professeur.objects.prefetch_related(
        'experience_set',
        'prof_mat_niv_set',
        'diplome_set',
        'pro_fichier'
    ).all()

    # Nombre d'éléments par page
    elements_par_page = 4

    # Créer un objet Paginator
    paginator = Paginator(professeurs, elements_par_page)

    # par défaut la page=1 est affichée
    page = request.GET.get('page', 1)
    #cette ligne de code permet de paginer la liste des professeurs et de récupérer la sous-liste correspondant à la page spécifiée,
    professeurs = paginator.page(page)

    context = {'professeurs': professeurs}
    return render(request, 'pages/liste_prof.html', context)


def profil_prof(request):
    return render(request , 'pages/profil_prof.html')

def index(request):
    # render indique que la page consernee se trouve dans templates
    return render(request , 'pages/index.html')

def about(request):
    return render(request , 'pages/about.html')

def contact(request):
    return render(request , 'pages/contact.html')