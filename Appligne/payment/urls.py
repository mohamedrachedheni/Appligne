# payment>urls.py

from django.urls import path
from . import views

app_name = 'payment'

urlpatterns = [
    path('checkout/', views.create_checkout_session, name='checkout'),
    path('success/', views.payment_success, name='success'),
    path('cancel/', views.payment_cancel, name='cancel'),
    path('webhooks/stripe/', views.stripe_webhook, name='webhook'),
    path('invoice/<int:invoice_id>/download/', views.download_invoice, name='download_invoice'),
    path('compte_stripe/', views.compte_stripe, name='compte_stripe'),
    path('compte_stripe_annuler/', views.compte_stripe_annuler, name='compte_stripe_annuler'),

    # Nouvelles URLs pour les transferts
    path('transfert/create/', views.create_transfert_session, name='create_transfert'),
    path('transfert/success/', views.transfert_success, name='transfert_success'),
    path('transfert/cancel/', views.transfert_cancel, name='transfert_cancel'),
    path('webhooks/stripe/transfert/', views.stripe_transfert_webhook, name='stripe_transfert_webhook'),

]