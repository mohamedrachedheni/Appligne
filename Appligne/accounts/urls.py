from django.urls import path
from . import views


urlpatterns = [
    path('signin', views.signin, name='signin' ), # pour se connecter
    path('logout', views.logout, name='logout' ), # pour se déconnecter
    path('nouveau_compte_prof', views.nouveau_compte_prof, name='nouveau_compte_prof'),
    path('modifier_compte_prof', views.modifier_compte_prof, name='modifier_compte_prof'),
    path('nouveau_diplome', views.nouveau_diplome, name='nouveau_diplome'),
    path('modifier_diplome', views.modifier_diplome, name='modifier_diplome'),
    # path('compte_prof_copy', views.compte_prof_copy, name='compte_prof_copy'),
    path('nouveau_experience', views.nouveau_experience, name='nouveau_experience'),
    path('modifier_experience', views.modifier_experience, name='modifier_experience'),
    path('modifier_format_cours', views.modifier_format_cours, name='modifier_format_cours'),
    path('nouveau_matiere', views.nouveau_matiere, name='nouveau_matiere'),
    path('modifier_matiere', views.modifier_matiere, name='modifier_matiere'),
    path('nouveau_zone', views.nouveau_zone, name='nouveau_zone'),
    path('modifier_zone', views.modifier_zone, name='modifier_zone'),
    path('nouveau_description', views.nouveau_description, name='nouveau_description'),
    path('modifier_description', views.modifier_description, name='modifier_description'),
    path('nouveau_fichier', views.nouveau_fichier, name='nouveau_fichier'),
    path('compte_prof', views.compte_prof, name='compte_prof'),
    path('votre_compte', views.votre_compte, name='votre_compte'),
    # path('creer_compte_client', views.creer_compte_client, name='creer_compte_client'),
    path('demande_cours_recu', views.demande_cours_recu, name='demande_cours_recu'),
    path('demande_cours_recu_eleve/<int:email_id>/', views.demande_cours_recu_eleve, name='demande_cours_recu_eleve'),
    path('reponse_email/<int:email_id>/', views.reponse_email, name='reponse_email'),
    path('email_recu_prof', views.email_recu_prof, name='email_recu_prof'),
    path('modifier_mot_pass', views.modifier_mot_pass, name='modifier_mot_pass'),
    path('nouveau_prix_heure', views.nouveau_prix_heure, name='nouveau_prix_heure'),
]
