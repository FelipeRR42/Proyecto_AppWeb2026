from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from .views import ReservaListCreateView
from usuarios.models import Administrador, Pasajero
from viajes.models import Vehiculo, Viaje
from .models import Reserva


class ReservaApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.pasajero = Pasajero.objects.create(
            nombre_completo='Pasajero de prueba',
            correo_electronico='pasajero@example.com',
            contrasenia='hashed-password',
            direccion_retorno_predeterminada='Calle Principal 123',
            telefono='123456789',
        )
        administrador = Administrador.objects.create(
            nombre_completo='Administrador de prueba',
            correo_electronico='admin@example.com',
            contrasenia='hashed-password',
            fecha_contratacion=timezone.localdate(),
            telefono_corporativo='987654321',
        )
        vehiculo = Vehiculo.objects.create(
            patente='TEST-123',
            modelo='Bus de prueba',
            capacidad_maxima=40,
        )
        ahora = timezone.now()
        self.viaje = Viaje.objects.create(
            id_admin=administrador,
            patente_vehiculo=vehiculo,
            origen='Santiago',
            destino='Valparaíso',
            fecha_evento=ahora,
            fecha_salida=ahora,
            fecha_retorno=ahora,
            precio_ida_y_vuelta=20000,
            precio_ida=12000,
            estado='programado',
            recinto='Recinto de prueba',
            artista='Artista de prueba',
            titulo='Viaje de prueba',
            descripcion='Descripción de prueba',
        )
        self.list_url = reverse('reservas-list-create')

    def _datos_reserva(self):
        return {
            'id_pasajero': self.pasajero.pk,
            'id_viaje': self.viaje.pk,
            'estado': 'pendiente',
            'tipo_viaje': 'ida',
            'direccion_retorno': '',
        }

    def test_crud_reserva(self):
        respuesta = self.client.get(self.list_url)
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data, [])

        respuesta = self.client.post(self.list_url, self._datos_reserva(), format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        reserva_id = respuesta.data['id_reserva']
        self.assertEqual(respuesta.data['id_pasajero'], self.pasajero.pk)
        self.assertEqual(respuesta.data['id_viaje'], self.viaje.pk)
        self.assertIn('fecha_reserva', respuesta.data)

        detail_url = reverse('reservas-detail', args=[reserva_id])
        respuesta = self.client.get(detail_url)
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

        datos_actualizados = self._datos_reserva()
        datos_actualizados['estado'] = 'confirmada'
        respuesta = self.client.put(detail_url, datos_actualizados, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data['estado'], 'confirmada')

        respuesta = self.client.patch(detail_url, {'estado': 'cancelada'}, format='json')
        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data['estado'], 'cancelada')

        respuesta = self.client.delete(detail_url)
        self.assertEqual(respuesta.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Reserva.objects.filter(pk=reserva_id).exists())
        self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_404_NOT_FOUND)

    def test_creacion_rechaza_datos_invalidos(self):
        datos = self._datos_reserva()
        datos['tipo_viaje'] = 'solo_ida'

        respuesta = self.client.post(self.list_url, datos, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_detalle_inexistente_devuelve_404(self):
        respuesta = self.client.get(reverse('reservas-detail', args=[999999]))

        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(respuesta.data, {'detail': 'Reserva no encontrada.'})

    @patch.object(ReservaListCreateView, 'get_queryset', side_effect=RuntimeError('Error inesperado'))
    def test_error_interno_devuelve_respuesta_json_estandar(self, _get_queryset):
        respuesta = self.client.get(self.list_url)

        self.assertEqual(respuesta.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(
            respuesta.data,
            {'detail': 'Error interno al procesar la solicitud.'},
        )
