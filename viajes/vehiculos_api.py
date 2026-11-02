from bson import ObjectId
from drf_spectacular.utils import OpenApiResponse, extend_schema
from pymongo.errors import DuplicateKeyError, PyMongoError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from config.mongo import get_mongo_db
from .vehiculos_serializers import VehiculoReadSerializer, VehiculoWriteSerializer


ERROR_400 = OpenApiResponse(description='Datos inválidos.')
ERROR_404 = OpenApiResponse(description='Vehículo no encontrado.')
ERROR_409 = OpenApiResponse(description='Patente duplicada o vehículo asociado a viajes.')
ERROR_500 = OpenApiResponse(description='Error interno o conexión con MongoDB no disponible.')


def _collection():
	return get_mongo_db().vehiculos


def _error_servidor():
	return Response(
		{'detail': 'Error interno al procesar la solicitud.'},
		status=status.HTTP_500_INTERNAL_SERVER_ERROR,
	)


class VehiculoListCreateView(APIView):
	@extend_schema(
		operation_id='vehiculos_listar',
		summary='Listar vehículos',
		responses={200: VehiculoReadSerializer(many=True), 500: ERROR_500},
	)
	def get(self, request):
		try:
			vehiculos = list(_collection().find().sort('patente', 1))
			return Response(VehiculoReadSerializer(vehiculos, many=True).data)
		except Exception:
			return _error_servidor()

	@extend_schema(
		operation_id='vehiculos_crear',
		summary='Crear vehículo',
		request=VehiculoWriteSerializer,
		responses={201: VehiculoReadSerializer, 400: ERROR_400, 409: ERROR_409, 500: ERROR_500},
	)
	def post(self, request):
		serializer = VehiculoWriteSerializer(data=request.data)
		if not serializer.is_valid():
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
		try:
			collection = _collection()
			values = dict(serializer.validated_data)
			if collection.find_one({'patente': values['patente']}):
				return Response(
					{'patente': ['Ya existe un vehículo con esta patente.']},
					status=status.HTTP_409_CONFLICT,
				)
			result = collection.insert_one(values)
			vehiculo = collection.find_one({'_id': result.inserted_id})
			return Response(VehiculoReadSerializer(vehiculo).data, status=status.HTTP_201_CREATED)
		except DuplicateKeyError:
			return Response(
				{'patente': ['Ya existe un vehículo con esta patente.']},
				status=status.HTTP_409_CONFLICT,
			)
		except Exception:
			return _error_servidor()


class VehiculoDetailView(APIView):
	@extend_schema(
		operation_id='vehiculos_obtener',
		summary='Obtener vehículo por patente',
		responses={200: VehiculoReadSerializer, 404: ERROR_404, 500: ERROR_500},
	)
	def get(self, request, patente):
		try:
			vehiculo = _collection().find_one({'patente': patente})
			if vehiculo is None:
				return Response({'detail': 'Vehículo no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
			return Response(VehiculoReadSerializer(vehiculo).data)
		except Exception:
			return _error_servidor()

	@extend_schema(
		operation_id='vehiculos_reemplazar',
		summary='Actualizar vehículo',
		request=VehiculoWriteSerializer,
		responses={200: VehiculoReadSerializer, 400: ERROR_400, 404: ERROR_404, 409: ERROR_409, 500: ERROR_500},
	)
	def put(self, request, patente):
		return self._actualizar(request, patente, partial=False)

	@extend_schema(
		operation_id='vehiculos_actualizar_parcial',
		summary='Actualizar parcialmente vehículo',
		request=VehiculoWriteSerializer,
		responses={200: VehiculoReadSerializer, 400: ERROR_400, 404: ERROR_404, 409: ERROR_409, 500: ERROR_500},
	)
	def patch(self, request, patente):
		return self._actualizar(request, patente, partial=True)

	def _actualizar(self, request, patente, partial):
		serializer = VehiculoWriteSerializer(data=request.data, partial=partial)
		if not serializer.is_valid():
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
		try:
			collection = _collection()
			vehiculo = collection.find_one({'patente': patente})
			if vehiculo is None:
				return Response({'detail': 'Vehículo no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
			values = dict(serializer.validated_data)
			patente_nueva = values.get('patente')
			if patente_nueva and patente_nueva != patente and collection.find_one({'patente': patente_nueva}):
				return Response(
					{'patente': ['Ya existe un vehículo con esta patente.']},
					status=status.HTTP_409_CONFLICT,
				)
			collection.update_one({'_id': vehiculo['_id']}, {'$set': values})
			actualizado = collection.find_one({'_id': vehiculo['_id']})
			return Response(VehiculoReadSerializer(actualizado).data)
		except DuplicateKeyError:
			return Response(
				{'patente': ['Ya existe un vehículo con esta patente.']},
				status=status.HTTP_409_CONFLICT,
			)
		except Exception:
			return _error_servidor()

	@extend_schema(
		operation_id='vehiculos_eliminar',
		summary='Eliminar vehículo',
		responses={204: OpenApiResponse(description='Vehículo eliminado.'), 404: ERROR_404, 409: ERROR_409, 500: ERROR_500},
	)
	def delete(self, request, patente):
		try:
			db = get_mongo_db()
			vehiculo = db.vehiculos.find_one({'patente': patente})
			if vehiculo is None:
				return Response({'detail': 'Vehículo no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
			if db.viajes.find_one({'patente_vehiculo': vehiculo['_id']}):
				return Response(
					{'detail': 'No se puede eliminar un vehículo asociado a viajes.'},
					status=status.HTTP_409_CONFLICT,
				)
			db.vehiculos.delete_one({'_id': vehiculo['_id']})
			return Response(status=status.HTTP_204_NO_CONTENT)
		except Exception:
			return _error_servidor()