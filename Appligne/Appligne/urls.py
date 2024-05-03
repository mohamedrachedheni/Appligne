"""
URL configuration for Appligne project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path , include
# pour définir url des photos liées ç la base des données
from django.conf import settings
from django.conf.urls.static import static
from decouple import config
from accounts.views import get_departments, get_regions, get_communes


urlpatterns = [
    path(config("ADMIN_ROUTE", default='admin/'), admin.site.urls),
    path( ''         , include('pages.urls') ),
    path( 'accounts/' , include('accounts.urls') ),
    path( 'eleves/' , include('eleves.urls') ),
    path('get_departments/', get_departments, name='get_departments'),
    path('get_regions/', get_regions, name='get_regions'),
    path('get_communes/', get_communes, name='get_communes'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
