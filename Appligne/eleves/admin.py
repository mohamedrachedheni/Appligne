from django.contrib import admin
from .models import Eleve
from .models import Parent
from .models import Temoignage


# Register your models here.
admin.site.register(Eleve)
admin.site.register(Parent)
admin.site.register(Temoignage)