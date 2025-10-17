# payment>urls.py

from django.urls import path
from . import views

app_name = 'payment'

urlpatterns = [
    path('checkout/', views.create_checkout_session, name='checkout'),
    path('success/', views.payment_success, name='success'),
    path('cancel/', views.payment_cancel, name='cancel'),
    path('stripe_webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('invoice/<int:invoice_id>/download/', views.download_invoice, name='download_invoice'),
    path('compte_stripe/', views.compte_stripe, name='compte_stripe'),

    # Nouvelles URLs pour les transferts
    path('transfert/create/', views.create_transfert_session, name='create_transfert'),
    path('transfert/success/', views.transfert_success, name='transfert_success'),
    path('transfert/cancel/', views.transfert_cancel, name='transfert_cancel'),
    # path('stripe_transfert_webhook/', views.stripe_transfert_webhook, name='stripe_transfert_webhook'),

    # Nouvelles URLs pour les refund_payment
    path('refund_payment/', views.refund_payment, name='refund_payment'),

]
