from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, identify_hasher
from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from usuarios.authentication import CookieJWTAuthentication
from usuarios.models import Usuario


class AuthenticationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)

    def _csrf_headers(self):
        response = self.client.get('/api/auth/csrf/')
        self.assertEqual(response.status_code, 200)
        return {'HTTP_X_CSRFTOKEN': response.data['csrfToken']}

    def test_login_rejects_missing_csrf_token(self):
        response = self.client.post(
            '/api/auth/login/',
            {
                'correo_electronico': 'ana@example.test',
                'contrasenia': 'Clave-segura-2026!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertNotIn(settings.JWT_ACCESS_COOKIE_NAME, response.cookies)

    def test_login_accepts_configured_lan_frontend_origin(self):
        client = APIClient(enforce_csrf_checks=True)
        account = get_user_model().objects.create_user(
            username='lan-user',
            email='lan@example.test',
            password='Clave-segura-2026!',
        )
        Usuario.objects.create(cuenta=account, nombre_completo='Usuario LAN')
        origin = 'http://192.168.56.1:5173'
        csrf_response = client.get('/api/auth/csrf/', HTTP_ORIGIN=origin)

        response = client.post(
            '/api/auth/login/',
            {
                'correo_electronico': account.email,
                'contrasenia': 'Clave-segura-2026!',
            },
            format='json',
            HTTP_ORIGIN=origin,
            HTTP_X_CSRFTOKEN=csrf_response.data['csrfToken'],
        )

        self.assertEqual(response.status_code, 200)

    def test_login_uses_postgres_and_sets_httponly_jwt_cookies(self):
        user_model = get_user_model()
        account = user_model.objects.create_user(
            username='legacy-username',
            email='ana@example.test',
            password='Clave-segura-2026!',
        )
        Usuario.objects.create(
            cuenta=account,
            nombre_completo='Ana Pérez',
            telefono='5551234',
            direccion_retorno='Av. Central 123',
        )

        response = self.client.post('/api/auth/login/', {
            'correo_electronico': 'ANA@example.test',
            'contrasenia': 'Clave-segura-2026!',
        }, format='json', **self._csrf_headers())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {
            'role': Usuario.Rol.PASAJERO,
            'nombre_completo': 'Ana Pérez',
        })

        access_cookie = response.cookies[settings.JWT_ACCESS_COOKIE_NAME]
        refresh_cookie = response.cookies[settings.JWT_REFRESH_COOKIE_NAME]
        self.assertEqual(
            AccessToken(access_cookie.value)['user_id'],
            str(account.pk),
        )
        self.assertTrue(access_cookie['httponly'])
        self.assertTrue(refresh_cookie['httponly'])
        self.assertEqual(bool(access_cookie['secure']), settings.JWT_COOKIE_SECURE)
        self.assertEqual(access_cookie['samesite'], settings.JWT_COOKIE_SAMESITE)

    def test_current_profile_endpoint_returns_only_reservation_profile_data(self):
        account = get_user_model().objects.create_user(
            username='profile-user',
            email='profile@example.test',
            password='Clave-segura-2026!',
        )
        Usuario.objects.create(
            cuenta=account,
            nombre_completo='Ana Pérez',
            telefono='5551234',
            direccion_retorno='Av. Central 123',
        )
        self.client.cookies[settings.JWT_ACCESS_COOKIE_NAME] = str(
            AccessToken.for_user(account),
        )

        response = self.client.get('/api/auth/profile/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {
            'nombre_completo': 'Ana Pérez',
            'correo_electronico': 'profile@example.test',
            'telefono': '5551234',
            'direccion_retorno_predeterminada': 'Av. Central 123',
        })

    def test_current_profile_endpoint_requires_authentication(self):
        response = self.client.get('/api/auth/profile/')

        self.assertEqual(response.status_code, 401)

    def test_login_rejects_incorrect_password(self):
        account = get_user_model().objects.create_user(
            username='ana',
            email='ana@example.test',
            password='Clave-correcta-2026!',
        )
        Usuario.objects.create(cuenta=account, nombre_completo='Ana Pérez')

        response = self.client.post('/api/auth/login/', {
            'correo_electronico': 'ana@example.test',
            'contrasenia': 'Clave-incorrecta-2026!',
        }, format='json', **self._csrf_headers())

        self.assertEqual(response.status_code, 401)

    def test_registration_creates_django_account_and_passenger_profile(self):
        response = self.client.post('/api/auth/register/', {
            'nombre_completo': 'Camila Soto',
            'correo_electronico': 'Camila@example.test',
            'contrasenia': 'Boleto-seguro-2026!',
            'telefono': '5559876',
            'direccion_retorno_predeterminada': 'Calle Norte 45',
            'rol': 'administrador',
        }, format='json', **self._csrf_headers())

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data, {'detail': 'Cuenta creada correctamente.'})
        account = get_user_model().objects.get(email='camila@example.test')
        profile = Usuario.objects.get(cuenta=account)
        self.assertEqual(account.username, 'camila@example.test')
        self.assertTrue(check_password('Boleto-seguro-2026!', account.password))
        self.assertEqual(identify_hasher(account.password).algorithm, 'pbkdf2_sha256')
        self.assertEqual(profile.nombre_completo, 'Camila Soto')
        self.assertEqual(profile.rol, Usuario.Rol.PASAJERO)
        self.assertEqual(profile.telefono, '5559876')
        self.assertEqual(profile.direccion_retorno, 'Calle Norte 45')

    def test_registration_rejects_duplicate_email(self):
        user_model = get_user_model()
        account = user_model.objects.create_user(
            username='existing-user',
            email='existing@example.test',
            password='Clave-segura-2026!',
        )
        Usuario.objects.create(cuenta=account, nombre_completo='Usuario existente')

        response = self.client.post('/api/auth/register/', {
            'nombre_completo': 'Otro usuario',
            'correo_electronico': 'EXISTING@example.test',
            'contrasenia': 'Otra-clave-segura-2026!',
        }, format='json', **self._csrf_headers())

        self.assertEqual(response.status_code, 409)

    def test_database_rejects_case_insensitive_duplicate_emails(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            username='first-account',
            email='same@example.test',
            password='Clave-segura-2026!',
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                user_model.objects.create_user(
                    username='second-account',
                    email='SAME@example.test',
                    password='Clave-segura-2026!',
                )

    def test_account_cannot_be_deleted_while_profile_exists(self):
        account = get_user_model().objects.create_user(
            username='protected-account',
            email='protected@example.test',
            password='Clave-segura-2026!',
        )
        Usuario.objects.create(cuenta=account, nombre_completo='Cuenta protegida')

        with self.assertRaises(ProtectedError):
            account.delete()

    def test_registration_supports_long_emails_with_unique_django_username(self):
        email = f"{'a' * 145}@example.test"
        payload = {
            'nombre_completo': 'Usuario de correo largo',
            'correo_electronico': email,
            'contrasenia': 'Boleto-seguro-2026!',
        }

        response = self.client.post(
            '/api/auth/register/',
            payload,
            format='json',
            **self._csrf_headers(),
        )
        duplicate_response = self.client.post(
            '/api/auth/register/',
            payload,
            format='json',
            **self._csrf_headers(),
        )

        self.assertEqual(response.status_code, 201)
        account = get_user_model().objects.get(email=email)
        self.assertNotEqual(account.username, email)
        self.assertLessEqual(len(account.username), 150)
        self.assertEqual(duplicate_response.status_code, 409)

    def test_refresh_uses_cookie_without_returning_access_token(self):
        account = get_user_model().objects.create_user(
            username='ana',
            email='ana@example.test',
            password='Clave-segura-2026!',
        )
        refresh_token = RefreshToken.for_user(account)
        self.client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = str(refresh_token)

        response = self.client.post(
            '/api/auth/refresh/',
            {},
            format='json',
            **self._csrf_headers(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'detail': 'Sesión renovada.'})
        self.assertEqual(
            AccessToken(
                response.cookies[settings.JWT_ACCESS_COOKIE_NAME].value,
            )['user_id'],
            str(account.pk),
        )
        self.assertNotIn('access', response.data)

    def test_logout_clears_authentication_cookies(self):
        self.client.cookies[settings.JWT_ACCESS_COOKIE_NAME] = 'access'
        self.client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = 'refresh'

        response = self.client.post(
            '/api/auth/logout/',
            {},
            format='json',
            **self._csrf_headers(),
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.cookies[settings.JWT_ACCESS_COOKIE_NAME].value, '')
        self.assertEqual(response.cookies[settings.JWT_REFRESH_COOKIE_NAME].value, '')

    def test_protected_route_rejects_missing_or_inactive_account_cookie(self):
        self.assertEqual(self.client.get('/api/reservas/').status_code, 401)

        account = get_user_model().objects.create_user(
            username='inactive',
            email='inactive@example.test',
            password='Clave-segura-2026!',
        )
        access_token = AccessToken.for_user(account)
        account.is_active = False
        account.save(update_fields=['is_active'])
        self.client.cookies[settings.JWT_ACCESS_COOKIE_NAME] = str(access_token)

        response = self.client.get('/api/reservas/')

        self.assertEqual(response.status_code, 401)

    def test_cookie_authentication_does_not_load_password_column(self):
        account = get_user_model().objects.create_user(
            username='cookie-user',
            email='cookie@example.test',
            password='Clave-segura-2026!',
        )
        request = APIRequestFactory().get('/api/reservas/')
        request.COOKIES[settings.JWT_ACCESS_COOKIE_NAME] = str(
            AccessToken.for_user(account),
        )

        user, _ = CookieJWTAuthentication().authenticate(Request(request))

        self.assertEqual(user.pk, account.pk)
        self.assertIn('password', user.get_deferred_fields())
