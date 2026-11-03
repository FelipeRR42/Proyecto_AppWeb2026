from rest_framework import serializers


ESTADOS_VIAJE = ('programado', 'lleno', 'finalizado', 'cancelado')


class ViajeWriteSerializer(serializers.Serializer):
    titulo = serializers.CharField(max_length=200)
    artista = serializers.CharField(max_length=100)
    recinto = serializers.CharField(max_length=100)
    descripcion = serializers.CharField()
    origen = serializers.CharField(max_length=100)
    destino = serializers.CharField(max_length=100)
    fecha_evento = serializers.DateTimeField()
    fecha_salida = serializers.DateTimeField()
    fecha_retorno = serializers.DateTimeField()
    precio_ida = serializers.IntegerField(min_value=0)
    precio_ida_y_vuelta = serializers.IntegerField(min_value=0)
    estado = serializers.ChoiceField(choices=ESTADOS_VIAJE)
    administrador_id = serializers.CharField()
    patente_vehiculo = serializers.CharField(max_length=20)

    def validate(self, attrs):
        fecha_salida = attrs.get('fecha_salida', getattr(self.instance, 'fecha_salida', None))
        fecha_evento = attrs.get('fecha_evento', getattr(self.instance, 'fecha_evento', None))
        fecha_retorno = attrs.get('fecha_retorno', getattr(self.instance, 'fecha_retorno', None))
        if fecha_salida and fecha_evento and fecha_retorno:
            if fecha_salida > fecha_evento:
                raise serializers.ValidationError({'fecha_evento': 'Debe ser posterior o igual a la salida.'})
            if fecha_evento > fecha_retorno:
                raise serializers.ValidationError({'fecha_retorno': 'Debe ser posterior o igual al evento.'})
        return attrs


class ViajeQuerySerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=ESTADOS_VIAJE, required=False)
    origen = serializers.CharField(max_length=100, required=False)
    destino = serializers.CharField(max_length=100, required=False)
    artista = serializers.CharField(max_length=100, required=False)
    fecha_desde = serializers.DateField(
        input_formats=('%Y-%m-%d',),
        required=False,
    )
    precio_minimo = serializers.IntegerField(min_value=0, required=False)
    precio_maximo = serializers.IntegerField(min_value=0, required=False)
    cupos_minimos = serializers.IntegerField(min_value=0, required=False)
    orden = serializers.ChoiceField(
        choices=('fecha', 'precio_asc', 'precio_desc'),
        required=False,
        default='fecha',
    )
    proximos = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        minimum = attrs.get('precio_minimo')
        maximum = attrs.get('precio_maximo')
        if minimum is not None and maximum is not None and maximum < minimum:
            raise serializers.ValidationError({
                'precio_maximo': 'Debe ser mayor o igual al precio mínimo.',
            })
        return attrs


class AsientoReadSerializer(serializers.Serializer):
    num_asiento = serializers.IntegerField()
    estado = serializers.CharField()
    bloqueado_hasta = serializers.DateTimeField(required=False, allow_null=True)


class ViajeReadSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    titulo = serializers.CharField()
    artista = serializers.CharField()
    recinto = serializers.CharField()
    descripcion = serializers.CharField()
    origen = serializers.CharField()
    destino = serializers.CharField()
    fecha_evento = serializers.DateTimeField()
    fecha_salida = serializers.DateTimeField()
    fecha_retorno = serializers.DateTimeField()
    precio_ida = serializers.IntegerField()
    precio_ida_y_vuelta = serializers.IntegerField()
    estado = serializers.ChoiceField(choices=ESTADOS_VIAJE)
    administrador_id = serializers.SerializerMethodField()
    administrador_nombre = serializers.SerializerMethodField()
    vehiculo_id = serializers.SerializerMethodField()
    asientos = AsientoReadSerializer(many=True, required=False)

    def get_id(self, viaje) -> str:
        return str(viaje['_id'])

    def get_administrador_id(self, viaje) -> str | None:
        administrador = viaje.get('administrador') or {}
        administrador_id = administrador.get('id_admin')
        return str(administrador_id) if administrador_id else None

    def get_administrador_nombre(self, viaje) -> str | None:
        administrador = viaje.get('administrador') or {}
        return administrador.get('nombre')

    def get_vehiculo_id(self, viaje) -> str | None:
        vehiculo_id = viaje.get('patente_vehiculo')
        return str(vehiculo_id) if vehiculo_id else None