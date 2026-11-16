from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from bson import ObjectId
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from usuarios.models import Usuario


class NotificacionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user_model = get_user_model()
        self.admin_account = user_model.objects.create_user(
            username='admin-test',
            email='admin@example.test',
            password='Clave-segura-2026!',
        )
        self.pasajero_account = user_model.objects.create_user(
            username='pasajero-test',
            email='pasajero@example.test',
            password='Clave-segura-2026!',
        )
        Usuario.objects.create(
            cuenta=self.admin_account,
            nombre_completo='Administradora de prueba',
            rol=Usuario.Rol.ADMINISTRADOR,
        )
        Usuario.objects.create(
            cuenta=self.pasajero_account,
            nombre_completo='Pasajero de prueba',
            rol=Usuario.Rol.PASAJERO,
        )
        self.client.force_authenticate(user=self.admin_account)
        self.admin_id = self.admin_account.pk
        self.pasajero_id = self.pasajero_account.pk
        self.notificacion_id = ObjectId()
        self.notificacion = {
            '_id': self.notificacion_id,
            'titulo': 'Aviso de prueba',
            'cuerpo': 'Contenido de la notificación de prueba.',
            'fecha_creacion': datetime(2026, 11, 2, tzinfo=timezone.utc),
            'administrador': {
                'id_admin': self.admin_id,
                'nombre': 'Administradora de prueba',
            },
            'destinatarios': [
                {'id_pasajero': self.pasajero_id, 'leido': False},
            ],
        }
        self.notificaciones = MagicMock()
        self.db = SimpleNamespace(
            notificaciones=self.notificaciones,
        )

    def _datos_notificacion(self):
        return {
            'titulo': 'Aviso de prueba',
            'cuerpo': 'Contenido de la notificación de prueba.',
            'destinatarios': [
                {'id_pasajero': str(self.pasajero_id), 'leido': False},
            ],
        }

    @patch('usuarios.notificacion_views.get_mongo_db')
    def test_listar_devuelve_notificaciones_con_object_id_como_texto(self, get_mongo_db):
        self.notificaciones.find.return_value = [self.notificacion]
        get_mongo_db.return_value = self.db

        respuesta = self.client.get('/api/notificaciones/')

        self.assertEqual(respuesta.status_code, 200)
        self.notificaciones.find.assert_called_once_with({})
        self.assertEqual(respuesta.data[0]['id_notificacion'], str(self.notificacion_id))
        self.assertEqual(respuesta.data[0]['id_admin'], str(self.admin_id))
        self.assertEqual(
            respuesta.data[0]['destinatarios'][0]['id_pasajero'],
            str(self.pasajero_id),
        )

    @patch('usuarios.notificacion_views.get_mongo_db')
    def test_crear_guarda_documento_mongo_y_devuelve_object_ids(self, get_mongo_db):
        self.notificaciones.insert_one.return_value = SimpleNamespace(
            inserted_id=self.notificacion_id,
        )
        get_mongo_db.return_value = self.db

        respuesta = self.client.post(
            '/api/notificaciones/',
            self._datos_notificacion(),
            format='json',
        )

        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.data['id_notificacion'], str(self.notificacion_id))
        self.assertEqual(respuesta.data['id_admin'], str(self.admin_id))
        guardado = self.notificaciones.insert_one.call_args.args[0]
        self.assertEqual(guardado['administrador']['id_admin'], str(self.admin_id))
        self.assertEqual(guardado['destinatarios'][0]['id_pasajero'], str(self.pasajero_id))

    @patch('usuarios.notificacion_views.get_mongo_db')
    def test_crud_actualizar_eliminar_y_consultar(self, get_mongo_db):
        self.notificaciones.find_one.side_effect = [
            self.notificacion,
            self.notificacion,
            {**self.notificacion, 'titulo': 'Aviso actualizado'},
            self.notificacion,
            {**self.notificacion, 'cuerpo': 'Contenido editado.'},
        ]
        self.notificaciones.delete_one.return_value = SimpleNamespace(deleted_count=1)
        get_mongo_db.return_value = self.db

        detail_url = f'/api/notificaciones/{self.notificacion_id}/'
        obtener = self.client.get(detail_url)
        reemplazar = self.client.put(
            detail_url,
            {**self._datos_notificacion(), 'titulo': 'Aviso actualizado'},
            format='json',
        )
        actualizar = self.client.patch(
            detail_url,
            {'cuerpo': 'Contenido editado.'},
            format='json',
        )
        eliminar = self.client.delete(detail_url)

        self.assertEqual(obtener.status_code, 200)
        self.assertEqual(reemplazar.status_code, 200)
        self.assertEqual(reemplazar.data['titulo'], 'Aviso actualizado')
        self.assertEqual(actualizar.status_code, 200)
        self.assertEqual(actualizar.data['cuerpo'], 'Contenido editado.')
        self.assertEqual(eliminar.status_code, 204)
        self.notificaciones.delete_one.assert_called_once_with(
            {'_id': self.notificacion_id},
        )

    @patch('usuarios.notificacion_views.get_mongo_db')
    def test_pasajero_solo_lista_sus_notificaciones(self, get_mongo_db):
        self.client.force_authenticate(user=self.pasajero_account)
        self.notificaciones.find.return_value = [self.notificacion]
        get_mongo_db.return_value = self.db

        respuesta = self.client.get('/api/notificaciones/')

        self.assertEqual(respuesta.status_code, 200)
        self.notificaciones.find.assert_called_once_with({
            'destinatarios.id_pasajero': str(self.pasajero_id),
        })

    @patch('usuarios.notificacion_views.get_mongo_db')
    def test_pasajero_no_puede_crear_notificacion(self, get_mongo_db):
        self.client.force_authenticate(user=self.pasajero_account)

        respuesta = self.client.post(
            '/api/notificaciones/',
            self._datos_notificacion(),
            format='json',
        )

        self.assertEqual(respuesta.status_code, 403)
        get_mongo_db.assert_not_called()

    @patch('usuarios.notificacion_views.get_mongo_db')
    def test_identificador_invalido_devuelve_400_sin_consultar_mongo(self, get_mongo_db):
        respuesta = self.client.get('/api/notificaciones/no-es-object-id/')

        self.assertEqual(respuesta.status_code, 400)
        get_mongo_db.assert_not_called()

    @patch('usuarios.notificacion_views.get_mongo_db')
    def test_notificacion_inexistente_devuelve_404(self, get_mongo_db):
        self.notificaciones.find_one.return_value = None
        get_mongo_db.return_value = self.db

        respuesta = self.client.get(f'/api/notificaciones/{self.notificacion_id}/')

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(respuesta.data, {'detail': 'Notificación no encontrada.'})

    @patch('usuarios.notificacion_views.get_mongo_db')
    def test_destinatario_inexistente_devuelve_400(self, get_mongo_db):
        get_mongo_db.return_value = self.db
        datos = self._datos_notificacion()
        datos['destinatarios'] = [{'id_pasajero': 999999, 'leido': False}]

        respuesta = self.client.post(
            '/api/notificaciones/',
            datos,
            format='json',
        )

        self.assertEqual(respuesta.status_code, 400)

    @patch('usuarios.notificacion_views.get_mongo_db', side_effect=ValueError('MongoDB no disponible'))
    def test_error_de_mongo_devuelve_500(self, _get_mongo_db):
        respuesta = self.client.get('/api/notificaciones/')

        self.assertEqual(respuesta.status_code, 500)
        self.assertEqual(
            respuesta.data,
            {'detail': 'Error interno al procesar la solicitud.'},
        )
