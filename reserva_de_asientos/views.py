import logging
from datetime import datetime, timezone

from bson import ObjectId
from drf_spectacular.utils import OpenApiResponse, extend_schema
from pymongo.errors import PyMongoError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from config.mongo import get_mongo_db
from .serializers import ReservaReadSerializer, ReservaWriteSerializer


logger = logging.getLogger(__name__)
ERROR_400 = OpenApiResponse(description='Solicitud inválida o identificador mal formado.')
ERROR_404 = OpenApiResponse(description='Reserva, pasajero o viaje no encontrado.')
ERROR_500 = OpenApiResponse(
    description='Error interno o conexión con MongoDB no disponible.'
)


def _error_servidor():
    return Response(
        {'detail': 'Error interno al procesar la solicitud.'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _reserva_no_encontrada():
    return Response(
        {'detail': 'Reserva no encontrada.'},
        status=status.HTTP_404_NOT_FOUND,
    )


def _resolver_referencias(db, id_pasajero, id_viaje):
    pasajero = db.usuarios.find_one({
        '_id': id_pasajero,
        'rol': 'pasajero',
    })
    if pasajero is None:
        return None, None, Response(
            {'detail': 'Pasajero no encontrado.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    viaje = db.viajes.find_one({'_id': id_viaje})
    if viaje is None:
        return None, None, Response(
            {'detail': 'Viaje no encontrado.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    return pasajero, viaje, None


def _crear_documento(values, pasajero, viaje):
    return {
        'fecha_reserva': datetime.now(timezone.utc),
        'estado': values['estado'],
        'tipo_viaje': values['tipo_viaje'],
        'direccion_retorno': values.get('direccion_retorno'),
        'pasajero_titular': {'id_pasajero': pasajero['_id']},
        'viaje_reservado': {'id_viaje_reservado': viaje['_id']},
        'asientos_reservados': [],
        'pagos': [],
    }


class ReservaListCreateView(APIView):
    @extend_schema(
        operation_id='reservas_listar',
        summary='Listar reservas',
        responses={200: ReservaReadSerializer(many=True), 500: ERROR_500},
    )
    def get(self, request):
        try:
            reservas = list(get_mongo_db().reservas.find())
            return Response(ReservaReadSerializer(reservas, many=True).data)
        except PyMongoError:
            logger.exception('Error al listar reservas en MongoDB.')
            return _error_servidor()
        except Exception:
            logger.exception('Error inesperado al listar reservas.')
            return _error_servidor()

    @extend_schema(
        operation_id='reservas_crear',
        summary='Crear reserva',
        request=ReservaWriteSerializer,
        responses={
            201: ReservaReadSerializer,
            400: ERROR_400,
            404: ERROR_404,
            500: ERROR_500,
        },
    )
    def post(self, request):
        serializer = ReservaWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            db = get_mongo_db()
            values = dict(serializer.validated_data)
            pasajero, viaje, error = _resolver_referencias(
                db,
                values['id_pasajero'],
                values['id_viaje'],
            )
            if error is not None:
                return error

            reserva = _crear_documento(values, pasajero, viaje)
            result = db.reservas.insert_one(reserva)
            reserva['_id'] = result.inserted_id
            return Response(
                ReservaReadSerializer(reserva).data,
                status=status.HTTP_201_CREATED,
            )
        except PyMongoError:
            logger.exception('Error al crear reserva en MongoDB.')
            return _error_servidor()
        except Exception:
            logger.exception('Error inesperado al crear reserva.')
            return _error_servidor()


class ReservaDetailView(APIView):
    @staticmethod
    def _object_id(reserva_id):
        if not ObjectId.is_valid(reserva_id):
            return None, Response(
                {'detail': 'Identificador inválido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return ObjectId(reserva_id), None

    @extend_schema(
        operation_id='reservas_obtener',
        summary='Obtener reserva',
        responses={
            200: ReservaReadSerializer,
            400: ERROR_400,
            404: OpenApiResponse(description='Reserva no encontrada.'),
            500: ERROR_500,
        },
    )
    def get(self, request, reserva_id):
        object_id, error = self._object_id(reserva_id)
        if error is not None:
            return error
        try:
            reserva = get_mongo_db().reservas.find_one({'_id': object_id})
            if reserva is None:
                return _reserva_no_encontrada()
            return Response(ReservaReadSerializer(reserva).data)
        except PyMongoError:
            logger.exception('Error al obtener reserva de MongoDB.')
            return _error_servidor()
        except Exception:
            logger.exception('Error inesperado al obtener reserva.')
            return _error_servidor()

    @extend_schema(
        operation_id='reservas_reemplazar',
        summary='Reemplazar reserva',
        request=ReservaWriteSerializer,
        responses={
            200: ReservaReadSerializer,
            400: ERROR_400,
            404: ERROR_404,
            500: ERROR_500,
        },
    )
    def put(self, request, reserva_id):
        return self._actualizar(request, reserva_id, partial=False)

    @extend_schema(
        operation_id='reservas_actualizar_parcial',
        summary='Actualizar parcialmente reserva',
        request=ReservaWriteSerializer,
        responses={
            200: ReservaReadSerializer,
            400: ERROR_400,
            404: ERROR_404,
            500: ERROR_500,
        },
    )
    def patch(self, request, reserva_id):
        return self._actualizar(request, reserva_id, partial=True)

    def _actualizar(self, request, reserva_id, partial):
        object_id, error = self._object_id(reserva_id)
        if error is not None:
            return error
        serializer = ReservaWriteSerializer(data=request.data, partial=partial)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            db = get_mongo_db()
            collection = db.reservas
            reserva = collection.find_one({'_id': object_id})
            if reserva is None:
                return _reserva_no_encontrada()

            values = dict(serializer.validated_data)
            pasajero_id = values.get(
                'id_pasajero',
                reserva.get('pasajero_titular', {}).get('id_pasajero'),
            )
            viaje_id = values.get(
                'id_viaje',
                reserva.get('viaje_reservado', {}).get('id_viaje_reservado'),
            )
            if pasajero_id is None or viaje_id is None:
                return Response(
                    {'detail': 'La reserva no tiene pasajero o viaje asociado.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            pasajero, viaje, error = _resolver_referencias(db, pasajero_id, viaje_id)
            if error is not None:
                return error

            updates = {
                field: values[field]
                for field in ('estado', 'tipo_viaje', 'direccion_retorno')
                if field in values
            }
            if 'id_pasajero' in values:
                updates['pasajero_titular'] = {'id_pasajero': pasajero['_id']}
            if 'id_viaje' in values:
                updates['viaje_reservado'] = {'id_viaje_reservado': viaje['_id']}
            if updates:
                collection.update_one({'_id': object_id}, {'$set': updates})
                reserva = collection.find_one({'_id': object_id})
                if reserva is None:
                    return _reserva_no_encontrada()
            return Response(ReservaReadSerializer(reserva).data)
        except PyMongoError:
            logger.exception('Error al actualizar reserva en MongoDB.')
            return _error_servidor()
        except Exception:
            logger.exception('Error inesperado al actualizar reserva.')
            return _error_servidor()

    @extend_schema(
        operation_id='reservas_eliminar',
        summary='Eliminar reserva',
        responses={
            204: OpenApiResponse(description='Reserva eliminada.'),
            400: ERROR_400,
            404: OpenApiResponse(description='Reserva no encontrada.'),
            500: ERROR_500,
        },
    )
    def delete(self, request, reserva_id):
        object_id, error = self._object_id(reserva_id)
        if error is not None:
            return error
        try:
            result = get_mongo_db().reservas.delete_one({'_id': object_id})
            if result.deleted_count == 0:
                return _reserva_no_encontrada()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PyMongoError:
            logger.exception('Error al eliminar reserva de MongoDB.')
            return _error_servidor()
        except Exception:
            logger.exception('Error inesperado al eliminar reserva.')
            return _error_servidor()
