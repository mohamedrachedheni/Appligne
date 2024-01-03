from django.shortcuts import render
#pas besion de cette ligne suivante
from django.http import HttpResponse
from accounts.models import Professeur

# Create your views here.

def about(request):
    return render(request , 'pages/about.html')

def contact(request):
    return render(request , 'pages/contact.html')

def liste_prof(request):
    context={
        'professeurs':Professeur.objects.all()
    }
    return render(request , 'pages/liste_prof.html', context)

def profil_prof(request):
    return render(request , 'pages/profil_prof.html')

def index(request):
    # render indique que la page consernee se trouve dans templates
    return render(request , 'pages/index.html')