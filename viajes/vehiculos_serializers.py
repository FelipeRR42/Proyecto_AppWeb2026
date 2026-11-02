from rest_framework import serializers


class VehiculoWriteSerializer(serializers.Serializer):
	patente = serializers.CharField(max_length=20, trim_whitespace=True)
	modelo = serializers.CharField(max_length=50, trim_whitespace=True)
	capacidad_maxima = serializers.IntegerField(min_value=1)


class VehiculoReadSerializer(serializers.Serializer):
	id = serializers.SerializerMethodField()
	patente = serializers.CharField()
	modelo = serializers.CharField()
	capacidad_maxima = serializers.IntegerField()

	def get_id(self, vehiculo) -> str:
		return str(vehiculo['_id'])