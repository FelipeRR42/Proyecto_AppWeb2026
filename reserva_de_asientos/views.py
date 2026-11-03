import logging
from datetime import datetime, timezone

from bson import ObjectId
from drf_spectacular.utils import OpenApiResponse, extend_schema
from pymongo.errors import PyMongoError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from config.mongo import get_mongo_db
from .serializers import (
    ReservaReadSerializer,
    ReservaUpdateSerializer,
    ReservaWriteSerializer,
)
from .services import (
    TIEMPO_BLOQUEO,
    bloquear_asientos,
    liberar_asientos_reserva,
    liberar_bloqueos_vencidos,
)


logger = logging.getLogger(__name__)
ERROR_400 = OpenApiResponse(description='Solicitud inválida o identificador mal formado.')
ERROR_404 = OpenApiResponse(description='Reserva, pasajero o viaje no encontrado.')
ERROR_409 = OpenApiResponse(
    description='Uno o más asientos ya no están disponibles para bloquear.'
)
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


def _crear_documento(values, pasajero, viaje, reserva_id, bloqueado_hasta):
    return {
        '_id': reserva_id,
        'fecha_reserva': datetime.now(timezone.utc),
        'estado': 'pendiente',
        'tipo_viaje': values['tipo_viaje'],
        'direccion_retorno': values.get('direccion_retorno'),
        'pasajero_titular': {'id_pasajero': pasajero['_id']},
        'viaje_reservado': {'id_viaje_reservado': viaje['_id']},
        'asientos_reservados': [
            {'num_asiento': numero}
            for numero in values['asientos']
        ],
        'bloqueado_hasta': bloqueado_hasta,
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
            db = get_mongo_db()
            liberar_bloqueos_vencidos(db)
            reservas = list(db.reservas.find())
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
            409: ERROR_409,
            500: ERROR_500,
        },
    )
    def post(self, request):
        serializer = ReservaWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        db = None
        reserva_id = ObjectId()
        bloqueada_hasta = datetime.now(timezone.utc) + TIEMPO_BLOQUEO
        numeros_asiento = serializer.validated_data['asientos']
        bloqueo_aplicado = False
        try:
            db = get_mongo_db()
            liberar_bloqueos_vencidos(db)
            values = dict(serializer.validated_data)
            pasajero, viaje, error = _resolver_referencias(
                db,
                values['id_pasajero'],
                values['id_viaje'],
            )
            if error is not None:
                return error
            if viaje.get('estado') != 'programado':
                return Response(
                    {'detail': 'Este viaje no está aceptando reservas.'},
                    status=status.HTTP_409_CONFLICT,
                )

            bloqueo_aplicado = bloquear_asientos(
                db.viajes,
                viaje['_id'],
                numeros_asiento,
                reserva_id,
                bloqueada_hasta,
                datetime.now(timezone.utc),
            )
            if not bloqueo_aplicado:
                return Response(
                    {'detail': 'Uno o más asientos ya no están disponibles.'},
                    status=status.HTTP_409_CONFLICT,
                )

            reserva = _crear_documento(
                values,
                pasajero,
                viaje,
                reserva_id,
                bloqueada_hasta,
            )
            db.reservas.insert_one(reserva)
            return Response(
                ReservaReadSerializer(reserva).data,
                status=status.HTTP_201_CREATED,
            )
        except PyMongoError:
            if bloqueo_aplicado:
                _compensar_bloqueo(db, serializer, numeros_asiento, reserva_id)
            logger.exception('Error al crear reserva en MongoDB.')
            return _error_servidor()
        except Exception:
            if bloqueo_aplicado:
                _compensar_bloqueo(db, serializer, numeros_asiento, reserva_id)
            logger.exception('Error inesperado al crear reserva.')
            return _error_servidor()


class ReservaDetailView(APIView):
    serializer_class = ReservaReadSerializer

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
            db = get_mongo_db()
            liberar_bloqueos_vencidos(db)
            reserva = db.reservas.find_one({'_id': object_id})
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
        request=ReservaUpdateSerializer,
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
        request=ReservaUpdateSerializer,
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
        serializer = ReservaUpdateSerializer(data=request.data, partial=partial)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            db = get_mongo_db()
            collection = db.reservas
            reserva = collection.find_one({'_id': object_id})
            if reserva is None:
                return _reserva_no_encontrada()

            updates = dict(serializer.validated_data)
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
            409: OpenApiResponse(description='La reserva cambió mientras se eliminaba.'),
            500: ERROR_500,
        },
    )
    def delete(self, request, reserva_id):
        object_id, error = self._object_id(reserva_id)
        if error is not None:
            return error
        try:
            db = get_mongo_db()
            reserva = db.reservas.find_one({'_id': object_id})
            if reserva is None:
                return _reserva_no_encontrada()
            if reserva.get('estado') == 'pendiente':
                if not _liberar_reserva_pendiente(db, reserva, 'cancelada'):
                    return Response(
                        {'detail': 'La reserva cambió mientras se procesaba.'},
                        status=status.HTTP_409_CONFLICT,
                    )
            result = db.reservas.delete_one({'_id': object_id})
            if result.deleted_count == 0:
                return _reserva_no_encontrada()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PyMongoError:
            logger.exception('Error al eliminar reserva de MongoDB.')
            return _error_servidor()
        except Exception:
            logger.exception('Error inesperado al eliminar reserva.')
            return _error_servidor()

class ReservaCancelView(APIView):
    serializer_class = ReservaReadSerializer

    @extend_schema(
        operation_id='reservas_cancelar',
        summary='Cancelar reserva pendiente',
        responses={
            200: ReservaReadSerializer,
            400: ERROR_400,
            404: OpenApiResponse(description='Reserva no encontrada.'),
            409: OpenApiResponse(description='La reserva ya no está pendiente.'),
            500: ERROR_500,
        },
    )
    def post(self, request, reserva_id):
        object_id, error = ReservaDetailView._object_id(reserva_id)
        if error is not None:
            return error
        try:
            db = get_mongo_db()
            liberar_bloqueos_vencidos(db)
            reserva = db.reservas.find_one({'_id': object_id})
            if reserva is None:
                return _reserva_no_encontrada()
            if reserva.get('estado') != 'pendiente':
                return Response(
                    {'detail': 'Solo se pueden cancelar reservas pendientes.'},
                    status=status.HTTP_409_CONFLICT,
                )
            if not _liberar_reserva_pendiente(db, reserva, 'cancelada'):
                return Response(
                    {'detail': 'La reserva cambió mientras se procesaba.'},
                    status=status.HTTP_409_CONFLICT,
                )
            cancelada = db.reservas.find_one({'_id': object_id})
            if cancelada is None:
                return _reserva_no_encontrada()
            return Response(ReservaReadSerializer(cancelada).data)
        except PyMongoError:
            logger.exception('Error al cancelar reserva en MongoDB.')
            return _error_servidor()
        except Exception:
            logger.exception('Error inesperado al cancelar reserva.')
            return _error_servidor()


def _liberar_reserva_pendiente(db, reserva, nuevo_estado):
    result = db.reservas.update_one(
        {'_id': reserva['_id'], 'estado': 'pendiente'},
        {'$set': {'estado': nuevo_estado}},
    )
    if result.modified_count == 0:
        return False

    viaje_id = reserva.get('viaje_reservado', {}).get('id_viaje_reservado')
    numeros = [
        asiento['num_asiento']
        for asiento in reserva.get('asientos_reservados', [])
        if 'num_asiento' in asiento
    ]
    if viaje_id is not None and numeros:
        liberar_asientos_reserva(
            db.viajes,
            viaje_id,
            numeros,
            reserva['_id'],
        )
    return True


def _compensar_bloqueo(db, serializer, numeros_asiento, reserva_id):
    try:
        liberar_asientos_reserva(
            db.viajes,
            serializer.validated_data['id_viaje'],
            numeros_asiento,
            reserva_id,
        )
    except PyMongoError:
        logger.exception('No se pudo liberar un bloqueo tras fallar la reserva.')
