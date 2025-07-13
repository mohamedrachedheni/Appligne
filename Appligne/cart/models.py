# cart>models.py
from django.db import models
from django.conf import settings
from django.core.files import File
from django.utils import timezone
from django.template.loader import render_to_string
from io import BytesIO
import uuid
import os
from decimal import Decimal
from xhtml2pdf import pisa
from accounts.models import Cours, Payment


# ========================
#   Modèle Panier (Cart)
# ========================
class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    payment = models.OneToOneField(Payment, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Panier de {self.user.username}"

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())


# ========================
#   Élément du panier
# ========================
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    cours = models.CharField(max_length=255, null=True, blank=True)  # Description texte du cours
    quantity = models.IntegerField(default=1)  # Nombre d'unités (jours)
    price = models.IntegerField()  # Prix unitaire en centimes (ex: 1250 = 12,50 €)


    @property
    def subtotal(self):
        return self.quantity * self.price  # En centimes



# ========================
#   Facture
# ========================
"""
Voici une explication complète du modèle Invoice (facture) 
dans Django. Ce modèle permet de générer, stocker et suivre 
les factures liées aux paniers et aux paiements (notamment via Stripe).
"""
import uuid
from io import BytesIO
from django.core.files import File
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from django.conf import settings
from django.db import models
from django.utils import timezone

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('paid', 'Payée'),
        ('canceled', 'Annulée'),
    ]

    cart = models.OneToOneField('Cart', on_delete=models.SET_NULL, null=True)
    payment = models.OneToOneField(Payment, on_delete=models.SET_NULL, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    invoice_number = models.CharField(max_length=20, unique=True)  # Généré automatiquement
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    stripe_id = models.CharField(max_length=255, blank=True) # créer avec view; create_checkout_session
    total = models.IntegerField()  # Calculé automatiquement depuis le panier en centimes
    pdf = models.FileField(upload_to='invoices/', blank=True)  # Généré automatiquement
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Facture {self.invoice_number}"

    def generate_invoice_number(self):
        """
        Génère un numéro de facture unique au format : INV-YYYYMMDD-XXXXXX
        """
        date_part = timezone.now().strftime('%Y%m%d')
        unique_part = uuid.uuid4().hex[:6].upper()
        return f"INV-{date_part}-{unique_part}"

    def generate_pdf(self):
        """
        Génère un PDF à partir du template 'invoice/pdf_template.html' et le stocke dans le champ `pdf`.
        Utilise xhtml2pdf pour la conversion HTML → PDF en mémoire (BytesIO).
        """
        from eleves.models import Eleve, Parent  # Adapter selon l'emplacement réel des modèles

        parent = None
        try:
            eleve = Eleve.objects.get(user=self.user)
            parent = Parent.objects.filter(user=self.user).first()  # Lié au même user que l'élève
        except Eleve.DoesNotExist:
            pass

        html = render_to_string('invoice/pdf_template.html', {
            'invoice': self,
            'parent': parent
        })

        result = BytesIO()
        pdf_status = pisa.CreatePDF(src=html, dest=result)

        if not pdf_status.err:
            filename = f"invoice_{self.invoice_number}.pdf"
            self.pdf.save(filename, File(result), save=False)


    def save(self, *args, **kwargs):
        # Générer le numéro si nécessaire
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()

        # Calculer le total si non défini
        if (self.total is None or self.total == 0) and self.cart:
            self.total = Decimal(self.cart.total) / Decimal('100') # Conversion centimes → euros

        # Sauvegarde initiale pour générer invoice_number
        super().save(*args, **kwargs)

        # Si le PDF est manquant, le générer
        if not self.pdf:
            try:
                self.generate_pdf()
                if self.pdf:  # Vérification que le fichier a bien été créé
                    super().save(update_fields=['pdf'])  # Sauvegarde uniquement du champ PDF
            except Exception as e:
                import traceback
                print("Erreur lors de la génération du PDF :", e)
                print(traceback.format_exc())
                # Optionnel : logger ou envoyer une alerte ici

"""
🛑 Risques ou améliorations possibles :
    1. 🔄 Boucle de sauvegarde infinie (à éviter) :
    Si generate_pdf() modifiait d'autres champs et déclenchait à son tour un nouveau save(), cela pourrait créer une boucle récursive. Ici ce n’est pas le cas, car :

    le PDF est généré en mémoire et sauvegardé sans appel à save() dans generate_pdf(),

    le deuxième save() reste simple et direct.

    2. ✅ Amélioration de performance possible :
    Tu pourrais optimiser le code pour éviter un 2e save() si le PDF est déjà généré en mémoire (mais ce n'est pas indispensable si le modèle est bien conçu).
"""