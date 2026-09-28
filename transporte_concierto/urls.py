from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PasajeroViewSet,
    AdministradorViewSet,
    NotificacionViewSet,
    VehiculoViewSet,
    ViajeAConciertoViewSet,
    ViajeUsaVehiculoViewSet,
    ReservaViewSet,
    AsientoReservaViewSet,
    PagoViewSet,
)

router = DefaultRouter()
router.register(r'pasajeros', PasajeroViewSet, basename='pasajero')
router.register(r'administradores', AdministradorViewSet, basename='administrador')
router.register(r'notificaciones', NotificacionViewSet, basename='notificacion')
router.register(r'vehiculos', VehiculoViewSet, basename='vehiculo')
router.register(r'viajes', ViajeAConciertoViewSet, basename='viaje')
router.register(r'viaje-vehiculos', ViajeUsaVehiculoViewSet, basename='viaje-vehiculo')
router.register(r'reservas', ReservaViewSet, basename='reserva')
router.register(r'asientos', AsientoReservaViewSet, basename='asiento')
router.register(r'pagos', PagoViewSet, basename='pago')

urlpatterns = [
    path('', include(router.urls)),
]
