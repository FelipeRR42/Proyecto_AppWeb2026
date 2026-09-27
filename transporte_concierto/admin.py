from django.contrib import admin
from .models import (
    Pasajero, Administrador, Notificacion, PasajeroRecibeNotificacion,
    ViajeAConcierto, Reserva, AsientoReserva, Pago, Vehiculo, ViajeUsaVehiculo,
)


@admin.register(Pasajero)
class PasajeroAdmin(admin.ModelAdmin):
    list_display = ('id_pasajero', 'nombre_completo', 'telefono', 'correo_electronico')
    search_fields = ('nombre_completo', 'correo_electronico')


@admin.register(Administrador)
class AdministradorAdmin(admin.ModelAdmin):
    list_display = ('id_admin', 'nombre_completo', 'correo_electronico')
    search_fields = ('nombre_completo', 'correo_electronico')


class PasajeroRecibeNotificacionInline(admin.TabularInline):
    model = PasajeroRecibeNotificacion
    extra = 1


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('id_notificacion', 'titulo')
    search_fields = ('titulo',)
    inlines = [PasajeroRecibeNotificacionInline]


class ViajeUsaVehiculoInline(admin.TabularInline):
    model = ViajeUsaVehiculo
    extra = 1


@admin.register(ViajeAConcierto)
class ViajeAConciertoAdmin(admin.ModelAdmin):
    list_display = ('id_viaje', 'titulo', 'fecha_viaje', 'recinto', 'estado', 'administrador')
    list_filter = ('estado', 'recinto')
    search_fields = ('titulo', 'recinto')
    inlines = [ViajeUsaVehiculoInline]


class AsientoReservaInline(admin.TabularInline):
    model = AsientoReserva
    extra = 1


class PagoInline(admin.StackedInline):
    model = Pago
    extra = 0


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('id_reserva', 'pasajero', 'viaje', 'fecha_reserva', 'tipo_viaje', 'estado')
    list_filter = ('estado', 'tipo_viaje')
    search_fields = ('pasajero__nombre_completo',)
    inlines = [AsientoReservaInline, PagoInline]


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ('patente', 'modelo', 'capacidad_maxima')
    search_fields = ('patente', 'modelo')