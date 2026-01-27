
from django.contrib import admin
from .models import Cart
from .models import CartItem
from .models import Invoice
from .models import PaymentIntentTransaction
from .models import BalanceTransaction
from .models import InvoiceTransfert
from .models import CartTransfertItem
from .models import CartTransfert




# Register your models here.
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Invoice)
admin.site.register(PaymentIntentTransaction)
admin.site.register(BalanceTransaction)
admin.site.register(InvoiceTransfert)
admin.site.register(CartTransfertItem)
admin.site.register(CartTransfert)