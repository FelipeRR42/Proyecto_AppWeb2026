import logging
from datetime import datetime, timezone
from uuid import uuid4

from bson import ObjectId
from drf_spectacular.utils import OpenApiResponse, extend_schema
from pymongo.errors import PyMongoError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from config.mongo import get_mongo_db
from usuarios.models import Usuario
from usuarios.permissions import (
    IsAppAdministrator,
    IsPassengerOrAdministrator,
    is_app_administrator,
)
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
ERROR_404 = OpenApiResponse(description='Reserva o viaje no encontrado.')
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


def _resolver_referencias(db, id_viaje):
    viaje = db.viajes.find_one({'_id': id_viaje})
    if viaje is None:
        return None, Response(
            {'detail': 'Viaje no encontrado.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    return viaje, None


def _crear_documento(
    values,
    pasajero_id,
    nombre_pasajero,
    viaje,
    reserva_id,
    bloqueado_hasta,
):
    pago_id = f'SIM-{uuid4().hex}'
    monto = (
        viaje.get('precio_ida_y_vuelta')
        if values['tipo_viaje'] == 'ida_vuelta'
        else viaje.get('precio_ida')
    )
    return {
        '_id': reserva_id,
        'fecha_reserva': datetime.now(timezone.utc),
        'estado': 'pendiente',
        'tipo_viaje': values['tipo_viaje'],
        'direccion_retorno': values.get('direccion_retorno'),
        'pasajero_titular': {
            'id_pasajero': str(pasajero_id),
            'nombre_completo': nombre_pasajero,
        },
        'viaje_reservado': {'id_viaje_reservado': viaje['_id']},
        'asientos_reservados': [
            {'num_asiento': numero}
            for numero in values['asientos']
        ],
        'bloqueado_hasta': bloqueado_hasta,
        'pagos': [{
            'id_transaccion': pago_id,
            'monto': monto,
            'metodo_pago': 'simulado',
            'estado': 'pendiente',
            'fecha_creacion': datetime.now(timezone.utc),
        }],
    }


class ReservaListCreateView(APIView):
    permission_classes = [IsPassengerOrAdministrator]

    @extend_schema(
        operation_id='reservas_listar',
        summary='Listar reservas',
        responses={200: ReservaReadSerializer(many=True), 500: ERROR_500},
    )
    def get(self, request):
        try:
            db = get_mongo_db()
            liberar_bloqueos_vencidos(db)
            query = {}
            if not is_app_administrator(request.user):
                query = {
                    'pasajero_titular.id_pasajero': str(request.user.pk),
                }
            reservas = list(db.reservas.find(query))
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
        try:
            profile = request.user.perfil
        except Usuario.DoesNotExist:
            return Response(
                {'detail': 'Se requiere un perfil de pasajero para reservar.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if profile.rol != Usuario.Rol.PASAJERO:
            return Response(
                {'detail': 'Solo las cuentas de pasajero pueden crear reservas.'},
                status=status.HTTP_403_FORBIDDEN,
            )

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
            viaje, error = _resolver_referencias(
                db,
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
                request.user.pk,
                profile.nombre_completo,
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
    permission_classes = [IsPassengerOrAdministrator]

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
            if reserva is None or not self._puede_acceder(request.user, reserva):
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
            if reserva is None or not self._puede_acceder(request.user, reserva):
                return _reserva_no_encontrada()
            if reserva.get('estado') != 'pendiente':
                return Response(
                    {'detail': 'Solo se pueden modificar reservas pendientes.'},
                    status=status.HTTP_409_CONFLICT,
                )

            updates = dict(serializer.validated_data)
            nuevos_asientos = updates.pop('asientos', None)
            if nuevos_asientos is not None:
                viaje_id = reserva.get('viaje_reservado', {}).get('id_viaje_reservado')
                viejos_asientos = [
                    asiento['num_asiento']
                    for asiento in reserva.get('asientos_reservados', [])
                    if 'num_asiento' in asiento
                ]
                viejos_asientos = sorted(set(viejos_asientos))
                nuevos_asientos = sorted(set(nuevos_asientos))
                if viejos_asientos != nuevos_asientos:
                    if viaje_id is None:
                        return _reserva_no_encontrada()

                    liberar_asientos_reserva(
                        db.viajes,
                        viaje_id,
                        viejos_asientos,
                        object_id,
                    )
                    bloqueada_hasta = reserva.get('bloqueado_hasta')
                    bloqueado = bloquear_asientos(
                        db.viajes,
                        viaje_id,
                        nuevos_asientos,
                        object_id,
                        bloqueada_hasta,
                        datetime.now(timezone.utc),
                    )
                    if not bloqueado:
                        bloquear_asientos(
                            db.viajes,
                            viaje_id,
                            viejos_asientos,
                            object_id,
                            bloqueada_hasta,
                            datetime.now(timezone.utc),
                        )
                        return Response(
                            {'detail': 'Uno o más asientos ya no están disponibles.'},
                            status=status.HTTP_409_CONFLICT,
                        )
                    updates['asientos_reservados'] = [
                        {'num_asiento': numero}
                        for numero in nuevos_asientos
                    ]
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
        summary='Cancelar reserva conservando el historial',
        responses={
            204: OpenApiResponse(description='Reserva cancelada; el documento histórico se conserva.'),
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
            liberar_bloqueos_vencidos(db)
            reserva = db.reservas.find_one({'_id': object_id})
            if reserva is None or not self._puede_acceder(request.user, reserva):
                return _reserva_no_encontrada()
            if reserva.get('estado') not in ('pendiente', 'confirmada'):
                return Response(
                    {'detail': 'Solo se pueden cancelar reservas pendientes o confirmadas.'},
                    status=status.HTTP_409_CONFLICT,
                )
            if not _cancelar_reserva(db, reserva):
                return Response(
                    {'detail': 'La reserva cambió mientras se procesaba.'},
                    status=status.HTTP_409_CONFLICT,
                )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PyMongoError:
            logger.exception('Error al eliminar reserva de MongoDB.')
            return _error_servidor()
        except Exception:
            logger.exception('Error inesperado al eliminar reserva.')
            return _error_servidor()

    @staticmethod
    def _puede_acceder(user, reserva):
        if is_app_administrator(user):
            return True
        titular = reserva.get('pasajero_titular') or {}
        return str(titular.get('id_pasajero', '')) == str(user.pk)

class ReservaCancelView(APIView):
    serializer_class = ReservaReadSerializer
    permission_classes = [IsPassengerOrAdministrator]

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
            if reserva is None or not ReservaDetailView._puede_acceder(request.user, reserva):
                return _reserva_no_encontrada()
            if reserva.get('estado') not in ('pendiente', 'confirmada'):
                return Response(
                    {'detail': 'Solo se pueden cancelar reservas pendientes o confirmadas.'},
                    status=status.HTTP_409_CONFLICT,
                )
            if not _cancelar_reserva(db, reserva):
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


def _cancelar_reserva(db, reserva):
    estado_actual = reserva.get('estado')
    nuevo_estado = 'reembolsada' if estado_actual == 'confirmada' else 'cancelada'
    result = db.reservas.update_one(
        {'_id': reserva['_id'], 'estado': estado_actual},
        {
            '$set': {
                'estado': nuevo_estado,
                'pagos': [
                    {
                        **pago,
                        'estado': 'reembolsado',
                        'fecha_reembolso': datetime.now(timezone.utc),
                    }
                    if estado_actual == 'confirmada' and pago.get('estado') == 'confirmado'
                    else pago
                    for pago in (reserva.get('pagos') or [])
                ],
            }
        },
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


class _ReservaPagoView(APIView):
    permission_classes = [IsAppAdministrator]
    nuevo_estado_pago = None
    nuevo_estado_reserva = None

    def post(self, request, reserva_id):
        object_id, error = ReservaDetailView._object_id(reserva_id)
        if error is not None:
            return error

        try:
            db = get_mongo_db()
            liberar_bloqueos_vencidos(db)
            reserva = db.reservas.find_one({'_id': object_id})
            if reserva is None or not ReservaDetailView._puede_acceder(request.user, reserva):
                return _reserva_no_encontrada()
            if reserva.get('estado') != 'pendiente':
                return Response(
                    {'detail': 'La reserva venció o ya fue procesada.'},
                    status=status.HTTP_409_CONFLICT,
                )

            pagos = reserva.get('pagos') or []
            if not pagos:
                return Response(
                    {'detail': 'La reserva no tiene un pago asociado.'},
                    status=status.HTTP_409_CONFLICT,
                )

            pago = pagos[-1]
            estado_actual = pago.get('estado')
            if estado_actual != 'pendiente':
                return Response(
                    {'detail': 'El pago ya fue procesado.'},
                    status=status.HTTP_409_CONFLICT,
                )

            ahora = datetime.now(timezone.utc)
            pago['estado'] = self.nuevo_estado_pago
            pago['fecha_actualizacion'] = ahora
            if self.nuevo_estado_pago == 'confirmado':
                pago['fecha_pago'] = ahora

            reserva_actualizada = db.reservas.update_one(
                {'_id': object_id, 'estado': 'pendiente'},
                {
                    '$set': {
                        'estado': self.nuevo_estado_reserva,
                        'pagos': pagos,
                    },
                },
            )
            if getattr(reserva_actualizada, 'modified_count', 1) == 0:
                return Response(
                    {'detail': 'La reserva cambió mientras se procesaba el pago.'},
                    status=status.HTTP_409_CONFLICT,
                )
            reserva['estado'] = self.nuevo_estado_reserva
            reserva['pagos'] = pagos

            viaje_id = reserva.get('viaje_reservado', {}).get('id_viaje_reservado')
            numeros = [
                asiento['num_asiento']
                for asiento in reserva.get('asientos_reservados', [])
                if 'num_asiento' in asiento
            ]
            if self.nuevo_estado_pago == 'confirmado':
                db.viajes.update_one(
                    {'_id': viaje_id},
                    {
                        '$set': {
                            'asientos.$[asiento].estado': 'reservado',
                            'asientos.$[asiento].bloqueado_hasta': None,
                        },
                    },
                    array_filters=[
                        {
                            'asiento.num_asiento': {'$in': numeros},
                            'asiento.reserva_id': object_id,
                        }
                    ],
                )
            else:
                liberar_asientos_reserva(db.viajes, viaje_id, numeros, object_id)

            return Response(ReservaReadSerializer(reserva).data)
        except PyMongoError:
            logger.exception('Error al actualizar el pago de la reserva.')
            return _error_servidor()
        except Exception:
            logger.exception('Error inesperado al actualizar el pago.')
            return _error_servidor()


class ReservaPagoConfirmarView(_ReservaPagoView):
    nuevo_estado_pago = 'confirmado'
    nuevo_estado_reserva = 'confirmada'


class ReservaPagoRechazarView(_ReservaPagoView):
    nuevo_estado_pago = 'rechazado'
    nuevo_estado_reserva = 'rechazada'


class ReservaPagoReembolsarView(_ReservaPagoView):
    permission_classes = [IsAppAdministrator]
    def post(self, request, reserva_id):
        object_id, error = ReservaDetailView._object_id(reserva_id)
        if error is not None:
            return error

        try:
            db = get_mongo_db()
            reserva = db.reservas.find_one({'_id': object_id})
            if reserva is None or not ReservaDetailView._puede_acceder(request.user, reserva):
                return _reserva_no_encontrada()

            pagos = reserva.get('pagos') or []
            if not pagos or pagos[-1].get('estado') != 'confirmado':
                return Response(
                    {'detail': 'Solo se puede reembolsar un pago confirmado.'},
                    status=status.HTTP_409_CONFLICT,
                )

            pagos[-1]['estado'] = 'reembolsado'
            pagos[-1]['fecha_reembolso'] = datetime.now(timezone.utc)
            db.reservas.update_one(
                {'_id': object_id, 'estado': {'$in': ['confirmada', 'cancelada']}},
                {'$set': {'estado': 'reembolsada', 'pagos': pagos}},
            )
            reserva['estado'] = 'reembolsada'
            reserva['pagos'] = pagos

            viaje_id = reserva.get('viaje_reservado', {}).get('id_viaje_reservado')
            numeros = [
                asiento['num_asiento']
                for asiento in reserva.get('asientos_reservados', [])
                if 'num_asiento' in asiento
            ]
            liberar_asientos_reserva(db.viajes, viaje_id, numeros, object_id)
            return Response(ReservaReadSerializer(reserva).data)
        except PyMongoError:
            logger.exception('Error al registrar el reembolso.')
            return _error_servidor()
        except Exception:
            logger.exception('Error inesperado al registrar el reembolso.')
            return _error_servidor()
