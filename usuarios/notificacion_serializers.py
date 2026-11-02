from bson import ObjectId
from rest_framework import serializers


class NotificacionWriteSerializer(serializers.Serializer):
    id_admin = serializers.CharField(
        max_length=24,
        help_text='ObjectId de MongoDB del administrador.',
    )
    titulo = serializers.CharField(max_length=200)
    cuerpo = serializers.CharField()
    destinatarios = serializers.ListField(
        child=serializers.DictField(),
        required=False,
    )

    def validate_id_admin(self, value):
        if not ObjectId.is_valid(value):
            raise serializers.ValidationError('Debe ser un ObjectId válido.')
        return ObjectId(value)

    def validate_destinatarios(self, destinatarios):
        validated = []
        for index, destinatario in enumerate(destinatarios):
            pasajero_id = destinatario.get('id_pasajero')
            if not isinstance(pasajero_id, str) or not ObjectId.is_valid(pasajero_id):
                raise serializers.ValidationError(
                    {index: {'id_pasajero': 'Debe ser un ObjectId válido.'}}
                )
            leido = destinatario.get('leido', False)
            if not isinstance(leido, bool):
                raise serializers.ValidationError(
                    {index: {'leido': 'Debe ser un valor booleano.'}}
                )
            validated.append({
                'id_pasajero': ObjectId(pasajero_id),
                'leido': leido,
            })
        return validated


class NotificacionReadSerializer(serializers.Serializer):
    id_notificacion = serializers.SerializerMethodField()
    id_admin = serializers.SerializerMethodField()
    nombre_admin = serializers.SerializerMethodField()
    titulo = serializers.CharField()
    cuerpo = serializers.CharField()
    fecha_creacion = serializers.DateTimeField()
    destinatarios = serializers.SerializerMethodField()

    def get_id_notificacion(self, notificacion) -> str:
        return str(notificacion['_id'])

    def get_id_admin(self, notificacion) -> str:
        return str(notificacion['administrador']['id_admin'])

    def get_nombre_admin(self, notificacion) -> str:
        return notificacion['administrador']['nombre']

    def get_destinatarios(self, notificacion) -> list[dict[str, str | bool]]:
        return [
            {
                'id_pasajero': str(destinatario['id_pasajero']),
                'leido': destinatario['leido'],
            }
            for destinatario in notificacion.get('destinatarios', [])
        ]
