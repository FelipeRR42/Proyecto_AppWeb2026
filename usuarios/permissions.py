from rest_framework.permissions import BasePermission

from .models import Usuario


def get_app_profile(user):
    if not user or not user.is_authenticated:
        return None
    try:
        return user.perfil
    except Usuario.DoesNotExist:
        return None


def is_app_administrator(user):
    profile = get_app_profile(user)
    return profile is not None and profile.rol == Usuario.Rol.ADMINISTRADOR


class IsPassengerOrAdministrator(BasePermission):
    message = 'Se requiere un perfil de pasajero o administrador.'

    def has_permission(self, request, view):
        profile = get_app_profile(request.user)
        return profile is not None and profile.rol in (
            Usuario.Rol.PASAJERO,
            Usuario.Rol.ADMINISTRADOR,
        )


class IsAppAdministrator(BasePermission):
    message = 'Se requiere un perfil de administrador.'

    def has_permission(self, request, view):
        return is_app_administrator(request.user)
