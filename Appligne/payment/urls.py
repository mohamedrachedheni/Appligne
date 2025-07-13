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
]