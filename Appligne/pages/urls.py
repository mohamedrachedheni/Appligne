# pages/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path( ''      , views.index , name='index' ),
    path( 'nous_contacter' , views.nous_contacter , name='nous_contacter' ),
    path( 'liste_prof' , views.liste_prof , name='liste_prof' ),
    path( 'profil_prof/<int:id_user>/' , views.profil_prof , name='profil_prof' ), #pour envoyer id du professeur à la page*
    path( 'compte_administrateur' , views.compte_administrateur , name='compte_administrateur' ),
    path( 'admin_compte_prof/<int:user_id>/' , views.admin_compte_prof , name='admin_compte_prof' ),
    path('admin_email_recu/<int:email_id>/', views.admin_email_recu, name='admin_email_recu'),
    path('admin_doc_recu/<int:doc_id>/', views.admin_doc_recu, name='admin_doc_recu'),
    path( 'admin_compte_eleve/<int:user_id>/' , views.admin_compte_eleve , name='admin_compte_eleve' ),
    path( 'admin_liste_email_recu' , views.admin_liste_email_recu , name='admin_liste_email_recu' ),
    path('admin_detaille_email', views.admin_detaille_email, name='admin_detaille_email'),
    path('admin_reponse_email', views.admin_reponse_email, name='admin_reponse_email'),
    path( 'admin_payment_en_attente_reglement' , views.admin_payment_en_attente_reglement , name='admin_payment_en_attente_reglement' ),
    path('admin_payment_accord_reglement', views.admin_payment_accord_reglement, name='admin_payment_accord_reglement'),
    path('admin_accord_reglement', views.admin_accord_reglement, name='admin_accord_reglement'),
    path( 'admin_reglement' , views.admin_reglement , name='admin_reglement' ),
    path( 'admin_reglement_email' , views.admin_reglement_email , name='admin_reglement_email' ),
    path('admin_reglement_detaille', views.admin_reglement_detaille, name='admin_reglement_detaille'),
    path('admin_payment_demande_paiement', views.admin_payment_demande_paiement, name='admin_payment_demande_paiement'),
    path('admin_reglement_modifier', views.admin_reglement_modifier, name='admin_reglement_modifier'),
    path('admin_accord_reglement_modifier', views.admin_accord_reglement_modifier, name='admin_accord_reglement_modifier'),
    path('reclamation', views.reclamation, name='reclamation'),
    path('nouvelle_reclamation', views.nouvelle_reclamation, name='nouvelle_reclamation'),
    path('reclamations', views.reclamations, name='reclamations'),
    path('admin_faq', views.admin_faq, name='admin_faq'),
    path( 'admin_payment_eleve_remboursement' , views.admin_payment_eleve_remboursement , name='admin_payment_eleve_remboursement' ),
    path('admin_payment_accord_remboursement', views.admin_payment_accord_remboursement, name='admin_payment_accord_remboursement'),
    path('admin_accord_remboursement', views.admin_accord_remboursement, name='admin_accord_remboursement'),
    path( 'admin_remboursement' , views.admin_remboursement , name='admin_remboursement' ),
    path('admin_remboursement_detaille', views.admin_remboursement_detaille, name='admin_remboursement_detaille'),
    path( 'admin_remboursement_email' , views.admin_remboursement_email , name='admin_remboursement_email' ),
    path('admin_remboursement_modifier', views.admin_remboursement_modifier, name='admin_remboursement_modifier'),
    path('admin_accord_remboursement_modifier', views.admin_accord_remboursement_modifier, name='admin_accord_remboursement_modifier'),
    path('seconnecter', views.seconnecter, name='seconnecter'),
    path('contact-admin/', views.contact_admin, name='contact_admin'),
    path('confirm_email/<str:token>/', views.confirm_email, name='confirm_email'),
    path('password_reset_request/', views.password_reset_request, name='password_reset_request'),
    path('password_reset_confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('demande_paiement_admin', views.demande_paiement_admin, name='demande_paiement_admin'),
    path('admin_demande_paiement', views.admin_demande_paiement, name='admin_demande_paiement'),

]
