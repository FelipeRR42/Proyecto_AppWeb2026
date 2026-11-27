from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.test import TestCase
from rest_framework.test import APIClient

from usuarios.models import Usuario


class UsuarioApiTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username='admin@example.test',
            email='admin@example.test',
            password='Boleto-admin-2026!',
        )
        Usuario.objects.create(
            cuenta=self.admin,
            nombre_completo='Administradora de prueba',
            rol=Usuario.Rol.ADMINISTRADOR,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_usuario_listado_lee_perfiles_de_postgresql(self):
        passenger = get_user_model().objects.create_user(
            username='ana@example.test',
            email='ana@example.test',
            password='Boleto-pasajero-2026!',
        )
        Usuario.objects.create(
            cuenta=passenger,
            nombre_completo='Ana Pérez',
            rol=Usuario.Rol.PASAJERO,
            telefono='5551234',
            direccion_retorno='Av. Central 123',
        )

        response = self.client.get('/api/usuarios/')

        self.assertEqual(response.status_code, 200)
        ana = next(item for item in response.data if item['id'] == str(passenger.pk))
        self.assertEqual(ana['rol'], Usuario.Rol.PASAJERO)
        self.assertEqual(ana['perfil_pasajero'], {
            'telefono': '5551234',
            'direccion_retorno_predeterminada': 'Av. Central 123',
        })
        self.assertNotIn('contrasenia', ana)

    def test_crear_usuario_guarda_cuenta_y_rol_en_postgresql(self):
        response = self.client.post('/api/usuarios/', {
            'nombre_completo': 'Ana Pérez',
            'correo_electronico': 'ana@example.test',
            'contrasenia': 'Boleto-pasajero-2026!',
            'rol': 'pasajero',
            'perfil_pasajero': {
                'telefono': '5551234',
                'direccion_retorno_predeterminada': 'Av. Central 123',
            },
        }, format='json')

        self.assertEqual(response.status_code, 201)
        account = get_user_model().objects.get(email='ana@example.test')
        profile = Usuario.objects.get(cuenta=account)
        self.assertTrue(check_password('Boleto-pasajero-2026!', account.password))
        self.assertEqual(response.data['id'], str(account.pk))
        self.assertEqual(profile.rol, Usuario.Rol.PASAJERO)
        self.assertEqual(profile.direccion_retorno, 'Av. Central 123')

    def test_creacion_de_usuario_rechaza_correo_duplicado(self):
        get_user_model().objects.create_user(
            username='ana@example.test',
            email='ana@example.test',
            password='Boleto-pasajero-2026!',
        )

        response = self.client.post('/api/usuarios/', {
            'nombre_completo': 'Otra Ana',
            'correo_electronico': 'ANA@example.test',
            'contrasenia': 'Boleto-pasajero-2026!',
        }, format='json')

        self.assertEqual(response.status_code, 409)

    def test_endpoints_de_usuario_usan_ids_de_postgresql_y_desactivan_sin_borrar(self):
        account = get_user_model().objects.create_user(
            username='ana@example.test',
            email='ana@example.test',
            password='Boleto-pasajero-2026!',
        )
        Usuario.objects.create(
            cuenta=account,
            nombre_completo='Ana Pérez',
            rol=Usuario.Rol.PASAJERO,
        )

        update = self.client.patch(
            f'/api/usuarios/{account.pk}/',
            {'nombre_completo': 'Ana Nueva'},
            format='json',
        )
        delete = self.client.delete(f'/api/usuarios/{account.pk}/')

        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.data['nombre_completo'], 'Ana Nueva')
        self.assertEqual(delete.status_code, 204)
        account.refresh_from_db()
        self.assertFalse(account.is_active)
        self.assertTrue(Usuario.objects.filter(cuenta=account).exists())

    def test_identificador_de_usuario_no_numerico_devuelve_400(self):
        response = self.client.get('/api/usuarios/no-es-numero/')

        self.assertEqual(response.status_code, 400)

    def test_pasajero_no_puede_administrar_usuarios(self):
        passenger = get_user_model().objects.create_user(
            username='pasajero@example.test',
            email='pasajero@example.test',
            password='Boleto-pasajero-2026!',
        )
        Usuario.objects.create(
            cuenta=passenger,
            nombre_completo='Pasajero de prueba',
            rol=Usuario.Rol.PASAJERO,
        )
        self.client.force_authenticate(user=passenger)

        response = self.client.get('/api/usuarios/')

        self.assertEqual(response.status_code, 403)

    def test_crear_pasajero_guarda_perfil_en_postgresql(self):
        response = self.client.post('/api/pasajeros/', {
            'nombre_completo': 'Ana Pérez',
            'correo_electronico': 'ana@example.test',
            'contrasenia': 'Boleto-pasajero-2026!',
            'direccion_retorno_predeterminada': 'Av. Central 123',
            'telefono': '5551234',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        account = get_user_model().objects.get(email='ana@example.test')
        profile = Usuario.objects.get(cuenta=account)
        self.assertEqual(profile.rol, Usuario.Rol.PASAJERO)
        self.assertEqual(profile.telefono, '5551234')
        self.assertEqual(profile.direccion_retorno, 'Av. Central 123')

    def test_crear_administrador_guarda_fecha_y_telefono_en_postgresql(self):
        response = self.client.post('/api/administradores/', {
            'nombre_completo': 'Camila Rojas',
            'correo_electronico': 'camila@example.test',
            'contrasenia': 'Boleto-admin-2026!',
            'fecha_contratacion': '2026-01-15',
            'telefono_corporativo': '5559876',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        profile = Usuario.objects.get(cuenta__email='camila@example.test')
        self.assertEqual(profile.rol, Usuario.Rol.ADMINISTRADOR)
        self.assertEqual(profile.fecha_contratacion.isoformat(), '2026-01-15')
        self.assertEqual(profile.telefono_corporativo, '5559876')

    def test_actualizar_pasajero_no_puede_modificar_un_administrador(self):
        response = self.client.patch(
            f'/api/pasajeros/{self.admin.pk}/',
            {'telefono': '5551234'},
            format='json',
        )

        self.assertEqual(response.status_code, 404)
