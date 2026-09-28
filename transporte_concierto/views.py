from rest_framework import viewsets
from .models import (
    Pasajero,
    Administrador,
    Notificacion,
    Vehiculo,
    ViajeAConcierto,
    ViajeUsaVehiculo,
    Reserva,
    AsientoReserva,
    Pago,
)
from .serializers import (
    PasajeroSerializer,
    AdministradorSerializer,
    NotificacionSerializer,
    VehiculoSerializer,
    ViajeAConciertoSerializer,
    ViajeUsaVehiculoSerializer,
    ReservaSerializer,
    AsientoReservaSerializer,
    PagoSerializer,
)


class PasajeroViewSet(viewsets.ModelViewSet):
    queryset = Pasajero.objects.all()
    serializer_class = PasajeroSerializer


class AdministradorViewSet(viewsets.ModelViewSet):
    queryset = Administrador.objects.all()
    serializer_class = AdministradorSerializer


class NotificacionViewSet(viewsets.ModelViewSet):
    queryset = Notificacion.objects.all()
    serializer_class = NotificacionSerializer


class VehiculoViewSet(viewsets.ModelViewSet):
    queryset = Vehiculo.objects.all()
    serializer_class = VehiculoSerializer


class ViajeAConciertoViewSet(viewsets.ModelViewSet):
    queryset = ViajeAConcierto.objects.select_related('administrador').prefetch_related('vehiculos').all()
    serializer_class = ViajeAConciertoSerializer


class ViajeUsaVehiculoViewSet(viewsets.ModelViewSet):
    queryset = ViajeUsaVehiculo.objects.all()
    serializer_class = ViajeUsaVehiculoSerializer


class ReservaViewSet(viewsets.ModelViewSet):
    queryset = Reserva.objects.select_related('pasajero', 'viaje').prefetch_related('asientos').all()
    serializer_class = ReservaSerializer


class AsientoReservaViewSet(viewsets.ModelViewSet):
    queryset = AsientoReserva.objects.all()
    serializer_class = AsientoReservaSerializer


class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.all()
    serializer_class = PagoSerializer
