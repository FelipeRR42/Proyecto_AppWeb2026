from bson import ObjectId
from drf_spectacular.utils import OpenApiResponse, extend_schema
from pymongo.errors import PyMongoError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from config.mongo import get_mongo_db
from .serializers import ViajeReadSerializer, ViajeWriteSerializer


ERROR_400 = OpenApiResponse(description='Solicitud inválida o identificador mal formado.')
ERROR_404 = OpenApiResponse(description='Viaje, administrador o vehículo no encontrado.')
ERROR_409 = OpenApiResponse(description='No se puede eliminar el viaje porque tiene reservas asociadas.')
ERROR_500 = OpenApiResponse(description='Error interno o conexión con MongoDB no disponible.')


def _viajes_collection():
	return get_mongo_db().viajes


def _error_servidor():
	return Response(
		{'detail': 'Error interno al procesar la solicitud.'},
		status=status.HTTP_500_INTERNAL_SERVER_ERROR,
	)


def _crear_documento(values, administrador, vehiculo, asientos=None):
	return {
		'titulo': values['titulo'],
		'artista': values['artista'],
		'recinto': values['recinto'],
		'descripcion': values['descripcion'],
		'origen': values['origen'],
		'destino': values['destino'],
		'fecha_evento': values['fecha_evento'],
		'fecha_salida': values['fecha_salida'],
		'fecha_retorno': values['fecha_retorno'],
		'precio_ida': values['precio_ida'],
		'precio_ida_y_vuelta': values['precio_ida_y_vuelta'],
		'estado': values['estado'],
		'administrador': {
			'id_admin': administrador['_id'],
			'nombre': administrador['nombre_completo'],
		},
		'patente_vehiculo': vehiculo['_id'],
		'asientos': asientos if asientos is not None else [
			{'num_asiento': number, 'estado': 'disponible', 'bloqueado_hasta': None}
			for number in range(1, vehiculo['capacidad_maxima'] + 1)
		],
	}


def _resolver_referencias(db, values):
	administrador_id = values.pop('administrador_id')
	if not ObjectId.is_valid(administrador_id):
		return None, None, Response(
			{'administrador_id': ['Debe ser un ObjectId válido.']},
			status=status.HTTP_400_BAD_REQUEST,
		)
	administrador = db.usuarios.find_one({
		'_id': ObjectId(administrador_id),
		'rol': 'administrador',
	})
	if administrador is None:
		return None, None, Response({'detail': 'Administrador no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

	vehiculo = db.vehiculos.find_one({'patente': values.pop('patente_vehiculo')})
	if vehiculo is None:
		return None, None, Response({'detail': 'Vehículo no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
	return administrador, vehiculo, None


class ViajeListCreateView(APIView):
	@extend_schema(
		operation_id='viajes_listar',
		summary='Listar viajes',
		responses={200: ViajeReadSerializer(many=True), 500: ERROR_500},
	)
	def get(self, request):
		try:
			query = {}
			for field in ('estado', 'origen', 'destino', 'artista'):
				value = request.query_params.get(field)
				if value:
					query[field] = value
			viajes = list(_viajes_collection().find(query).sort('fecha_salida', 1))
			return Response(ViajeReadSerializer(viajes, many=True).data)
		except Exception:
			return _error_servidor()

	@extend_schema(
		operation_id='viajes_crear',
		summary='Crear viaje',
		request=ViajeWriteSerializer,
		responses={201: ViajeReadSerializer, 400: ERROR_400, 404: ERROR_404, 500: ERROR_500},
	)
	def post(self, request):
		serializer = ViajeWriteSerializer(data=request.data)
		if not serializer.is_valid():
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
		try:
			db = get_mongo_db()
			values = dict(serializer.validated_data)
			administrador, vehiculo, error = _resolver_referencias(db, values)
			if error:
				return error
			documento = _crear_documento(values, administrador, vehiculo)
			result = db.viajes.insert_one(documento)
			viaje = db.viajes.find_one({'_id': result.inserted_id})
			return Response(ViajeReadSerializer(viaje).data, status=status.HTTP_201_CREATED)
		except (PyMongoError, ValueError, KeyError):
			return _error_servidor()
		except Exception:
			return _error_servidor()


class ViajeDetailView(APIView):
	@extend_schema(
		operation_id='viajes_obtener',
		summary='Obtener viaje',
		responses={200: ViajeReadSerializer, 400: ERROR_400, 404: ERROR_404, 500: ERROR_500},
	)
	def get(self, request, viaje_id):
		if not ObjectId.is_valid(viaje_id):
			return Response({'detail': 'Identificador inválido.'}, status=status.HTTP_400_BAD_REQUEST)
		try:
			viaje = _viajes_collection().find_one({'_id': ObjectId(viaje_id)})
			if viaje is None:
				return Response({'detail': 'Viaje no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
			return Response(ViajeReadSerializer(viaje).data)
		except Exception:
			return _error_servidor()

	@extend_schema(
		operation_id='viajes_actualizar',
		summary='Actualizar viaje',
		request=ViajeWriteSerializer,
		responses={200: ViajeReadSerializer, 400: ERROR_400, 404: ERROR_404, 500: ERROR_500},
	)
	def put(self, request, viaje_id):
		return self._actualizar(request, viaje_id, partial=False)

	@extend_schema(
		operation_id='viajes_actualizar_parcial',
		summary='Actualizar parcialmente viaje',
		request=ViajeWriteSerializer,
		responses={200: ViajeReadSerializer, 400: ERROR_400, 404: ERROR_404, 500: ERROR_500},
	)
	def patch(self, request, viaje_id):
		return self._actualizar(request, viaje_id, partial=True)

	def _actualizar(self, request, viaje_id, partial):
		if not ObjectId.is_valid(viaje_id):
			return Response({'detail': 'Identificador inválido.'}, status=status.HTTP_400_BAD_REQUEST)
		object_id = ObjectId(viaje_id)
		try:
			collection = _viajes_collection()
			viaje_actual = collection.find_one({'_id': object_id})
			if viaje_actual is None:
				return Response({'detail': 'Viaje no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
			vehiculo_actual = get_mongo_db().vehiculos.find_one({'_id': viaje_actual['patente_vehiculo']})
			if vehiculo_actual is None:
				return Response({'detail': 'Vehículo asociado no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
			payload = request.data
			if partial:
				payload = {
					'titulo': viaje_actual['titulo'],
					'artista': viaje_actual['artista'],
					'recinto': viaje_actual['recinto'],
					'descripcion': viaje_actual['descripcion'],
					'origen': viaje_actual['origen'],
					'destino': viaje_actual['destino'],
					'fecha_evento': viaje_actual['fecha_evento'],
					'fecha_salida': viaje_actual['fecha_salida'],
					'fecha_retorno': viaje_actual['fecha_retorno'],
					'precio_ida': viaje_actual['precio_ida'],
					'precio_ida_y_vuelta': viaje_actual['precio_ida_y_vuelta'],
					'estado': viaje_actual['estado'],
					'administrador_id': str(viaje_actual['administrador']['id_admin']),
					'patente_vehiculo': vehiculo_actual['patente'],
				}
				payload.update(request.data)
			serializer = ViajeWriteSerializer(data=payload)
			if not serializer.is_valid():
				return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
			values = dict(serializer.validated_data)
			administrador, vehiculo, error = _resolver_referencias(get_mongo_db(), values)
			if error:
				return error
			documento = _crear_documento(values, administrador, vehiculo, viaje_actual.get('asientos', []))
			collection.update_one({'_id': object_id}, {'$set': documento})
			viaje = collection.find_one({'_id': object_id})
			return Response(ViajeReadSerializer(viaje).data)
		except (PyMongoError, ValueError, KeyError):
			return _error_servidor()
		except Exception:
			return _error_servidor()

	@extend_schema(
		operation_id='viajes_eliminar',
		summary='Eliminar viaje',
		responses={204: OpenApiResponse(description='Viaje eliminado.'), 400: ERROR_400, 404: ERROR_404, 409: ERROR_409, 500: ERROR_500},
	)
	def delete(self, request, viaje_id):
		if not ObjectId.is_valid(viaje_id):
			return Response({'detail': 'Identificador inválido.'}, status=status.HTTP_400_BAD_REQUEST)
		try:
			db = get_mongo_db()
			object_id = ObjectId(viaje_id)
			if db.viajes.find_one({'_id': object_id}) is None:
				return Response({'detail': 'Viaje no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
			if db.reservas.find_one({'viaje_reservado.id_viaje_reservado': object_id}):
				return Response(
					{'detail': 'No se puede eliminar un viaje con reservas asociadas.'},
					status=status.HTTP_409_CONFLICT,
				)
			db.viajes.delete_one({'_id': object_id})
			return Response(status=status.HTTP_204_NO_CONTENT)
		except Exception:
			return _error_servidor()
