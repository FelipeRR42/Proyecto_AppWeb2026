from django.contrib import admin
from .models import Usuario, Pasajero, Administrador, Notificacion, PasajeroRecibeNotificacion

admin.site.register(Usuario)
admin.site.register(Pasajero)
admin.site.register(Administrador)
admin.site.register(Notificacion)
admin.site.register(PasajeroRecibeNotificacion)