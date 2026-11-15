from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from usuarios.models import Usuario


class AuthenticationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_login_by_email_uses_django_account_and_returns_jwt(self):
        user_model = get_user_model()
        account = user_model.objects.create_user(
            username='legacy-username',
            email='ana@example.test',
            password='Clave-segura-2026!',
        )
        profile = Usuario.objects.create(
            cuenta=account,
            nombre_completo='Ana Pérez',
            telefono='5551234',
            direccion_retorno='Av. Central 123',
        )

        response = self.client.post('/api/auth/login/', {
            'correo_electronico': 'ANA@example.test',
            'contrasenia': 'Clave-segura-2026!',
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['role'], Usuario.Rol.PASAJERO)
        self.assertEqual(response.data['user']['id'], str(profile.pk))
        self.assertEqual(response.data['user']['nombre_completo'], 'Ana Pérez')
        self.assertEqual(response.data['user']['telefono'], '5551234')
        self.assertEqual(
            response.data['user']['direccion_retorno_predeterminada'],
            'Av. Central 123',
        )
        self.assertEqual(AccessToken(response.data['access'])['user_id'], str(account.pk))
        self.assertTrue(response.data['refresh'])

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
        }, format='json')

        self.assertEqual(response.status_code, 401)

    def test_registration_creates_django_account_and_passenger_profile(self):
        response = self.client.post('/api/auth/register/', {
            'nombre_completo': 'Camila Soto',
            'correo_electronico': 'Camila@example.test',
            'contrasenia': 'Boleto-seguro-2026!',
            'telefono': '5559876',
            'direccion_retorno_predeterminada': 'Calle Norte 45',
            'rol': 'administrador',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data, {'detail': 'Cuenta creada correctamente.'})
        account = get_user_model().objects.get(email='camila@example.test')
        profile = Usuario.objects.get(cuenta=account)
        self.assertEqual(account.username, 'camila@example.test')
        self.assertTrue(check_password('Boleto-seguro-2026!', account.password))
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
        }, format='json')

        self.assertEqual(response.status_code, 409)

    def test_registration_supports_long_emails_with_unique_django_username(self):
        email = f"{'a' * 145}@example.test"
        payload = {
            'nombre_completo': 'Usuario de correo largo',
            'correo_electronico': email,
            'contrasenia': 'Boleto-seguro-2026!',
        }

        response = self.client.post('/api/auth/register/', payload, format='json')
        duplicate_response = self.client.post(
            '/api/auth/register/',
            payload,
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        account = get_user_model().objects.get(email=email)
        self.assertNotEqual(account.username, email)
        self.assertLessEqual(len(account.username), 150)
        self.assertEqual(duplicate_response.status_code, 409)

    def test_refresh_endpoint_returns_new_access_token(self):
        account = get_user_model().objects.create_user(
            username='ana',
            email='ana@example.test',
            password='Clave-segura-2026!',
        )
        refresh_token = RefreshToken.for_user(account)

        response = self.client.post('/api/auth/refresh/', {
            'refresh': str(refresh_token),
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(AccessToken(response.data['access'])['user_id'], str(account.pk))
