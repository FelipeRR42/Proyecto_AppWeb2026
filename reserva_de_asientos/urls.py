from django.urls import path

from .views import ReservaCancelView, ReservaDetailView, ReservaListCreateView


urlpatterns = [
    path('reservas/', ReservaListCreateView.as_view(), name='reservas-list-create'),
    path(
        'reservas/<str:reserva_id>/cancelar/',
        ReservaCancelView.as_view(),
        name='reservas-cancelar',
    ),
    path('reservas/<str:reserva_id>/', ReservaDetailView.as_view(), name='reservas-detail'),
]
