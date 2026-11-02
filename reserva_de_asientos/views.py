import logging

from django.http import Http404
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import generics
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework import status

from .models import Reserva
from .serializers import ReservaSerializer


SERVER_ERROR = OpenApiResponse(description='Error interno al procesar la solicitud.')
logger = logging.getLogger(__name__)


class ReservaErrorHandlingMixin:
    def handle_exception(self, exc):
        try:
            return super().handle_exception(exc)
        except Exception:
            logger.exception('Error interno al procesar una solicitud de reservas.')
            return Response(
                {'detail': 'Error interno al procesar la solicitud.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema_view(
    get=extend_schema(
        operation_id='reservas_listar',
        summary='Listar reservas',
        responses={200: ReservaSerializer(many=True), 500: SERVER_ERROR},
    ),
    post=extend_schema(
        operation_id='reservas_crear',
        summary='Crear reserva',
        request=ReservaSerializer,
        responses={
            201: ReservaSerializer,
            400: OpenApiResponse(description='Datos inválidos o pasajero/viaje inexistente.'),
            500: SERVER_ERROR,
        },
    ),
)
class ReservaListCreateView(ReservaErrorHandlingMixin, generics.ListCreateAPIView):
    queryset = Reserva.objects.select_related('id_pasajero', 'id_viaje')
    serializer_class = ReservaSerializer


@extend_schema_view(
    get=extend_schema(
        operation_id='reservas_obtener',
        summary='Obtener reserva',
        responses={200: ReservaSerializer, 404: OpenApiResponse(description='Reserva no encontrada.'), 500: SERVER_ERROR},
    ),
    put=extend_schema(
        operation_id='reservas_reemplazar',
        summary='Reemplazar reserva',
        request=ReservaSerializer,
        responses={
            200: ReservaSerializer,
            400: OpenApiResponse(description='Datos inválidos o pasajero/viaje inexistente.'),
            404: OpenApiResponse(description='Reserva no encontrada.'),
            500: SERVER_ERROR,
        },
    ),
    patch=extend_schema(
        operation_id='reservas_actualizar_parcial',
        summary='Actualizar parcialmente reserva',
        request=ReservaSerializer,
        responses={
            200: ReservaSerializer,
            400: OpenApiResponse(description='Datos inválidos o pasajero/viaje inexistente.'),
            404: OpenApiResponse(description='Reserva no encontrada.'),
            500: SERVER_ERROR,
        },
    ),
    delete=extend_schema(
        operation_id='reservas_eliminar',
        summary='Eliminar reserva',
        responses={
            204: OpenApiResponse(description='Reserva eliminada.'),
            404: OpenApiResponse(description='Reserva no encontrada.'),
            500: SERVER_ERROR,
        },
    ),
)
class ReservaDetailView(ReservaErrorHandlingMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Reserva.objects.select_related('id_pasajero', 'id_viaje')
    serializer_class = ReservaSerializer
    lookup_field = 'id_reserva'
    lookup_url_kwarg = 'reserva_id'

    def get_object(self):
        try:
            return super().get_object()
        except Http404 as exc:
            raise NotFound('Reserva no encontrada.') from exc
