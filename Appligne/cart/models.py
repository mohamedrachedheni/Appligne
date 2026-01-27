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
from accounts.models import Cours, Payment, Professeur, Demande_paiement, AccordReglement
import stripe


# ========================
#   Modèle Panier (Cart)
# ========================
class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # payment = models.OneToOneField(Payment, on_delete=models.SET_NULL, null=True) # à supprimer
    demande_paiement = models.OneToOneField(Demande_paiement, on_delete=models.SET_NULL, null=True)
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
    cours = models.CharField(max_length=255, null=True, blank=True)  # Description texte du cours (à renommé confusion avec table cours)
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
    DRAFT='draft'
    PAID='paid'
    CANCELED='canceled'

    STATUS_CHOICES = [
        (DRAFT, 'Brouillon'), # au lencement de create_checkout_session
        (PAID, 'Payée'), # suite au payment_success
        (CANCELED, 'Annulée'), # suite au payment_cancel
    ]

    cart = models.OneToOneField('Cart', on_delete=models.SET_NULL, null=True) # non utile à enlever
    demande_paiement = models.OneToOneField(Demande_paiement, on_delete=models.SET_NULL, null=True) 
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    invoice_number = models.CharField(max_length=50, unique=True)  # Généré automatiquement
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    
    # ⚙️ ID de la session Checkout Stripe
    stripe_id = models.CharField(max_length=255, null=True, blank=True, help_text="ID de la session Checkout Stripe")
    
    # 🆕 ID du PaymentIntent Stripe
    stripe_payment_intent_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Identifiant Stripe du PaymentIntent associé"
    )
    
    stripe_charge_id = models.CharField(max_length=255, null=True, blank=True, help_text="Identifiant Stripe de la denière Charge associée")
    balance_txn_id = models.CharField(max_length=255, null=True, blank=True, help_text="Identifiant Stripe de la BalanceTransaction associée")

    total = models.IntegerField()  # Calculé automatiquement depuis le panier en centimes
    pdf = models.FileField(upload_to='invoices/', blank=True)  # Généré automatiquement
    cancellation_reason = models.CharField(max_length=255, null=True, blank=True, help_text="Raison d'annulation")
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


# ========================
#   Modèles pour les transferts
# ========================
class CartTransfert(models.Model):
    """
    Panier de transfert pour les professeurs
    """
    user_admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transferts_effectues')
    user_professeur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transferts_recus')
    accord_reglement = models.OneToOneField(AccordReglement, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Transfert {self.id} - {self.user_professeur.username}"

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())
    
    @property
    def total_euros(self):
        return self.total / 100.0
    
    @property
    def frais_plateforme(self):
        return int(self.total * 0.10)  # 10% de frais
    
    @property
    def frais_plateforme_euros(self):
        return self.frais_plateforme / 100.0
    
    @property
    def montant_net(self):
        return self.total - self.frais_plateforme
    
    @property
    def montant_net_euros(self):
        return self.montant_net / 100.0

class CartTransfertItem(models.Model):
    """
    Élément détaillé du panier de transfert
    """
    cart_transfert = models.ForeignKey(CartTransfert, related_name='items', on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    quantity = models.IntegerField(default=1)
    price = models.IntegerField()  # Prix en centimes
    
    def __str__(self):
        return f"{self.description} - {self.quantity}x {self.price/100}€"

    @property
    def subtotal(self):
        return self.quantity * self.price
    
    @property
    def price_euros(self):
        return self.price / 100.0
    
    @property
    def subtotal_euros(self):
        return self.subtotal / 100.0


class InvoiceTransfert(models.Model):
    """
    Facture détaillée pour les transferts vers les professeurs
    """
    DRAFT='draft'
    INPROGRESS='in_progess'
    PENDING='pending'
    TRANSFERRED='transferd'
    PAID='paid'
    FAILED='failed'
    CANCELED='canceled'

    STATUS_CHOICES = [
        (DRAFT, 'Brouillon'), # créer par API stripe.transfer
        (INPROGRESS, 'En cours'), # créer mais pas encaisser
        (PENDING, 'En attente'), # momentanément bloquer
        (TRANSFERRED, 'Transférer'), # Le montant est transféré mais pas encore encaissé (en attente du payout.succeed)
        (PAID, 'Payée'), # encaisser
        (FAILED, 'Échouée'), # encaissement échouer
        (CANCELED, 'Annulée'), # annuler par l'admin
    ]

    user_admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='factures_transfert_emises')
    user_professeur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='factures_transfert_recues')
    accord_reglement = models.OneToOneField(AccordReglement, on_delete=models.SET_NULL, null=True, blank=True)
    # payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True)
    invoice_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    stripe_transfer_id = models.CharField(max_length=255, null=True, blank=True) # identifiant unique du transfer à la création si c'est réussit et en cours grasse à API
    total = models.DecimalField(max_digits=6, decimal_places=2, default=0.00, null=True, blank=True)  # En centimes
    balance_transaction = models.CharField(max_length=255, null=True, blank=True) # représente l’entrée dans le grand livre Stripe — contient le net, les frais, et la date de disponibilité des fonds.
    destination_payment = models.CharField(max_length=255, null=True, blank=True) # ➡️ ID du paiement créé sur le compte connecté utile pour suivi avancé (rarement indispensable)
    frais = models.DecimalField(max_digits=6, decimal_places=2, default=0.00, null=True, blank=True)  # En centimes
    montant_net = models.DecimalField(max_digits=6, decimal_places=2, default=0.00, null=True, blank=True)  # En centimes
    pdf = models.FileField(upload_to='invoices_transfert/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # champs à supprimer
    # paid_at = models.DateTimeField(null=True, blank=True) # (à supprimer)
    # frais_stripe = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, default=0.00)# (à supprimer)
    # montant_net_final = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, default=0.00) # (à supprimer)
    # date_mise_en_valeur = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Facture Transfert {self.invoice_number}"

    def generate_invoice_transfert_number(self):
        date_part = timezone.now().strftime('%Y%m%d')
        unique_part = uuid.uuid4().hex[:6].upper()
        return f"TRANSF-{date_part}-{unique_part}"

    def generate_pdf(self):
        """
        Génère un PDF détaillé pour la facture de transfert UNIQUEMENT si le statut est 'paid'
        """
        # Vérifier si le statut est 'paid'
        if self.status != 'paid':
            print(f"⏳ PDF non généré - Statut actuel: {self.status}. Attendre le statut 'paid'.")
            return False
        
        try:
            # 🔁 Toujours recharger l'objet depuis la base
            self.refresh_from_db()

            # Double vérification après rechargement
            if self.status != 'paid':
                print(f"⏳ PDF non généré après refresh - Statut: {self.status}")
                return False

            professeur = Professeur.objects.get(user=self.user_professeur)
            items = self.get_transfert_items()
            
            print("✅ DEBUG - Génération PDF (statut paid confirmé):")
            print("stripe_transfer_id =", self.stripe_transfer_id)
            print("paid_at =", self.paid_at)
            print("status =", self.status)
            
            html = render_to_string('invoice/transfert_pdf_template.html', {
                'invoice': self,
                'professeur': professeur,
                'items': items,
            })

            result = BytesIO()
            pdf_status = pisa.CreatePDF(src=html, dest=result)

            if not pdf_status.err:
                filename = f"transfert_{self.invoice_number}.pdf"
                self.pdf.save(filename, File(result), save=False)
                print("✅ PDF généré avec succès")
                return True
            else:
                print("❌ Erreur lors de la création du PDF")
                return False
                
        except Exception as e:
            print(f"❌ Erreur génération PDF transfert: {e}")
            return False

    def get_transfert_items(self):
        """
        Récupère les items liés au transfert, via plusieurs méthodes robustes.
        """
        try:
            # ✅ 1. Si un Payment est lié et que celui-ci est lié à un CartTransfert
            if self.payment:
                cart_transfert = CartTransfert.objects.filter(payment=self.payment).first()
                if cart_transfert:
                    return cart_transfert.items.all()

            # ✅ 2. Si les métadonnées Stripe contiennent l'ID du panier (méthode secondaire)
            if self.stripe_transfer_id:
                try:
                    transfert = stripe.Transfer.retrieve(self.stripe_transfer_id)
                    cart_transfert_id = transfert.metadata.get('cart_transfert_id')
                    if cart_transfert_id:
                        cart_transfert = CartTransfert.objects.filter(id=cart_transfert_id).first()
                        if cart_transfert:
                            return cart_transfert.items.all()
                except Exception as e:
                    print(f"[⚠️] Erreur Stripe lors de la récupération des items : {e}")

            # ✅ 3. Dernier recours : retrouver le CartTransfert via l'admin + prof
            fallback_cart = CartTransfert.objects.filter(
                user_admin=self.user_admin,
                user_professeur=self.user_professeur
            ).order_by('-created_at').first()

            if fallback_cart:
                return fallback_cart.items.all()

        except Exception as e:
            print(f"Erreur récupération items transfert: {e}")

        return []


    def save(self, *args, **kwargs):
        # Générer le numéro si nécessaire
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_transfert_number()
        
        # SUPPRIMER toute référence à cart_transfert dans le save
        # Les montants sont définis à la création, pas besoin de recalcul
        
        super().save(*args, **kwargs)

        # Générer le PDF si manquant
        if not self.pdf:
            try:
                self.generate_pdf()
                if self.pdf:
                    # Utiliser update pour éviter la boucle récursive
                    InvoiceTransfert.objects.filter(id=self.id).update(pdf=self.pdf)
            except Exception as e:
                print(f"Erreur génération PDF: {e}")






class BalanceTransaction(models.Model): # « Le solde disponible global du compte Stripe a changé »: “À partir de maintenant, X € sont disponibles”
    # 🔑 Identifiant Stripe
    balance_txn_id = models.CharField(max_length=100, unique=True)
    
    # 💰 Informations financières de base
    amount = models.IntegerField(default=0)
    fee = models.IntegerField(default=0)
    net = models.IntegerField(default=0) 
    currency = models.CharField(max_length=10, default='eur')
    status = models.CharField(max_length=50, blank=True, null=True)
    
    # 📅 Gestion de la disponibilité des fonds
    is_available = models.BooleanField(default=False) # montant disponible ou non
    available_on = models.DateTimeField(blank=True, null=True) # Date de disponibité attendue

    # Traitement de la balance est terminé suite à l'évènement balance.available
    is_settled = models.BooleanField(default=False)
    
    # 🏷️ Type et contexte de l'événement
    event_type = models.CharField(
        max_length=50, blank=True, null=True,
        help_text="Ex: payment_intent.succeeded, refund.created, transfer.created, payout.created, charge.dispute.created"
    )
    
    # 💳 NOUVEAUX CHAMPS - Informations de la source de paiement
    payment_method_brand = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        help_text="Marque de la carte: visa, mastercard, amex, etc."
    )
    
    payment_method_last4 = models.CharField(
        max_length=4, 
        blank=True, 
        null=True,
        help_text="4 derniers chiffres de la carte"
    )
    
    payment_method_country = models.CharField(
        max_length=2, 
        blank=True, 
        null=True,
        help_text="Code pays ISO 2 lettres de la carte"
    )
    
    payment_method_type = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Type de moyen de paiement: card, bank_transfer, etc."
    )
    
    # 📍 NOUVEAUX CHAMPS - Informations géographiques et techniques
    ip_country = models.CharField(
        max_length=2,
        blank=True,
        null=True,
        help_text="Pays de l'IP utilisée pour le paiement"
    )
    
    # 🏦 NOUVEAUX CHAMPS - Détails des frais détaillés
    stripe_fee = models.IntegerField(
        default=0,
        help_text="Frais Stripe spécifiques (hors taxes)"
    )
    
    tax_fee = models.IntegerField(
        default=0,
        help_text="Montant des taxes appliquées aux frais"
    )
    
    # 📊 Métadonnées supplémentaires
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description Stripe de la transaction"
    )
    
    # ⏰ Horodatages
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.event_type} → {self.balance_txn_id} ({self.net/100:.2f} {self.currency})"



class PaymentIntentTransaction(models.Model):
    balance_txn = models.OneToOneField(BalanceTransaction, on_delete=models.CASCADE)
    payment_intent_id = models.CharField(max_length=100, db_index=True)
    charge_id = models.CharField(max_length=100, unique=True) # c'est la charge finale 
    
    def __str__(self):
        return f"PI: {self.payment_intent_id} | Charge: {self.charge_id}"



##################
# à supprimer
##################

