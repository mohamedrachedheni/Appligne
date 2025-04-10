from django.contrib import admin
from .models import ReclamationCategorie
from .models import Reclamation
from .models import PieceJointeReclamation
from .models import MessageReclamation
from .models import FAQ


# Register your models here.
admin.site.register(ReclamationCategorie)
admin.site.register(Reclamation)
admin.site.register(PieceJointeReclamation)
admin.site.register(MessageReclamation)



# Voire le formulaire (PAGES/ FAQs) dans Admin: (http://localhost:8000/Mrhssoc22578338admin/pages/faq/)
@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'public_cible', 'ordre', 'actif') # Les champs dans Admin
    list_filter = ('public_cible', 'actif') # Le filter dans Admin
    search_fields = ('question', 'reponse') # La recherche dans Admin