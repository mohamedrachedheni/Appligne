from django.urls import path
from . import views

urlpatterns = [
    path('nouveau_compte_eleve', views.nouveau_compte_eleve, name='nouveau_compte_eleve'),
    path('modifier_coordonnee_eleve', views.modifier_coordonnee_eleve, name='modifier_coordonnee_eleve'),
    path('compte_eleve', views.compte_eleve, name='compte_eleve'),
    path('modifier_coordonnee_parent', views.modifier_coordonnee_parent, name='modifier_coordonnee_parent'),
    path('demande_cours_envoie/<int:id_prof>/', views.demande_cours_envoie, name='demande_cours_envoie'),
    path('email_recu', views.email_recu, name='email_recu'),
    path('email_detaille/<int:email_id>/', views.email_detaille, name='email_detaille'),
    path('reponse_email_eleve/<int:email_id>/', views.reponse_email_eleve, name='reponse_email_eleve'),
    path('temoignage_eleve', views.temoignage_eleve, name='temoignage_eleve'),
    path('liste_paiement_eleve', views.liste_paiement_eleve, name='liste_paiement_eleve'),
    path('liste_remboursement', views.liste_remboursement, name='liste_remboursement'),
    path('register_eleve', views.register_eleve, name='register_eleve'),
    path('demande_paiement_eleve', views.demande_paiement_eleve, name='demande_paiement_eleve'),
    path('eleve_demande_paiement', views.eleve_demande_paiement, name='eleve_demande_paiement'),
    
]
