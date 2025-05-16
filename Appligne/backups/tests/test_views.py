#backups/tests/test_views.py

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from views import create_backup_view
import os
from django.conf import settings
from django.core.exceptions import PermissionDenied

class BackupViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(
            username='admin',
            password='testpass123',
            email='admin@example.com'
        )
        
        # Créer le répertoire de logs si inexistant
        os.makedirs(os.path.join(settings.BASE_DIR, 'logs'), exist_ok=True)
    
    def test_create_backup_view_get(self):
        request = self.factory.get('/admin/backups/create-backup/')
        request.user = self.user
        response = create_backup_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('title', response.context_data)
    
    def test_create_backup_view_post(self):
        request = self.factory.post('/admin/backups/create-backup/', {
            'backup_type': 'full',
            'encrypted': 'off',
            'notes': 'Test backup',
            'confirm': '1'
        })
        request.user = self.user
        response = create_backup_view(request)
        
        messages = list(get_messages(request))
        self.assertEqual(response.status_code, 302)  # Redirection
        self.assertTrue(any("succès" in str(m) for m in messages) or 
                      any("erreur" in str(m) for m in messages))
    
    def test_permission_denied(self):
        regular_user = User.objects.create_user(
            username='regular',
            password='testpass123'
        )
        request = self.factory.get('/admin/backups/create-backup/')
        request.user = regular_user
        
        with self.assertRaises(PermissionDenied):
            create_backup_view(request)