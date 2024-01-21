from django.urls import path
from . import views

urlpatterns = [
    path( ''      , views.index , name='index' ),
    path( 'about' , views.about , name='about' ),
    path( 'contact' , views.contact , name='contact' ),
    path( 'liste_prof' , views.liste_prof , name='liste_prof' ),
    path( 'profil_prof/<int:id_user>/' , views.profil_prof , name='profil_prof' ), #pour envoyer id du professeur à la page

]

