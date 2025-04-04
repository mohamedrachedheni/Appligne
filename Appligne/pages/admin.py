from django.contrib import admin
from .models import ReclamationCategorie
from .models import Reclamation
from .models import PieceJointeReclamation
from .models import MessageReclamation


# Register your models here.
admin.site.register(ReclamationCategorie)
admin.site.register(Reclamation)
admin.site.register(PieceJointeReclamation)
admin.site.register(MessageReclamation)
