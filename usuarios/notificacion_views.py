import logging
from datetime import datetime, timezone

from bson import ObjectId
from drf_spectacular.utils import OpenApiResponse, extend_schema
from pymongo.errors import PyMongoError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from config.mongo import get_mongo_db
from .notificacion_serializers import (
    NotificacionReadSerializer,
    NotificacionWriteSerializer,
)


logger = logging.getLogger(__name__)
ERROR_400 = OpenApiResponse(description='Solicitud inválida o referencia inexistente.')
ERROR_404 = OpenApiResponse(description='Notificación no encontrada.')
ERROR_500 = OpenApiResponse(
    description='Error interno o conexión con MongoDB no disponible.'
)


def _error_servidor():
    return Response(
        {'detail': 'Error interno al procesar la solicitud.'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _error_no_encontrada():
    return Response(
        {'detail': 'Notificación no encontrada.'},
        status=status.HTTP_404_NOT_FOUND,
    )


def _validar_referencias(db, values):
    administrador = None
    if 'id_admin' in values:
        administrador = db.usuarios.find_one({
            '_id': values['id_admin'],
            'rol': 'administrador',
        })
        if administrador is None:
            return None, Response(
                {'id_admin': ['Administrador no encontrado.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

    destinatarios = values.get('destinatarios')
    if destinatarios is not None and destinatarios:
        pasajero_ids = [item['id_pasajero'] for item in destinatarios]
        pasajeros = db.usuarios.find({
            '_id': {'$in': pasajero_ids},
            'rol': 'pasajero',
        })
        encontrados = {pasajero['_id'] for pasajero in pasajeros}
        if any(pasajero_id not in encontrados for pasajero_id in pasajero_ids):
            return None, Response(
                {'destinatarios': ['Uno o más pasajeros no existen.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

    return administrador, None


def _destinatarios_publicos(destinatarios):
    return [
        {
            'id_pasajero': item['id_pasajero'],
            'leido': item['leido'],
        }
        for item in destinatarios
    ]


class NotificacionListCreateView(APIView):
    @extend_schema(
        operation_id='notificaciones_listar',
        summary='Listar notificaciones',
        responses={200: NotificacionReadSerializer(many=True), 500: ERROR_500},
    )
    def get(self, request):
        try:
            notificaciones = list(get_mongo_db().notificaciones.find())
            return Response(NotificacionReadSerializer(notificaciones, many=True).data)
        except (PyMongoError, ValueError):
            logger.exception('Error al listar notificaciones.')
            return _error_servidor()
        except Exception:
            logger.exception('Error inesperado al listar notificaciones.')
            return _error_servidor()

    @extend_schema(
        operation_id='notificaciones_crear',
        summary='Crear notificación',
        request=NotificacionWriteSerializer,
        responses={
            201: NotificacionReadSerializer,
            400: ERROR_400,
            500: ERROR_500,
        },
    )
    def post(self, request):
        serializer = NotificacionWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            db = get_mongo_db()
            values = dict(serializer.validated_data)
            administrador, error = _validar_referencias(db, values)
            if error is not None:
                return error

            destinatarios = values.pop('destinatarios', [])
            notificacion = {
                'titulo': values['titulo'],
                'cuerpo': values['cuerpo'],
                'fecha_creacion': datetime.now(timezone.utc),
                'administrador': {
                    'id_admin': administrador['_id'],
                    'nombre': administrador['nombre_completo'],
                },
                'destinatarios': destinatarios,
            }
            result = db.notificaciones.insert_one(notificacion)
            notificacion['_id'] = result.inserted_id
            return Response(
                NotificacionReadSerializer(notificacion).data,
                status=status.HTTP_201_CREATED,
            )
        except (PyMongoError, ValueError, KeyError):
            logger.exception('Error al crear notificación.')
            return _error_servidor()
        except Exception:
            logger.exception('Error inesperado al crear notificación.')
            return _error_servidor()


class NotificacionDetailView(APIView):
    def _notificacion_id(self, notificacion_id):
        if not ObjectId.is_valid(notificacion_id):
            return None, Response(
                {'detail': 'Identificador inválido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return ObjectId(notificacion_id), None

    @extend_schema(
        operation_id='notificaciones_obtener',
        summary='Obtener notificación',
        responses={
            200: NotificacionReadSerializer,
            400: OpenApiResponse(description='Identificador mal formado.'),
            404: ERROR_404,
            500: ERROR_500,
        },
    )
    def get(self, request, notificacion_id):
        object_id, error = self._notificacion_id(notificacion_id)
        if error is not None:
            return error
        try:
            notificacion = get_mongo_db().notificaciones.find_one({'_id': object_id})
            if notificacion is None:
                return _error_no_encontrada()
            return Response(NotificacionReadSerializer(notificacion).data)
        except (PyMongoError, ValueError):
            logger.exception('Error al obtener notificación.')
            return _error_servidor()
        except Exception:
            logger.exception('Error inesperado al obtener notificación.')
            return _error_servidor()

    @extend_schema(
        operation_id='notificaciones_reemplazar',
        summary='Reemplazar notificación',
        request=NotificacionWriteSerializer,
        responses={
            200: NotificacionReadSerializer,
            400: ERROR_400,
            404: ERROR_404,
            500: ERROR_500,
        },
    )
    def put(self, request, notificacion_id):
        return self._actualizar(request, notificacion_id, partial=False)

    @extend_schema(
        operation_id='notificaciones_actualizar_parcial',
        summary='Actualizar parcialmente notificación',
        request=NotificacionWriteSerializer,
        responses={
            200: NotificacionReadSerializer,
            400: ERROR_400,
            404: ERROR_404,
            500: ERROR_500,
        },
    )
    def patch(self, request, notificacion_id):
        return self._actualizar(request, notificacion_id, partial=True)

    def _actualizar(self, request, notificacion_id, partial):
        object_id, error = self._notificacion_id(notificacion_id)
        if error is not None:
            return error
        serializer = NotificacionWriteSerializer(data=request.data, partial=partial)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            db = get_mongo_db()
            collection = db.notificaciones
            notificacion = collection.find_one({'_id': object_id})
            if notificacion is None:
                return _error_no_encontrada()

            values = dict(serializer.validated_data)
            administrador, error = _validar_referencias(db, values)
            if error is not None:
                return error

            updates = {}
            for field in ('titulo', 'cuerpo', 'destinatarios'):
                if field in values:
                    updates[field] = values[field]
            if administrador is not None:
                updates['administrador'] = {
                    'id_admin': administrador['_id'],
                    'nombre': administrador['nombre_completo'],
                }
            if not partial and 'destinatarios' not in updates:
                updates['destinatarios'] = []

            collection.update_one({'_id': object_id}, {'$set': updates})
            actualizado = collection.find_one({'_id': object_id})
            return Response(NotificacionReadSerializer(actualizado).data)
        except (PyMongoError, ValueError, KeyError):
            logger.exception('Error al actualizar notificación.')
            return _error_servidor()
        except Exception:
            logger.exception('Error inesperado al actualizar notificación.')
            return _error_servidor()

    @extend_schema(
        operation_id='notificaciones_eliminar',
        summary='Eliminar notificación',
        responses={
            204: OpenApiResponse(description='Notificación eliminada.'),
            400: OpenApiResponse(description='Identificador mal formado.'),
            404: ERROR_404,
            500: ERROR_500,
        },
    )
    def delete(self, request, notificacion_id):
        object_id, error = self._notificacion_id(notificacion_id)
        if error is not None:
            return error
        try:
            result = get_mongo_db().notificaciones.delete_one({'_id': object_id})
            if result.deleted_count == 0:
                return _error_no_encontrada()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except (PyMongoError, ValueError):
            logger.exception('Error al eliminar notificación.')
            return _error_servidor()
        except Exception:
            logger.exception('Error inesperado al eliminar notificación.')
            return _error_servidor()
