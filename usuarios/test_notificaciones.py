from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from bson import ObjectId
from django.test import SimpleTestCase
from rest_framework.test import APIClient


class NotificacionApiTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_id = ObjectId()
        self.pasajero_id = ObjectId()
        self.notificacion_id = ObjectId()
        self.administrador = {
            '_id': self.admin_id,
            'nombre_completo': 'Administradora de prueba',
            'rol': 'administrador',
        }
        self.pasajero = {
            '_id': self.pasajero_id,
            'nombre_completo': 'Pasajero de prueba',
            'rol': 'pasajero',
        }
        self.notificacion = {
            '_id': self.notificacion_id,
            'titulo': 'Aviso de prueba',
            'cuerpo': 'Contenido de la notificación de prueba.',
            'fecha_creacion': datetime(2026, 11, 2, tzinfo=timezone.utc),
            'administrador': {
                'id_admin': self.admin_id,
                'nombre': self.administrador['nombre_completo'],
            },
            'destinatarios': [
                {'id_pasajero': self.pasajero_id, 'leido': False},
            ],
        }
        self.notificaciones = MagicMock()
        self.usuarios = MagicMock()
        self.db = SimpleNamespace(
            notificaciones=self.notificaciones,
            usuarios=self.usuarios,
        )

    def _datos_notificacion(self):
        return {
            'id_admin': str(self.admin_id),
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
        self.assertEqual(respuesta.data[0]['id_notificacion'], str(self.notificacion_id))
        self.assertEqual(respuesta.data[0]['id_admin'], str(self.admin_id))
        self.assertEqual(
            respuesta.data[0]['destinatarios'][0]['id_pasajero'],
            str(self.pasajero_id),
        )

    @patch('usuarios.notificacion_views.get_mongo_db')
    def test_crear_guarda_documento_mongo_y_devuelve_object_ids(self, get_mongo_db):
        self.usuarios.find_one.return_value = self.administrador
        self.usuarios.find.return_value = [self.pasajero]
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
        self.assertEqual(guardado['administrador']['id_admin'], self.admin_id)
        self.assertEqual(guardado['destinatarios'][0]['id_pasajero'], self.pasajero_id)

    @patch('usuarios.notificacion_views.get_mongo_db')
    def test_crud_actualizar_eliminar_y_consultar(self, get_mongo_db):
        self.usuarios.find_one.return_value = self.administrador
        self.usuarios.find.return_value = [self.pasajero]
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
    def test_administrador_inexistente_devuelve_400(self, get_mongo_db):
        self.usuarios.find_one.return_value = None
        get_mongo_db.return_value = self.db

        respuesta = self.client.post(
            '/api/notificaciones/',
            self._datos_notificacion(),
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
