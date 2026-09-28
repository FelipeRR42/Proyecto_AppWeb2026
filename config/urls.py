"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from transporte_concierto import views

urlpatterns = [
    path('', views.home, name='home'),
    
    # Endpoints GET (Consultas SELECT)
    path('api/pagos/', views.listar_pagos, name='listar_pagos'),
    path('api/viajes/pendientes/', views.listar_viajes_pendientes, name='viajes_pendientes'),
    path('api/pasajeros/reservas/', views.listar_pasajeros_reserva, name='pasajeros_reservas'),
    
    # Endpoints de Escritura y Eliminación (POST / DELETE)
    path('api/viajes/nuevo/', views.registrar_viaje_pendiente, name='nuevo_viaje'),
    path('api/viajes/asignar-vehiculo/', views.asignar_vehiculo, name='asignar_vehiculo'),
    path('api/viajes/<int:id_viaje>/eliminar/', views.eliminar_viaje, name='eliminar_viaje'),
    
    path('admin/', admin.site.urls),
]
]
