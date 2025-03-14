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
    path('admin_detaille_email/<int:email_id>/', views.admin_detaille_email, name='admin_detaille_email'),
    path('admin_reponse_email/<int:email_id>/', views.admin_reponse_email, name='admin_reponse_email'),
    path( 'admin_payment_en_attente_reglement' , views.admin_payment_en_attente_reglement , name='admin_payment_en_attente_reglement' ),
    path('admin_payment_accord_reglement/<int:prof_id>/', views.admin_payment_accord_reglement, name='admin_payment_accord_reglement'),
    path('admin_accord_reglement/<int:prof_id>/', views.admin_accord_reglement, name='admin_accord_reglement'),
    path( 'admin_reglement' , views.admin_reglement , name='admin_reglement' ),
    path( 'admin_reglement_email' , views.admin_reglement_email , name='admin_reglement_email' ),
    path('admin_reglement_detaille', views.admin_reglement_detaille, name='admin_reglement_detaille'),
    path('admin_payment_demande_paiement', views.admin_payment_demande_paiement, name='admin_payment_demande_paiement'),
    path('admin_reglement_modifier', views.admin_reglement_modifier, name='admin_reglement_modifier'),
    path('admin_accord_reglement_modifier', views.admin_accord_reglement_modifier, name='admin_accord_reglement_modifier'),

]
