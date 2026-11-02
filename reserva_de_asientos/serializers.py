from bson import ObjectId
from rest_framework import serializers


class ReservaWriteSerializer(serializers.Serializer):
    id_pasajero = serializers.CharField(
        max_length=24,
        help_text='ObjectId de MongoDB del pasajero.',
    )
    id_viaje = serializers.CharField(
        max_length=24,
        help_text='ObjectId de MongoDB del viaje.',
    )
    estado = serializers.CharField(max_length=20)
    tipo_viaje = serializers.ChoiceField(choices=('ida', 'ida_vuelta'))
    direccion_retorno = serializers.CharField(
        max_length=200,
        allow_blank=True,
        allow_null=True,
        required=False,
    )

    def validate_id_pasajero(self, value):
        if not ObjectId.is_valid(value):
            raise serializers.ValidationError('Debe ser un ObjectId válido.')
        return ObjectId(value)

    def validate_id_viaje(self, value):
        if not ObjectId.is_valid(value):
            raise serializers.ValidationError('Debe ser un ObjectId válido.')
        return ObjectId(value)


class ReservaReadSerializer(serializers.Serializer):
    id_reserva = serializers.SerializerMethodField()
    id_pasajero = serializers.SerializerMethodField()
    id_viaje = serializers.SerializerMethodField()
    fecha_reserva = serializers.DateTimeField()
    estado = serializers.CharField()
    tipo_viaje = serializers.CharField()
    direccion_retorno = serializers.CharField(allow_null=True, allow_blank=True)

    def get_id_reserva(self, reserva) -> str:
        return str(reserva['_id'])

    def get_id_pasajero(self, reserva) -> str | None:
        titular = reserva.get('pasajero_titular')
        if titular is None:
            return None
        return str(titular['id_pasajero'])

    def get_id_viaje(self, reserva) -> str | None:
        viaje = reserva.get('viaje_reservado')
        if viaje is None:
            return None
        return str(viaje['id_viaje_reservado'])
