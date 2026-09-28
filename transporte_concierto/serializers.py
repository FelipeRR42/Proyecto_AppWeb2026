from rest_framework import serializers
from .models import (
    Pasajero,
    Administrador,
    Notificacion,
    PasajeroRecibeNotificacion,
    Vehiculo,
    ViajeAConcierto,
    ViajeUsaVehiculo,
    Reserva,
    AsientoReserva,
    Pago,
)


class PasajeroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pasajero
        fields = ['id_pasajero', 'nombre_completo', 'telefono', 'correo_electronico', 'contrasenia']
        extra_kwargs = {
            'contrasenia': {'write_only': True},
        }


class AdministradorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Administrador
        fields = ['id_admin', 'nombre_completo', 'correo_electronico', 'contrasenia']
        extra_kwargs = {
            'contrasenia': {'write_only': True},
        }


class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = '__all__'


class PasajeroRecibeNotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PasajeroRecibeNotificacion
        fields = '__all__'


class VehiculoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehiculo
        fields = '__all__'


class ViajeUsaVehiculoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ViajeUsaVehiculo
        fields = '__all__'


class ViajeAConciertoSerializer(serializers.ModelSerializer):
    vehiculos_detalle = VehiculoSerializer(source='vehiculos', many=True, read_only=True)

    class Meta:
        model = ViajeAConcierto
        fields = [
            'id_viaje',
            'titulo',
            'descripcion',
            'recinto',
            'fecha_viaje',
            'estado',
            'direccion_origen',
            'direccion_destino',
            'administrador',
            'vehiculos_detalle',
        ]


class AsientoReservaSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsientoReserva
        fields = '__all__'


class PagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = '__all__'


class ReservaSerializer(serializers.ModelSerializer):
    asientos = AsientoReservaSerializer(many=True, read_only=True)
    pago = PagoSerializer(read_only=True)

    class Meta:
        model = Reserva
        fields = [
            'id_reserva',
            'pasajero',
            'viaje',
            'fecha_reserva',
            'tipo_viaje',
            'estado',
            'asientos',
            'pago',
        ]
