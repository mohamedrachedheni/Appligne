
from django.contrib import admin
from .models import Cart
from .models import CartItem
from .models import Invoice


# Register your models here.
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Invoice)