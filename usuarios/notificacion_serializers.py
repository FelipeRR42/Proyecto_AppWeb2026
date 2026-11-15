from rest_framework import serializers


class DestinatarioWriteSerializer(serializers.Serializer):
    id_pasajero = serializers.IntegerField(min_value=1)
    leido = serializers.BooleanField(required=False, default=False)


class NotificacionWriteSerializer(serializers.Serializer):
    titulo = serializers.CharField(max_length=200)
    cuerpo = serializers.CharField()
    destinatarios = serializers.ListField(
        child=DestinatarioWriteSerializer(),
        required=False,
    )

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
