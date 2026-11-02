from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from bson import ObjectId
from django.contrib.auth.hashers import check_password
from django.test import SimpleTestCase
from rest_framework.test import APIClient
from datetime import datetime, timezone


class UsuarioApiTests(SimpleTestCase):
	def setUp(self):
		self.client = APIClient()
		self.usuario_id = ObjectId()
		self.usuario = {
			'_id': self.usuario_id,
			'nombre_completo': 'Ana Pérez',
			'correo_electronico': 'ana@example.com',
			'contrasenia': 'pbkdf2_sha256$test',
			'rol': 'pasajero',
			'perfil_pasajero': {'telefono': '5551234'},
			'perfil_admin': None,
		}
		self.collection = MagicMock()
		self.database = SimpleNamespace(usuarios=self.collection)

	@patch('usuarios.views.get_mongo_db')
	def test_lista_usuarios_devuelve_200_sin_contrasenias(self, get_mongo_db):
		self.collection.find.return_value = [self.usuario]
		get_mongo_db.return_value = self.database

		response = self.client.get('/api/usuarios/')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data[0]['id'], str(self.usuario_id))
		self.assertNotIn('contrasenia', response.data[0])

	@patch('usuarios.views.get_mongo_db')
	def test_crear_usuario_guarda_contrasenia_hasheada(self, get_mongo_db):
		self.collection.find_one.side_effect = [None, self.usuario]
		self.collection.insert_one.return_value = SimpleNamespace(inserted_id=self.usuario_id)
		get_mongo_db.return_value = self.database

		response = self.client.post('/api/usuarios/', {
			'nombre_completo': 'Ana Pérez',
			'correo_electronico': 'ana@example.com',
			'contrasenia': 'clave-segura-123',
		}, format='json')

		self.assertEqual(response.status_code, 201)
		saved = self.collection.insert_one.call_args.args[0]
		self.assertTrue(check_password('clave-segura-123', saved['contrasenia']))
		self.assertNotIn('contrasenia', response.data)

	@patch('usuarios.views.get_mongo_db')
	def test_correo_duplicado_devuelve_409(self, get_mongo_db):
		self.collection.find_one.return_value = self.usuario
		get_mongo_db.return_value = self.database

		response = self.client.post('/api/usuarios/', {
			'nombre_completo': 'Ana Pérez',
			'correo_electronico': 'ana@example.com',
			'contrasenia': 'clave-segura-123',
		}, format='json')

		self.assertEqual(response.status_code, 409)

	@patch('usuarios.views.get_mongo_db')
	def test_id_invalido_devuelve_400(self, get_mongo_db):
		response = self.client.get('/api/usuarios/no-es-object-id/')

		self.assertEqual(response.status_code, 400)
		get_mongo_db.assert_not_called()

	@patch('usuarios.views.get_mongo_db')
	def test_usuario_inexistente_devuelve_404(self, get_mongo_db):
		self.collection.find_one.return_value = None
		get_mongo_db.return_value = self.database

		response = self.client.get(f'/api/usuarios/{self.usuario_id}/')

		self.assertEqual(response.status_code, 404)

	@patch('usuarios.views.get_mongo_db')
	def test_error_de_mongo_devuelve_500(self, get_mongo_db):
		get_mongo_db.side_effect = ValueError('MongoDB no configurada')

		response = self.client.get('/api/usuarios/')

		self.assertEqual(response.status_code, 500)

	@patch('usuarios.views.get_mongo_db')
	def test_actualizar_y_eliminar_usuario(self, get_mongo_db):
		self.collection.find_one.side_effect = [self.usuario, {**self.usuario, 'nombre_completo': 'Ana Nueva'}]
		self.collection.update_one.return_value = SimpleNamespace(modified_count=1)
		self.collection.delete_one.return_value = SimpleNamespace(deleted_count=1)
		get_mongo_db.return_value = self.database

		update_response = self.client.patch(
			f'/api/usuarios/{self.usuario_id}/',
			{'nombre_completo': 'Ana Nueva'},
			format='json',
		)
		delete_response = self.client.delete(f'/api/usuarios/{self.usuario_id}/')

		self.assertEqual(update_response.status_code, 200)
		self.assertEqual(delete_response.status_code, 204)

	@patch('usuarios.views.get_mongo_db')
	def test_crear_pasajero_guarda_perfil_anidado(self, get_mongo_db):
		pasajero = {
			**self.usuario,
			'rol': 'pasajero',
			'perfil_pasajero': {
				'direccion_retorno_predeterminada': 'Av. Central 123',
				'telefono': '5551234',
			},
			'perfil_admin': None,
		}
		self.collection.find_one.side_effect = [None, pasajero]
		self.collection.insert_one.return_value = SimpleNamespace(inserted_id=self.usuario_id)
		get_mongo_db.return_value = self.database

		response = self.client.post('/api/pasajeros/', {
			'nombre_completo': 'Ana Pérez',
			'correo_electronico': 'ana@example.com',
			'contrasenia': 'clave-segura-123',
			'direccion_retorno_predeterminada': 'Av. Central 123',
			'telefono': '5551234',
		}, format='json')

		self.assertEqual(response.status_code, 201)
		documento = self.collection.insert_one.call_args.args[0]
		self.assertEqual(documento['rol'], 'pasajero')
		self.assertEqual(documento['perfil_pasajero']['telefono'], '5551234')
		self.assertIsNone(documento['perfil_admin'])

	@patch('usuarios.views.get_mongo_db')
	def test_crear_administrador_guarda_fecha_y_perfil(self, get_mongo_db):
		administrador = {
			**self.usuario,
			'rol': 'administrador',
			'perfil_pasajero': None,
			'perfil_admin': {
				'fecha_contratacion': datetime(2026, 1, 15, tzinfo=timezone.utc),
				'telefono_corporativo': '5559876',
			},
		}
		self.collection.find_one.side_effect = [None, administrador]
		self.collection.insert_one.return_value = SimpleNamespace(inserted_id=self.usuario_id)
		get_mongo_db.return_value = self.database

		response = self.client.post('/api/administradores/', {
			'nombre_completo': 'Ana Pérez',
			'correo_electronico': 'ana@example.com',
			'contrasenia': 'clave-segura-123',
			'fecha_contratacion': '2026-01-15',
			'telefono_corporativo': '5559876',
		}, format='json')

		self.assertEqual(response.status_code, 201)
		documento = self.collection.insert_one.call_args.args[0]
		self.assertEqual(documento['rol'], 'administrador')
		self.assertEqual(documento['perfil_admin']['fecha_contratacion'].date().isoformat(), '2026-01-15')
		self.assertIsNone(documento['perfil_pasajero'])

	@patch('usuarios.views.get_mongo_db')
	def test_listar_pasajeros_filtra_por_rol(self, get_mongo_db):
		self.collection.find.return_value = [self.usuario]
		get_mongo_db.return_value = self.database

		response = self.client.get('/api/pasajeros/')

		self.assertEqual(response.status_code, 200)
		self.collection.find.assert_called_once_with({'rol': 'pasajero'})

	@patch('usuarios.views.get_mongo_db')
	def test_detalle_pasajero_no_expone_administrador(self, get_mongo_db):
		self.collection.find_one.return_value = None
		get_mongo_db.return_value = self.database

		response = self.client.get(f'/api/pasajeros/{self.usuario_id}/')

		self.assertEqual(response.status_code, 404)
		self.collection.find_one.assert_called_once_with({'_id': self.usuario_id, 'rol': 'pasajero'})

	@patch('usuarios.views.get_mongo_db')
	def test_actualizar_y_eliminar_pasajero_filtra_por_rol(self, get_mongo_db):
		pasajero = {
			**self.usuario,
			'perfil_pasajero': {'telefono': '5550000'},
		}
		self.collection.find_one.side_effect = [pasajero, pasajero]
		self.collection.delete_one.return_value = SimpleNamespace(deleted_count=1)
		get_mongo_db.return_value = self.database

		update_response = self.client.patch(
			f'/api/pasajeros/{self.usuario_id}/',
			{'telefono': '5550001'},
			format='json',
		)
		delete_response = self.client.delete(f'/api/pasajeros/{self.usuario_id}/')

		self.assertEqual(update_response.status_code, 200)
		self.assertEqual(delete_response.status_code, 204)
		self.collection.update_one.assert_called_once_with(
			{'_id': self.usuario_id, 'rol': 'pasajero'},
			{'$set': {'perfil_pasajero.telefono': '5550001'}},
		)
		self.collection.delete_one.assert_called_once_with({'_id': self.usuario_id, 'rol': 'pasajero'})

	@patch('usuarios.views.get_mongo_db')
	def test_actualizar_y_eliminar_administrador_filtra_por_rol(self, get_mongo_db):
		administrador = {
			**self.usuario,
			'rol': 'administrador',
			'perfil_pasajero': None,
			'perfil_admin': {
				'fecha_contratacion': datetime(2026, 1, 15, tzinfo=timezone.utc),
				'telefono_corporativo': '5550000',
			},
		}
		self.collection.find_one.side_effect = [administrador, administrador]
		self.collection.delete_one.return_value = SimpleNamespace(deleted_count=1)
		get_mongo_db.return_value = self.database

		update_response = self.client.patch(
			f'/api/administradores/{self.usuario_id}/',
			{'telefono_corporativo': '5550001'},
			format='json',
		)
		delete_response = self.client.delete(f'/api/administradores/{self.usuario_id}/')

		self.assertEqual(update_response.status_code, 200)
		self.assertEqual(delete_response.status_code, 204)
		self.collection.update_one.assert_called_once_with(
			{'_id': self.usuario_id, 'rol': 'administrador'},
			{'$set': {'perfil_admin.telefono_corporativo': '5550001'}},
		)
		self.collection.delete_one.assert_called_once_with({'_id': self.usuario_id, 'rol': 'administrador'})
