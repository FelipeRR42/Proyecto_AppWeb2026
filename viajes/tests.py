from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from bson import ObjectId
from django.test import SimpleTestCase
from rest_framework.test import APIClient


class ViajeApiTests(SimpleTestCase):
	def setUp(self):
		self.client = APIClient()
		self.viaje_id = ObjectId()
		self.admin_id = ObjectId()
		self.vehiculo_id = ObjectId()
		self.administrador = {
			'_id': self.admin_id,
			'nombre_completo': 'Administradora',
			'rol': 'administrador',
		}
		self.vehiculo = {
			'_id': self.vehiculo_id,
			'patente': 'ABC123',
			'capacidad_maxima': 2,
		}
		self.viaje = {
			'_id': self.viaje_id,
			'titulo': 'Concierto',
			'artista': 'Banda',
			'recinto': 'Estadio',
			'descripcion': 'Viaje al concierto',
			'origen': 'Ciudad A',
			'destino': 'Ciudad B',
			'fecha_salida': datetime(2026, 12, 10, 15, tzinfo=timezone.utc),
			'fecha_evento': datetime(2026, 12, 10, 20, tzinfo=timezone.utc),
			'fecha_retorno': datetime(2026, 12, 11, 1, tzinfo=timezone.utc),
			'precio_ida': 10000,
			'precio_ida_y_vuelta': 18000,
			'estado': 'programado',
			'administrador': {'id_admin': self.admin_id, 'nombre': 'Administradora'},
			'patente_vehiculo': self.vehiculo_id,
			'asientos': [
				{'num_asiento': 1, 'estado': 'disponible', 'bloqueado_hasta': None},
				{'num_asiento': 2, 'estado': 'disponible', 'bloqueado_hasta': None},
			],
		}
		self.database = MagicMock()
		self.collection = self.database.viajes

	def _payload(self):
		return {
			'titulo': 'Concierto',
			'artista': 'Banda',
			'recinto': 'Estadio',
			'descripcion': 'Viaje al concierto',
			'origen': 'Ciudad A',
			'destino': 'Ciudad B',
			'fecha_salida': '2026-12-10T15:00:00Z',
			'fecha_evento': '2026-12-10T20:00:00Z',
			'fecha_retorno': '2026-12-11T01:00:00Z',
			'precio_ida': 10000,
			'precio_ida_y_vuelta': 18000,
			'estado': 'programado',
			'administrador_id': str(self.admin_id),
			'patente_vehiculo': 'ABC123',
		}

	@patch('viajes.views.get_mongo_db')
	def test_listar_viajes_devuelve_200(self, get_mongo_db):
		self.collection.find.return_value.sort.return_value = [self.viaje]
		get_mongo_db.return_value = self.database

		response = self.client.get('/api/viajes/')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data[0]['id'], str(self.viaje_id))

	@patch('viajes.views.get_mongo_db')
	def test_filtros_de_busqueda_se_aplican_en_mongo(self, get_mongo_db):
		self.collection.find.return_value.sort.return_value = [self.viaje]
		get_mongo_db.return_value = self.database

		response = self.client.get(
			'/api/viajes/?proximos=true&fecha_desde=2026-12-10'
			'&origen=Ciudad%20A&artista=Banda&precio_minimo=9000'
			'&precio_maximo=12000&cupos_minimos=2&orden=precio_asc',
		)

		self.assertEqual(response.status_code, 200)
		query = self.collection.find.call_args.args[0]
		self.assertEqual(query['origen'], 'Ciudad A')
		self.assertEqual(query['artista'], 'Banda')
		self.assertEqual(query['precio_ida'], {'$gte': 9000, '$lte': 12000})
		conditions = query['$and']
		self.assertIn(
			{'estado': {'$in': ('programado', 'lleno')}},
			conditions,
		)
		event_date_filter = next(
			item['fecha_evento']
			for item in conditions
			if 'fecha_evento' in item
		)
		self.assertEqual(
			event_date_filter['$gte'],
			datetime(
				2026, 12, 10, 3, tzinfo=timezone.utc,
			),
		)
		seat_filter = next(item['$expr'] for item in conditions if '$expr' in item)
		self.assertEqual(seat_filter['$gte'][1], 2)
		self.assertEqual(
			seat_filter['$gte'][0]['$size']['$filter']['cond'],
			{'$eq': ['$$asiento.estado', 'disponible']},
		)
		self.collection.find.return_value.sort.assert_called_once_with(
			'precio_ida',
			1,
		)

	@patch('viajes.views.get_mongo_db')
	def test_filtros_invalidos_devuelven_400_sin_consultar_mongo(self, get_mongo_db):
		response = self.client.get(
			'/api/viajes/?precio_minimo=12000&precio_maximo=9000',
		)

		self.assertEqual(response.status_code, 400)
		self.assertIn('precio_maximo', response.data)
		get_mongo_db.assert_not_called()

	@patch('viajes.views.get_mongo_db')
	def test_fecha_y_orden_invalidos_devuelven_400(self, get_mongo_db):
		invalid_date = self.client.get('/api/viajes/?fecha_desde=10-12-2026')
		invalid_order = self.client.get('/api/viajes/?orden=aleatorio')

		self.assertEqual(invalid_date.status_code, 400)
		self.assertIn('fecha_desde', invalid_date.data)
		self.assertEqual(invalid_order.status_code, 400)
		self.assertIn('orden', invalid_order.data)
		get_mongo_db.assert_not_called()

	@patch('viajes.views.get_mongo_db')
	def test_listar_viajes_serializa_asientos_bloqueados_sin_id_interno(self, get_mongo_db):
		reserva_id = ObjectId()
		viaje = {
			**self.viaje,
			'asientos': [{
				'num_asiento': 1,
				'estado': 'bloqueado',
				'bloqueado_hasta': datetime(2026, 12, 10, 15, 5, tzinfo=timezone.utc),
				'reserva_id': reserva_id,
			}],
		}
		self.collection.find.return_value.sort.return_value = [viaje]
		get_mongo_db.return_value = self.database

		response = self.client.get('/api/viajes/')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(
			response.data[0]['asientos'],
			[{
				'num_asiento': 1,
				'estado': 'bloqueado',
				'bloqueado_hasta': '2026-12-10T15:05:00Z',
			}],
		)
		self.assertNotIn(str(reserva_id), response.content.decode())

	@patch('viajes.views.get_mongo_db')
	def test_crear_viaje_guarda_referencias_y_asientos(self, get_mongo_db):
		self.database.usuarios.find_one.return_value = self.administrador
		self.database.vehiculos.find_one.return_value = self.vehiculo
		self.collection.insert_one.return_value = SimpleNamespace(inserted_id=self.viaje_id)
		self.collection.find_one.return_value = self.viaje
		get_mongo_db.return_value = self.database

		response = self.client.post('/api/viajes/', self._payload(), format='json')

		self.assertEqual(response.status_code, 201)
		documento = self.collection.insert_one.call_args.args[0]
		self.assertEqual(documento['administrador']['id_admin'], self.admin_id)
		self.assertEqual(documento['patente_vehiculo'], self.vehiculo_id)
		self.assertEqual(len(documento['asientos']), 2)

	@patch('viajes.views.get_mongo_db')
	def test_crear_viaje_rechaza_admin_inexistente(self, get_mongo_db):
		self.database.usuarios.find_one.return_value = None
		get_mongo_db.return_value = self.database

		response = self.client.post('/api/viajes/', self._payload(), format='json')

		self.assertEqual(response.status_code, 404)
		self.collection.insert_one.assert_not_called()

	@patch('viajes.views.get_mongo_db')
	def test_consultar_viaje_devuelve_200_y_id_invalido_400(self, get_mongo_db):
		self.collection.find_one.return_value = self.viaje
		get_mongo_db.return_value = self.database

		response = self.client.get(f'/api/viajes/{self.viaje_id}/')
		invalid_response = self.client.get('/api/viajes/id-invalido/')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(invalid_response.status_code, 400)

	@patch('viajes.views.get_mongo_db')
	def test_patch_actualiza_sin_perder_campos_existentes(self, get_mongo_db):
		self.collection.find_one.side_effect = [self.viaje, self.viaje]
		self.database.vehiculos.find_one.side_effect = [self.vehiculo, self.vehiculo]
		self.database.usuarios.find_one.return_value = self.administrador
		get_mongo_db.return_value = self.database

		response = self.client.patch(
			f'/api/viajes/{self.viaje_id}/',
			{'titulo': 'Concierto actualizado'},
			format='json',
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(self.collection.update_one.call_args.args[1]['$set']['titulo'], 'Concierto actualizado')

	@patch('viajes.views.get_mongo_db')
	def test_eliminar_viaje_con_reservas_devuelve_409(self, get_mongo_db):
		self.collection.find_one.return_value = self.viaje
		self.database.reservas.find_one.return_value = {'_id': ObjectId()}
		get_mongo_db.return_value = self.database

		response = self.client.delete(f'/api/viajes/{self.viaje_id}/')

		self.assertEqual(response.status_code, 409)
		self.collection.delete_one.assert_not_called()

	@patch('viajes.views.get_mongo_db')
	def test_eliminar_viaje_sin_reservas_devuelve_204(self, get_mongo_db):
		self.collection.find_one.return_value = self.viaje
		self.database.reservas.find_one.return_value = None
		get_mongo_db.return_value = self.database

		response = self.client.delete(f'/api/viajes/{self.viaje_id}/')

		self.assertEqual(response.status_code, 204)
		self.collection.delete_one.assert_called_once_with({'_id': self.viaje_id})


class VehiculoApiTests(SimpleTestCase):
	def setUp(self):
		self.client = APIClient()
		self.vehiculo_id = ObjectId()
		self.vehiculo = {
			'_id': self.vehiculo_id,
			'patente': 'ABC123',
			'modelo': 'Bus urbano',
			'capacidad_maxima': 32,
		}
		self.database = MagicMock()
		self.collection = self.database.vehiculos

	@patch('viajes.vehiculos_api.get_mongo_db')
	def test_listar_vehiculos_devuelve_200(self, get_mongo_db):
		self.collection.find.return_value.sort.return_value = [self.vehiculo]
		get_mongo_db.return_value = self.database

		response = self.client.get('/api/vehiculos/')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data[0]['patente'], 'ABC123')

	@patch('viajes.vehiculos_api.get_mongo_db')
	def test_crear_vehiculo_devuelve_201(self, get_mongo_db):
		self.collection.find_one.side_effect = [None, self.vehiculo]
		self.collection.insert_one.return_value = SimpleNamespace(inserted_id=self.vehiculo_id)
		get_mongo_db.return_value = self.database

		response = self.client.post('/api/vehiculos/', {
			'patente': 'ABC123',
			'modelo': 'Bus urbano',
			'capacidad_maxima': 32,
		}, format='json')

		self.assertEqual(response.status_code, 201)
		self.assertEqual(self.collection.insert_one.call_args.args[0]['capacidad_maxima'], 32)

	@patch('viajes.vehiculos_api.get_mongo_db')
	def test_patente_duplicada_devuelve_409_y_capacidad_invalida_400(self, get_mongo_db):
		self.collection.find_one.return_value = self.vehiculo
		get_mongo_db.return_value = self.database

		duplicate_response = self.client.post('/api/vehiculos/', {
			'patente': 'ABC123',
			'modelo': 'Bus urbano',
			'capacidad_maxima': 32,
		}, format='json')
		invalid_response = self.client.post('/api/vehiculos/', {
			'patente': 'XYZ123',
			'modelo': 'Bus urbano',
			'capacidad_maxima': 0,
		}, format='json')

		self.assertEqual(duplicate_response.status_code, 409)
		self.assertEqual(invalid_response.status_code, 400)

	@patch('viajes.vehiculos_api.get_mongo_db')
	def test_consultar_actualizar_y_eliminar_vehiculo(self, get_mongo_db):
		self.collection.find_one.side_effect = [
			self.vehiculo,
			self.vehiculo,
			self.vehiculo,
			self.vehiculo,
		]
		self.collection.update_one.return_value = SimpleNamespace(modified_count=1)
		self.database.viajes.find_one.return_value = None
		self.collection.delete_one.return_value = SimpleNamespace(deleted_count=1)
		get_mongo_db.return_value = self.database

		get_response = self.client.get('/api/vehiculos/ABC123/')
		patch_response = self.client.patch(
			'/api/vehiculos/ABC123/',
			{'modelo': 'Bus actualizado'},
			format='json',
		)
		delete_response = self.client.delete('/api/vehiculos/ABC123/')

		self.assertEqual(get_response.status_code, 200)
		self.assertEqual(patch_response.status_code, 200)
		self.assertEqual(delete_response.status_code, 204)

	@patch('viajes.vehiculos_api.get_mongo_db')
	def test_no_elimina_vehiculo_asociado_a_viajes(self, get_mongo_db):
		self.collection.find_one.return_value = self.vehiculo
		self.database.viajes.find_one.return_value = {'_id': ObjectId()}
		get_mongo_db.return_value = self.database

		response = self.client.delete('/api/vehiculos/ABC123/')

		self.assertEqual(response.status_code, 409)
		self.collection.delete_one.assert_not_called()
