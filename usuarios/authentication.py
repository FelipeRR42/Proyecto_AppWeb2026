from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.permissions import SAFE_METHODS
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.settings import api_settings


def enforce_csrf(request):
    django_request = getattr(request, '_request', request)
    check = CSRFCheck(lambda current_request: None)
    check.process_request(django_request)
    reason = check.process_view(django_request, None, (), {})
    if reason:
        raise PermissionDenied(f'CSRF Failed: {reason}')


def set_access_cookie(response, access_token):
    lifetime = settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
    response.set_cookie(
        settings.JWT_ACCESS_COOKIE_NAME,
        access_token,
        max_age=int(lifetime.total_seconds()),
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        path=settings.JWT_ACCESS_COOKIE_PATH,
    )


def set_refresh_cookie(response, refresh_token):
    lifetime = settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=int(lifetime.total_seconds()),
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        path=settings.JWT_REFRESH_COOKIE_PATH,
    )


def clear_auth_cookies(response):
    response.delete_cookie(
        settings.JWT_ACCESS_COOKIE_NAME,
        path=settings.JWT_ACCESS_COOKIE_PATH,
        samesite=settings.JWT_COOKIE_SAMESITE,
    )
    response.delete_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        path=settings.JWT_REFRESH_COOKIE_PATH,
        samesite=settings.JWT_COOKIE_SAMESITE,
    )


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        raw_token = request.COOKIES.get(settings.JWT_ACCESS_COOKIE_NAME)
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        if request.method not in SAFE_METHODS:
            enforce_csrf(request)
        return self.get_user(validated_token), validated_token

    def get_user(self, validated_token):
        user_id = validated_token.get(api_settings.USER_ID_CLAIM)
        if user_id is None:
            raise AuthenticationFailed('El token no identifica una cuenta.')

        user_model = get_user_model()
        try:
            user = user_model._default_manager.only('pk', 'is_active').get(
                **{api_settings.USER_ID_FIELD: user_id},
            )
        except user_model.DoesNotExist as error:
            raise AuthenticationFailed('La cuenta del token no existe.') from error
        except (TypeError, ValueError) as error:
            raise AuthenticationFailed(
                'El token contiene un identificador inválido.',
            ) from error

        if not user.is_active:
            raise AuthenticationFailed('La cuenta está desactivada.')
        return user

    def authenticate_header(self, request):
        return 'Bearer'
