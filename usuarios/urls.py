from django.urls import path

from .views import (
    AdministradorDetailView,
    AdministradorListCreateView,
    LoginView,
    PasajeroDetailView,
    PasajeroListCreateView,
    UsuarioDetailView,
    UsuarioListCreateView,
)


urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('pasajeros/', PasajeroListCreateView.as_view(), name='pasajeros-list-create'),
    path('pasajeros/<str:usuario_id>/', PasajeroDetailView.as_view(), name='pasajeros-detail'),
    path('administradores/', AdministradorListCreateView.as_view(), name='administradores-list-create'),
    path('administradores/<str:usuario_id>/', AdministradorDetailView.as_view(), name='administradores-detail'),
    path('usuarios/', UsuarioListCreateView.as_view(), name='usuarios-list-create'),
    path('usuarios/<str:usuario_id>/', UsuarioDetailView.as_view(), name='usuarios-detail'),
]