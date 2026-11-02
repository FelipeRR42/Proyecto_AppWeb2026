from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from bson import ObjectId
from django.test import SimpleTestCase
from rest_framework.test import APIClient

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
        self.viaje = {'_id': self.viaje_id, 'titulo': 'Viaje de prueba'}
        self.reserva = {
            '_id': self.reserva_id,
            'fecha_reserva': datetime(2026, 11, 2, tzinfo=timezone.utc),
            'estado': 'pendiente',
            'tipo_viaje': 'ida',
            'direccion_retorno': None,
            'pasajero_titular': {'id_pasajero': self.pasajero_id},
            'viaje_reservado': {'id_viaje_reservado': self.viaje_id},
            'asientos_reservados': [],
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
            'estado': 'pendiente',
            'tipo_viaje': 'ida',
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
        self.assertEqual(respuesta.data['id_reserva'], str(self.reserva_id))
        documento = self.reservas.insert_one.call_args.args[0]
        self.assertEqual(
            documento['pasajero_titular']['id_pasajero'],
            self.pasajero_id,
        )
        self.assertEqual(
            documento['viaje_reservado']['id_viaje_reservado'],
            self.viaje_id,
        )
        self.reservas.insert_one.assert_called_once()

    @patch('reserva_de_asientos.views.get_mongo_db')
    def test_crud_consultar_actualizar_y_eliminar(self, get_mongo_db):
        self.usuarios.find_one.return_value = self.pasajero
        self.viajes.find_one.return_value = self.viaje
        self.reservas.find_one.side_effect = [
            self.reserva,
            self.reserva,
            {**self.reserva, 'estado': 'confirmada'},
            self.reserva,
            {**self.reserva, 'estado': 'cancelada'},
        ]
        self.reservas.delete_one.return_value = SimpleNamespace(deleted_count=1)
        get_mongo_db.return_value = self.db

        detail_url = f'/api/reservas/{self.reserva_id}/'
        obtener = self.client.get(detail_url)
        actualizar = self.client.patch(
            detail_url,
            {'estado': 'confirmada'},
            format='json',
        )
        reemplazar = self.client.put(
            detail_url,
            {**self._datos_reserva(), 'estado': 'cancelada'},
            format='json',
        )
        eliminar = self.client.delete(detail_url)

        self.assertEqual(obtener.status_code, 200)
        self.assertEqual(actualizar.status_code, 200)
        self.assertEqual(actualizar.data['estado'], 'confirmada')
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
