# accounts/context_processors.py
from django.conf import settings

def debug_variable(request):
    return {
        'DEBUG': settings.DEBUG
    }
