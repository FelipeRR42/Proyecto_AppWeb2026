from rest_framework import serializers

from .models import Reserva


class ReservaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reserva
        fields = (
            'id_reserva',
            'id_pasajero',
            'id_viaje',
            'fecha_reserva',
            'estado',
            'tipo_viaje',
            'direccion_retorno',
        )
        read_only_fields = ('id_reserva', 'fecha_reserva')
