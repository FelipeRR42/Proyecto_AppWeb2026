from rest_framework import serializers


class UsuarioWriteSerializer(serializers.Serializer):
    nombre_completo = serializers.CharField(max_length=200)
    correo_electronico = serializers.EmailField()
    contrasenia = serializers.CharField(write_only=True, min_length=8, max_length=128)
    rol = serializers.ChoiceField(
        choices=('usuario', 'pasajero', 'administrador'),
        required=False,
    )
    perfil_pasajero = serializers.JSONField(required=False, allow_null=True)
    perfil_admin = serializers.JSONField(required=False, allow_null=True)


class UsuarioReadSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    nombre_completo = serializers.CharField()
    correo_electronico = serializers.EmailField()
    rol = serializers.CharField(required=False)
    perfil_pasajero = serializers.JSONField(required=False, allow_null=True)
    perfil_admin = serializers.JSONField(required=False, allow_null=True)

    def get_id(self, usuario) -> str:
        return str(usuario['_id'])


class PerfilUsuarioWriteSerializer(serializers.Serializer):
    nombre_completo = serializers.CharField(max_length=200)
    correo_electronico = serializers.EmailField()
    contrasenia = serializers.CharField(write_only=True, min_length=8, max_length=128)


class PasajeroWriteSerializer(PerfilUsuarioWriteSerializer):
    direccion_retorno_predeterminada = serializers.CharField(max_length=200)
    telefono = serializers.CharField(max_length=20)


class AdministradorWriteSerializer(PerfilUsuarioWriteSerializer):
    fecha_contratacion = serializers.DateField()
    telefono_corporativo = serializers.CharField(max_length=20)