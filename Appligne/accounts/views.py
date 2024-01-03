from django.shortcuts import render

# Create your views here.

def signin(request):
    return render(request, 'accounts/signin.html')

def signup(request):
    return render(request, 'accounts/signup.html')

def creer_compte_client(request):
    return render(request, 'accounts/creer_compte_client.html')

def creer_compte_prof(request):
    return render(request, 'accounts/creer_compte_prof.html')

def compte_client(request):
    return render(request, 'accounts/compte_client.html')

def compte_prof(request):
    return render(request, 'accounts/compte_prof.html')
