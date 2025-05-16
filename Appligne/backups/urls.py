# bacpups / urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('create_backup_view', views.create_backup_view, name='create_backup_view'),
    path('download/<int:backup_id>/', views.download_backup, name='download_backup'),
]
