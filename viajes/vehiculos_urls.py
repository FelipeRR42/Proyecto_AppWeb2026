from django.urls import path

from .vehiculos_api import VehiculoDetailView, VehiculoListCreateView


urlpatterns = [
	path('', VehiculoListCreateView.as_view(), name='vehiculos-list-create'),
	path('<str:patente>/', VehiculoDetailView.as_view(), name='vehiculos-detail'),
]