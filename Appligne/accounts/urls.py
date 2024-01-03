from django.urls import path
from . import views

urlpatterns = [
    path('signin', views.signin, name='signin' ),
    path('signup', views.signup, name='signup' ),
    path('creer_compte_client', views.creer_compte_client, name='creer_compte_client'),
    path('creer_compte_prof', views.creer_compte_prof, name='creer_compte_prof'),
    path('compte_client', views.compte_client, name='compte_client'),
    path('compte_prof', views.compte_prof, name='compte_prof'),
]
