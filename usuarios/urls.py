from django.urls import path

from .views import (
    AdministradorDetailView,
    AdministradorListCreateView,
    CsrfTokenView,
    CurrentUserProfileView,
    LoginView,
    LogoutView,
    PasajeroDetailView,
    PasajeroListCreateView,
    RefreshCookieView,
    RegistroView,
    UsuarioDetailView,
    UsuarioListCreateView,
)


urlpatterns = [
    path('auth/register/', RegistroView.as_view(), name='auth-register'),
    path('auth/csrf/', CsrfTokenView.as_view(), name='auth-csrf'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/profile/', CurrentUserProfileView.as_view(), name='auth-profile'),
    path('auth/refresh/', RefreshCookieView.as_view(), name='auth-refresh'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('pasajeros/', PasajeroListCreateView.as_view(), name='pasajeros-list-create'),
    path('pasajeros/<str:usuario_id>/', PasajeroDetailView.as_view(), name='pasajeros-detail'),
    path('administradores/', AdministradorListCreateView.as_view(), name='administradores-list-create'),
    path('administradores/<str:usuario_id>/', AdministradorDetailView.as_view(), name='administradores-detail'),
    path('usuarios/', UsuarioListCreateView.as_view(), name='usuarios-list-create'),
    path('usuarios/<str:usuario_id>/', UsuarioDetailView.as_view(), name='usuarios-detail'),
]