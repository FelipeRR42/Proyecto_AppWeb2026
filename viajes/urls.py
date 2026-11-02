from django.urls import path

from .views import ViajeDetailView, ViajeListCreateView


urlpatterns = [
	path('', ViajeListCreateView.as_view(), name='viajes-list-create'),
	path('<str:viaje_id>/', ViajeDetailView.as_view(), name='viajes-detail'),
]