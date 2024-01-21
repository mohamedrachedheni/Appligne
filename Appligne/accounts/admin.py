from django.contrib import admin
from .models import Professeur
from .models import Diplome_cathegorie
from .models import Diplome
from .models import Experience_cathegorie
from .models import Experience
from .models import Format_cour
from .models import Pays
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
