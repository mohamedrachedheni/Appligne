from django.contrib import admin
from .models import Pays
from .models import Professeur
from .models import Diplome_cathegorie
from .models import Diplome
from .models import Experience_cathegorie
from .models import Experience
from .models import Format_cour
from .models import Region
from .models import Departement
from .models import Commune
from .models import Prof_zone
from .models import Matiere_cathegorie
from .models import Matiere
from .models import Niveau_cathegorie
from .models import Niveau
from .models import Prof_mat_niv
from .models import Pro_fichier
from .models import Prof_doc_telecharge
from .models import Email_telecharge
from .models import Email_detaille
from .models import Prix_heure
from .models import Mes_eleves
from .models import Payment
from .models import Cours
from .models import Horaire
from .models import Demande_paiement
from .models import Detail_demande_paiement
from .models import Historique_prof
from .models import AccordReglement
from .models import DetailAccordReglement
from .models import Coordonnees_bancaires
from .models import AccordRemboursement
from .models import DetailAccordRemboursement
from .models import Transfer
from .models import RefundPayment
from .models import WebhookEvent







    






# Register your models here.
admin.site.register(Professeur)
admin.site.register(Diplome_cathegorie)
admin.site.register(Diplome)
admin.site.register(Experience_cathegorie)
admin.site.register(Experience)
admin.site.register(Format_cour)
admin.site.register(Pays)
admin.site.register(Region)
admin.site.register(Departement)
admin.site.register(Commune)
admin.site.register(Prof_zone)
admin.site.register(Matiere_cathegorie)
admin.site.register(Matiere)
admin.site.register(Niveau_cathegorie)
admin.site.register(Niveau)
admin.site.register(Prof_mat_niv)
admin.site.register(Pro_fichier)
admin.site.register(Prof_doc_telecharge)
admin.site.register(Email_telecharge)
admin.site.register(Email_detaille)
admin.site.register(Prix_heure)
admin.site.register(Mes_eleves)
admin.site.register(Payment)
admin.site.register(Cours)
admin.site.register(Horaire)
admin.site.register(Demande_paiement)
admin.site.register(Detail_demande_paiement)
admin.site.register(Historique_prof)
admin.site.register(AccordReglement)
admin.site.register(DetailAccordReglement)
admin.site.register(Coordonnees_bancaires)
admin.site.register(AccordRemboursement)
admin.site.register(DetailAccordRemboursement)
admin.site.register(Transfer)
admin.site.register(RefundPayment)
admin.site.register(WebhookEvent)

