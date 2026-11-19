from django.urls import path

from .views import (
    ReservaCancelView,
    ReservaDetailView,
    ReservaListCreateView,
    ReservaPagoConfirmarView,
    ReservaPagoRechazarView,
    ReservaPagoReembolsarView,
)


urlpatterns = [
    path('reservas/', ReservaListCreateView.as_view(), name='reservas-list-create'),
    path(
        'reservas/<str:reserva_id>/cancelar/',
        ReservaCancelView.as_view(),
        name='reservas-cancelar',
    ),
    path(
        'reservas/<str:reserva_id>/pago/confirmar/',
        ReservaPagoConfirmarView.as_view(),
        name='reserva-pago-confirmar',
    ),
    path(
        'reservas/<str:reserva_id>/pago/rechazar/',
        ReservaPagoRechazarView.as_view(),
        name='reserva-pago-rechazar',
    ),
    path(
        'reservas/<str:reserva_id>/pago/reembolsar/',
        ReservaPagoReembolsarView.as_view(),
        name='reserva-pago-reembolsar',
    ),
    path('reservas/<str:reserva_id>/', ReservaDetailView.as_view(), name='reservas-detail'),
]
