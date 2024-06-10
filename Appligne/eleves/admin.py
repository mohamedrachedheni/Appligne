from django.contrib import admin
from .models import Eleve
from .models import Parent


# Register your models here.
admin.site.register(Eleve)
admin.site.register(Parent)