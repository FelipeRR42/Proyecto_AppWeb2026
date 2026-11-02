from django.urls import path

from .views import ReservaDetailView, ReservaListCreateView


urlpatterns = [
    path('reservas/', ReservaListCreateView.as_view(), name='reservas-list-create'),
    path('reservas/<str:reserva_id>/', ReservaDetailView.as_view(), name='reservas-detail'),
]
