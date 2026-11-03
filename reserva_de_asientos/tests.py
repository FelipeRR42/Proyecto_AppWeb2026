from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from bson import ObjectId
from django.test import SimpleTestCase
from pymongo.errors import PyMongoError
from rest_framework.test import APIClient
from reserva_de_asientos.services import liberar_bloqueos_vencidos

class ReservaApiTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.pasajero_id = ObjectId()
        self.viaje_id = ObjectId()
        self.reserva_id = ObjectId()
        self.pasajero = {
            '_id': self.pasajero_id,
            'nombre_completo': 'Pasajero de prueba',
            'rol': 'pasajero',
        }
        self.viaje = {
            '_id': self.viaje_id,
            'titulo': 'Viaje de prueba',
            'estado': 'programado',
            'asientos': [
                {'num_asiento': 1, 'estado': 'disponible', 'bloqueado_hasta': None},
                {'num_asiento': 2, 'estado': 'disponible', 'bloqueado_hasta': None},
            ],
        }
        self.reserva = {
            '_id': self.reserva_id,
            'fecha_reserva': datetime(2026, 11, 2, tzinfo=timezone.utc),
            'estado': 'pendiente',
            'tipo_viaje': 'ida',
            'direccion_retorno': None,
            'pasajero_titular': {'id_pasajero': self.pasajero_id},
            'viaje_reservado': {'id_viaje_reservado': self.viaje_id},
            'asientos_reservados': [{'num_asiento': 1}],
            'bloqueado_hasta': datetime(2026, 11, 2, 0, 5, tzinfo=timezone.utc),
            'pagos': [],
        }
        self.reservas = MagicMock()
        self.usuarios = MagicMock()
        self.viajes = MagicMock()
        self.db = SimpleNamespace(
            reservas=self.reservas,
            usuarios=self.usuarios,
            viajes=self.viajes,
        )
        self.list_url = '/api/reservas/'

    def _datos_reserva(self):
        return {
            'id_pasajero': str(self.pasajero_id),
            'id_viaje': str(self.viaje_id),
            'tipo_viaje': 'ida',
            'asientos': [1],
            'direccion_retorno': None,
        }

    @patch('reserva_de_asientos.views.get_mongo_db')
    def test_listar_devuelve_reservas_de_mongo_con_object_ids(self, get_mongo_db):
        self.reservas.find.return_value = [self.reserva]
        get_mongo_db.return_value = self.db

        respuesta = self.client.get(self.list_url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data[0]['id_reserva'], str(self.reserva_id))
        self.assertEqual(respuesta.data[0]['id_pasajero'], str(self.pasajero_id))
        self.assertEqual(respuesta.data[0]['id_viaje'], str(self.viaje_id))

    @patch('reserva_de_asientos.views.get_mongo_db')
    def test_crear_guarda_reserva_en_mongo(self, get_mongo_db):
        self.usuarios.find_one.return_value = self.pasajero
        self.viajes.find_one.return_value = self.viaje
        self.viajes.update_one.return_value = SimpleNamespace(modified_count=1)
        self.reservas.insert_one.return_value = SimpleNamespace(
            inserted_id=self.reserva_id,
        )
        get_mongo_db.return_value = self.db

        respuesta = self.client.post(
            self.list_url,
            self._datos_reserva(),
            format='json',
        )

        self.assertEqual(respuesta.status_code, 201)
        self.assertTrue(ObjectId.is_valid(respuesta.data['id_reserva']))
        documento = self.reservas.insert_one.call_args.args[0]
        self.assertEqual(
            documento['pasajero_titular']['id_pasajero'],
            self.pasajero_id,
        )
        self.assertEqual(
            documento['viaje_reservado']['id_viaje_reservado'],
            self.viaje_id,
        )
        self.assertEqual(documento['estado'], 'pendiente')
        self.assertEqual(documento['asientos_reservados'], [{'num_asiento': 1}])
        self.assertGreater(documento['bloqueado_hasta'], documento['fecha_reserva'])
        self.assertLessEqual(
            documento['bloqueado_hasta'] - documento['fecha_reserva'],
            timedelta(minutes=5),
        )
        self.assertEqual(respuesta.data['asientos_reservados'], [{'num_asiento': 1}])
        self.assertIsNotNone(respuesta.data['bloqueado_hasta'])
        asiento_update = self.viajes.update_one.call_args
        self.assertEqual(
            asiento_update.args[1]['$set']['asientos.$[asiento].estado'],
            'bloqueado',
        )
        self.reservas.insert_one.assert_called_once()

    @patch('reserva_de_asientos.views.get_mongo_db')
    def test_crud_consultar_actualizar_y_eliminar(self, get_mongo_db):
        self.reservas.find_one.side_effect = [
            self.reserva,
            self.reserva,
            {**self.reserva, 'direccion_retorno': 'Nueva dirección'},
            {**self.reserva, 'direccion_retorno': 'Nueva dirección'},
            {**self.reserva, 'direccion_retorno': 'Nueva dirección'},
            self.reserva,
        ]
        self.reservas.update_one.return_value = SimpleNamespace(modified_count=1)
        self.viajes.update_one.return_value = SimpleNamespace(modified_count=1)
        self.reservas.delete_one.return_value = SimpleNamespace(deleted_count=1)
        get_mongo_db.return_value = self.db

        detail_url = f'/api/reservas/{self.reserva_id}/'
        obtener = self.client.get(detail_url)
        actualizar = self.client.patch(
            detail_url,
            {'direccion_retorno': 'Nueva dirección'},
            format='json',
        )
        reemplazar = self.client.put(
            detail_url,
            {'tipo_viaje': 'ida_vuelta', 'direccion_retorno': None},
            format='json',
        )
        eliminar = self.client.delete(detail_url)

        self.assertEqual(obtener.status_code, 200)
        self.assertEqual(actualizar.status_code, 200)
        self.assertEqual(actualizar.data['direccion_retorno'], 'Nueva dirección')
        self.assertEqual(reemplazar.status_code, 200)
        self.assertEqual(eliminar.status_code, 204)
        self.reservas.delete_one.assert_called_once_with({'_id': self.reserva_id})

    @patch('reserva_de_asientos.views.get_mongo_db')
    def test_identificador_invalido_devuelve_400(self, get_mongo_db):
        respuesta = self.client.get('/api/reservas/no-es-object-id/')

        self.assertEqual(respuesta.status_code, 400)
        get_mongo_db.assert_not_called()

    @patch('reserva_de_asientos.views.get_mongo_db')
    def test_reserva_inexistente_devuelve_404(self, get_mongo_db):
        self.reservas.find_one.return_value = None
        get_mongo_db.return_value = self.db

        respuesta = self.client.get(f'/api/reservas/{self.reserva_id}/')

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(respuesta.data, {'detail': 'Reserva no encontrada.'})

    @patch('reserva_de_asientos.views.get_mongo_db')
    def test_referencia_inexistente_devuelve_404(self, get_mongo_db):
        self.usuarios.find_one.return_value = None
        get_mongo_db.return_value = self.db

        respuesta = self.client.post(
            self.list_url,
            self._datos_reserva(),
            format='json',
        )

        self.assertEqual(respuesta.status_code, 404)
        self.reservas.insert_one.assert_not_called()

    @patch('reserva_de_asientos.views.get_mongo_db')
    def test_crear_rechaza_asientos_no_disponibles(self, get_mongo_db):
        self.usuarios.find_one.return_value = self.pasajero
        self.viajes.find_one.return_value = self.viaje
        self.viajes.update_one.return_value = SimpleNamespace(modified_count=0)
        get_mongo_db.return_value = self.db

        respuesta = self.client.post(
            self.list_url,
            self._datos_reserva(),
            format='json',
        )

        self.assertEqual(respuesta.status_code, 409)
        self.reservas.insert_one.assert_not_called()

    @patch('reserva_de_asientos.views.get_mongo_db')
    def test_crear_rechaza_viajes_que_no_aceptan_reservas(self, get_mongo_db):
        self.usuarios.find_one.return_value = self.pasajero
        self.viajes.find_one.return_value = {**self.viaje, 'estado': 'cancelado'}
        get_mongo_db.return_value = self.db

        respuesta = self.client.post(
            self.list_url,
            self._datos_reserva(),
            format='json',
        )

        self.assertEqual(respuesta.status_code, 409)
        self.viajes.update_one.assert_not_called()

    @patch('reserva_de_asientos.views.get_mongo_db')
    def test_crear_rechaza_asientos_repetidos(self, get_mongo_db):
        data = self._datos_reserva()
        data['asientos'] = [1, 1]

        respuesta = self.client.post(self.list_url, data, format='json')

        self.assertEqual(respuesta.status_code, 400)
        get_mongo_db.assert_not_called()

    @patch('reserva_de_asientos.views.get_mongo_db')
    def test_cancelar_libera_asientos_y_actualiza_estado(self, get_mongo_db):
        self.reservas.find_one.side_effect = [
            self.reserva,
            {**self.reserva, 'estado': 'cancelada'},
        ]
        self.reservas.update_one.return_value = SimpleNamespace(modified_count=1)
        self.viajes.update_one.return_value = SimpleNamespace(modified_count=1)
        get_mongo_db.return_value = self.db

        respuesta = self.client.post(
            f'/api/reservas/{self.reserva_id}/cancelar/',
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data['estado'], 'cancelada')
        self.reservas.update_one.assert_called_once_with(
            {'_id': self.reserva_id, 'estado': 'pendiente'},
            {'$set': {'estado': 'cancelada'}},
        )
        self.viajes.update_one.assert_called_once()

    @patch('reserva_de_asientos.views.get_mongo_db')
    def test_crear_compensa_bloqueo_si_falla_el_insert(self, get_mongo_db):
        self.usuarios.find_one.return_value = self.pasajero
        self.viajes.find_one.return_value = self.viaje
        self.viajes.update_one.return_value = SimpleNamespace(modified_count=1)
        self.reservas.insert_one.side_effect = PyMongoError('insert fallido')
        get_mongo_db.return_value = self.db

        respuesta = self.client.post(
            self.list_url,
            self._datos_reserva(),
            format='json',
        )

        self.assertEqual(respuesta.status_code, 500)
        self.assertEqual(self.viajes.update_one.call_count, 2)
        rollback = self.viajes.update_one.call_args
        self.assertEqual(
            rollback.args[1]['$set']['asientos.$[asiento].estado'],
            'disponible',
        )

    @patch('reserva_de_asientos.views.get_mongo_db')
    def test_estado_no_se_puede_cambiar_con_patch(self, get_mongo_db):
        get_mongo_db.return_value = self.db

        respuesta = self.client.patch(
            f'/api/reservas/{self.reserva_id}/',
            {'estado': 'confirmada'},
            format='json',
        )

        self.assertEqual(respuesta.status_code, 400)
        self.reservas.update_one.assert_not_called()

    @patch('reserva_de_asientos.views.get_mongo_db', side_effect=ValueError('MongoDB no disponible'))
    def test_error_de_mongo_devuelve_500_estandar(self, _get_mongo_db):
        respuesta = self.client.get(self.list_url)

        self.assertEqual(respuesta.status_code, 500)
        self.assertEqual(
            respuesta.data,
            {'detail': 'Error interno al procesar la solicitud.'},
        )

    @patch('reserva_de_asientos.views.get_mongo_db')
    def test_error_inesperado_devuelve_500_estandar(self, get_mongo_db):
        self.reservas.find.side_effect = RuntimeError('Error inesperado')
        get_mongo_db.return_value = self.db

        respuesta = self.client.get(self.list_url)

        self.assertEqual(respuesta.status_code, 500)
        self.assertEqual(
            respuesta.data,
            {'detail': 'Error interno al procesar la solicitud.'},
        )


class LiberarBloqueosTests(SimpleTestCase):
    def test_limpia_asientos_y_reservas_vencidas(self):
        db = SimpleNamespace(viajes=MagicMock(), reservas=MagicMock())
        ahora = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)

        liberar_bloqueos_vencidos(db, ahora=ahora)

        viajes_query, viajes_update = db.viajes.update_many.call_args.args
        self.assertEqual(
            viajes_query['asientos']['$elemMatch']['bloqueado_hasta']['$lte'],
            ahora,
        )
        self.assertEqual(
            viajes_update['$set']['asientos.$[asiento].estado'],
            'disponible',
        )
        self.assertEqual(
            db.reservas.update_many.call_args.args[0]['estado'],
            'pendiente',
        )
        self.assertEqual(
            db.reservas.update_many.call_args.args[1]['$set']['estado'],
            'vencida',
        )
