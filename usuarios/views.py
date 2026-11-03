from datetime import datetime, time, timezone
import secrets

from bson import ObjectId
from django.contrib.auth.hashers import check_password, make_password
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from pymongo.errors import DuplicateKeyError, PyMongoError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from config.mongo import get_mongo_db
from .serializers import (
	AdministradorWriteSerializer,
	LoginWriteSerializer,
	PasajeroWriteSerializer,
	UsuarioReadSerializer,
	UsuarioWriteSerializer,
)


ERROR_RESPONSES = {
	400: OpenApiResponse(description='Solicitud inválida o identificador mal formado.'),
	404: OpenApiResponse(description='Usuario no encontrado.'),
	409: OpenApiResponse(description='Ya existe un usuario con ese correo electrónico.'),
	500: OpenApiResponse(description='Error interno o conexión con MongoDB no disponible.'),
}


def _usuarios_collection():
	return get_mongo_db().usuarios


def _error_servidor():
	return Response(
		{'detail': 'Error interno al procesar la solicitud.'},
		status=status.HTTP_500_INTERNAL_SERVER_ERROR,
	)


def _correo_duplicado(collection, correo, usuario_id=None):
	query = {'correo_electronico': correo}
	if usuario_id is not None:
		query['_id'] = {'$ne': usuario_id}
	return collection.find_one(query) is not None


class LoginView(APIView):
	@extend_schema(
		operation_id='auth_login',
		summary='Iniciar sesión',
		request=LoginWriteSerializer,
		responses={200: OpenApiResponse(description='Sesión de prueba iniciada.'), 400: ERROR_RESPONSES[400], 401: OpenApiResponse(description='Credenciales incorrectas.'), 500: ERROR_RESPONSES[500]},
	)
	def post(self, request):
		serializer = LoginWriteSerializer(data=request.data)
		if not serializer.is_valid():
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

		try:
			values = serializer.validated_data
			usuario = _usuarios_collection().find_one({
				'correo_electronico': values['correo_electronico'],
			})
			if usuario is None or not check_password(values['contrasenia'], usuario.get('contrasenia', '')):
				return Response(
					{'detail': 'El correo electrónico o la contraseña son incorrectos.'},
					status=status.HTTP_401_UNAUTHORIZED,
				)
			if usuario.get('rol') not in ('pasajero', 'administrador'):
				return Response(
					{'detail': 'La cuenta no tiene un rol habilitado para iniciar sesión.'},
					status=status.HTTP_401_UNAUTHORIZED,
				)
			perfil_pasajero = usuario.get('perfil_pasajero') or {}
			return Response({
				'access': secrets.token_urlsafe(32),
				'role': usuario['rol'],
				'user': {
					'id': str(usuario['_id']),
					'nombre_completo': usuario.get('nombre_completo', ''),
					'correo_electronico': usuario.get('correo_electronico', ''),
					'telefono': perfil_pasajero.get('telefono', ''),
					'direccion_retorno_predeterminada': perfil_pasajero.get('direccion_retorno_predeterminada', ''),
				},
			})
		except (PyMongoError, ValueError):
			return _error_servidor()
		except Exception:
			return _error_servidor()


class UsuarioListCreateView(APIView):
	@extend_schema(
		operation_id='usuarios_listar',
		summary='Listar usuarios',
		responses={
			200: UsuarioReadSerializer(many=True),
			500: ERROR_RESPONSES[500],
		},
	)
	def get(self, request):
		try:
			usuarios = list(_usuarios_collection().find())
			return Response(UsuarioReadSerializer(usuarios, many=True).data)
		except (PyMongoError, ValueError):
			return _error_servidor()
		except Exception:
			return _error_servidor()

	@extend_schema(
		operation_id='usuarios_crear',
		summary='Crear usuario',
		request=UsuarioWriteSerializer,
		responses={
			201: UsuarioReadSerializer,
			400: ERROR_RESPONSES[400],
			409: ERROR_RESPONSES[409],
			500: ERROR_RESPONSES[500],
		},
	)
	def post(self, request):
		serializer = UsuarioWriteSerializer(data=request.data)
		if not serializer.is_valid():
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

		try:
			collection = _usuarios_collection()
			values = serializer.validated_data
			if _correo_duplicado(collection, values['correo_electronico']):
				return Response(
					{'correo_electronico': ['Ya existe un usuario con este correo.']},
					status=status.HTTP_409_CONFLICT,
				)

			values['contrasenia'] = make_password(values['contrasenia'])
			values.setdefault('rol', 'usuario')
			values.setdefault('perfil_pasajero', None)
			values.setdefault('perfil_admin', None)
			result = collection.insert_one(values)
			usuario = collection.find_one({'_id': result.inserted_id})
			return Response(
				UsuarioReadSerializer(usuario).data,
				status=status.HTTP_201_CREATED,
			)
		except DuplicateKeyError:
			return Response(
				{'correo_electronico': ['Ya existe un usuario con este correo.']},
				status=status.HTTP_409_CONFLICT,
			)
		except (PyMongoError, ValueError):
			return _error_servidor()
		except Exception:
			return _error_servidor()


class UsuarioDetailView(APIView):
	@extend_schema(
		operation_id='usuarios_obtener',
		summary='Obtener usuario',
		responses={
			200: UsuarioReadSerializer,
			400: ERROR_RESPONSES[400],
			404: ERROR_RESPONSES[404],
			500: ERROR_RESPONSES[500],
		},
	)
	def get(self, request, usuario_id):
		if not ObjectId.is_valid(usuario_id):
			return Response({'detail': 'Identificador inválido.'}, status=status.HTTP_400_BAD_REQUEST)
		try:
			usuario = _usuarios_collection().find_one({'_id': ObjectId(usuario_id)})
			if usuario is None:
				return Response({'detail': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
			return Response(UsuarioReadSerializer(usuario).data)
		except (PyMongoError, ValueError):
			return _error_servidor()
		except Exception:
			return _error_servidor()

	@extend_schema(
		operation_id='usuarios_reemplazar',
		summary='Actualizar usuario',
		request=UsuarioWriteSerializer,
		responses={200: UsuarioReadSerializer, 400: ERROR_RESPONSES[400], 404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409], 500: ERROR_RESPONSES[500]},
	)
	def put(self, request, usuario_id):
		return self._actualizar(request, usuario_id, partial=False)

	@extend_schema(
		operation_id='usuarios_actualizar_parcial',
		summary='Actualizar parcialmente usuario',
		request=UsuarioWriteSerializer,
		responses={200: UsuarioReadSerializer, 400: ERROR_RESPONSES[400], 404: ERROR_RESPONSES[404], 409: ERROR_RESPONSES[409], 500: ERROR_RESPONSES[500]},
	)
	def patch(self, request, usuario_id):
		return self._actualizar(request, usuario_id, partial=True)

	def _actualizar(self, request, usuario_id, partial):
		if not ObjectId.is_valid(usuario_id):
			return Response({'detail': 'Identificador inválido.'}, status=status.HTTP_400_BAD_REQUEST)
		serializer = UsuarioWriteSerializer(data=request.data, partial=partial)
		if not serializer.is_valid():
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
		try:
			collection = _usuarios_collection()
			object_id = ObjectId(usuario_id)
			if collection.find_one({'_id': object_id}) is None:
				return Response({'detail': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
			values = dict(serializer.validated_data)
			correo = values.get('correo_electronico')
			if correo and _correo_duplicado(collection, correo, object_id):
				return Response({'correo_electronico': ['Ya existe un usuario con este correo.']}, status=status.HTTP_409_CONFLICT)
			if 'contrasenia' in values:
				values['contrasenia'] = make_password(values['contrasenia'])
			collection.update_one({'_id': object_id}, {'$set': values})
			usuario = collection.find_one({'_id': object_id})
			return Response(UsuarioReadSerializer(usuario).data)
		except DuplicateKeyError:
			return Response({'correo_electronico': ['Ya existe un usuario con este correo.']}, status=status.HTTP_409_CONFLICT)
		except Exception:
			return _error_servidor()

	@extend_schema(
		operation_id='usuarios_eliminar',
		summary='Eliminar usuario',
		responses={204: OpenApiResponse(description='Usuario eliminado.'), 400: ERROR_RESPONSES[400], 404: ERROR_RESPONSES[404], 500: ERROR_RESPONSES[500]},
	)
	def delete(self, request, usuario_id):
		if not ObjectId.is_valid(usuario_id):
			return Response({'detail': 'Identificador inválido.'}, status=status.HTTP_400_BAD_REQUEST)
		try:
			result = _usuarios_collection().delete_one({'_id': ObjectId(usuario_id)})
			if result.deleted_count == 0:
				return Response({'detail': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
			return Response(status=status.HTTP_204_NO_CONTENT)
		except Exception:
			return _error_servidor()


class PerfilUsuarioListCreateView(APIView):
	tipo_rol = None
	perfil_key = None
	serializer_class = None
	campos_perfil = ()

	def _preparar_perfil(self, values):
		perfil = {field: values.pop(field) for field in self.campos_perfil}
		return perfil

	def _preparar_valor_perfil(self, field, value):
		if field == 'fecha_contratacion':
			return datetime.combine(value, time.min, tzinfo=timezone.utc)
		return value

	@extend_schema(
		responses={200: UsuarioReadSerializer(many=True), 500: ERROR_RESPONSES[500]},
	)
	def get(self, request):
		try:
			usuarios = list(_usuarios_collection().find({'rol': self.tipo_rol}))
			return Response(UsuarioReadSerializer(usuarios, many=True).data)
		except Exception:
			return _error_servidor()

	@extend_schema(
		responses={
			201: UsuarioReadSerializer,
			400: ERROR_RESPONSES[400],
			409: ERROR_RESPONSES[409],
			500: ERROR_RESPONSES[500],
		},
	)
	def post(self, request):
		serializer = self.serializer_class(data=request.data)
		if not serializer.is_valid():
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

		try:
			collection = _usuarios_collection()
			values = dict(serializer.validated_data)
			if _correo_duplicado(collection, values['correo_electronico']):
				return Response(
					{'correo_electronico': ['Ya existe un usuario con este correo.']},
					status=status.HTTP_409_CONFLICT,
				)

			perfil = self._preparar_perfil(values)
			perfil = {
				field: self._preparar_valor_perfil(field, value)
				for field, value in perfil.items()
			}
			values['contrasenia'] = make_password(values['contrasenia'])
			values['rol'] = self.tipo_rol
			values[self.perfil_key] = perfil
			values['perfil_pasajero' if self.tipo_rol == 'administrador' else 'perfil_admin'] = None
			result = collection.insert_one(values)
			usuario = collection.find_one({'_id': result.inserted_id})
			return Response(UsuarioReadSerializer(usuario).data, status=status.HTTP_201_CREATED)
		except DuplicateKeyError:
			return Response(
				{'correo_electronico': ['Ya existe un usuario con este correo.']},
				status=status.HTTP_409_CONFLICT,
			)
		except Exception:
			return _error_servidor()


class PerfilUsuarioDetailView(APIView):
	tipo_rol = None
	perfil_key = None
	serializer_class = None
	campos_perfil = ()

	def _buscar_usuario(self, collection, object_id):
		return collection.find_one({'_id': object_id, 'rol': self.tipo_rol})

	def _preparar_valor_perfil(self, field, value):
		if field == 'fecha_contratacion':
			return datetime.combine(value, time.min, tzinfo=timezone.utc)
		return value

	@extend_schema(
		responses={
			200: UsuarioReadSerializer,
			400: ERROR_RESPONSES[400],
			404: ERROR_RESPONSES[404],
			500: ERROR_RESPONSES[500],
		},
	)
	def get(self, request, usuario_id):
		if not ObjectId.is_valid(usuario_id):
			return Response({'detail': 'Identificador inválido.'}, status=status.HTTP_400_BAD_REQUEST)
		try:
			usuario = self._buscar_usuario(_usuarios_collection(), ObjectId(usuario_id))
			if usuario is None:
				return Response({'detail': 'Perfil no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
			return Response(UsuarioReadSerializer(usuario).data)
		except Exception:
			return _error_servidor()

	@extend_schema(
		request=PasajeroWriteSerializer,
		responses={
			200: UsuarioReadSerializer,
			400: ERROR_RESPONSES[400],
			404: ERROR_RESPONSES[404],
			409: ERROR_RESPONSES[409],
			500: ERROR_RESPONSES[500],
		},
	)
	def put(self, request, usuario_id):
		return self._actualizar(request, usuario_id, partial=False)

	@extend_schema(
		request=PasajeroWriteSerializer,
		responses={
			200: UsuarioReadSerializer,
			400: ERROR_RESPONSES[400],
			404: ERROR_RESPONSES[404],
			409: ERROR_RESPONSES[409],
			500: ERROR_RESPONSES[500],
		},
	)
	def patch(self, request, usuario_id):
		return self._actualizar(request, usuario_id, partial=True)

	def _actualizar(self, request, usuario_id, partial):
		if not ObjectId.is_valid(usuario_id):
			return Response({'detail': 'Identificador inválido.'}, status=status.HTTP_400_BAD_REQUEST)
		serializer = self.serializer_class(data=request.data, partial=partial)
		if not serializer.is_valid():
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

		try:
			collection = _usuarios_collection()
			object_id = ObjectId(usuario_id)
			if self._buscar_usuario(collection, object_id) is None:
				return Response({'detail': 'Perfil no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

			values = dict(serializer.validated_data)
			correo = values.get('correo_electronico')
			if correo and _correo_duplicado(collection, correo, object_id):
				return Response(
					{'correo_electronico': ['Ya existe un usuario con este correo.']},
					status=status.HTTP_409_CONFLICT,
				)
			if 'contrasenia' in values:
				values['contrasenia'] = make_password(values['contrasenia'])
			for field in self.campos_perfil:
				if field in values:
					value = self._preparar_valor_perfil(field, values.pop(field))
					values[f'{self.perfil_key}.{field}'] = value
			collection.update_one(
				{'_id': object_id, 'rol': self.tipo_rol},
				{'$set': values},
			)
			usuario = self._buscar_usuario(collection, object_id)
			return Response(UsuarioReadSerializer(usuario).data)
		except DuplicateKeyError:
			return Response(
				{'correo_electronico': ['Ya existe un usuario con este correo.']},
				status=status.HTTP_409_CONFLICT,
			)
		except Exception:
			return _error_servidor()

	@extend_schema(
		responses={
			204: OpenApiResponse(description='Perfil eliminado.'),
			400: ERROR_RESPONSES[400],
			404: ERROR_RESPONSES[404],
			500: ERROR_RESPONSES[500],
		},
	)
	def delete(self, request, usuario_id):
		if not ObjectId.is_valid(usuario_id):
			return Response({'detail': 'Identificador inválido.'}, status=status.HTTP_400_BAD_REQUEST)
		try:
			result = _usuarios_collection().delete_one({
				'_id': ObjectId(usuario_id),
				'rol': self.tipo_rol,
			})
			if result.deleted_count == 0:
				return Response({'detail': 'Perfil no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
			return Response(status=status.HTTP_204_NO_CONTENT)
		except Exception:
			return _error_servidor()


@extend_schema_view(
	get=extend_schema(operation_id='pasajeros_listar', summary='Listar pasajeros'),
	post=extend_schema(
		operation_id='pasajeros_crear',
		summary='Crear pasajero',
		request=PasajeroWriteSerializer,
	),
)
class PasajeroListCreateView(PerfilUsuarioListCreateView):
	tipo_rol = 'pasajero'
	perfil_key = 'perfil_pasajero'
	serializer_class = PasajeroWriteSerializer
	campos_perfil = ('direccion_retorno_predeterminada', 'telefono')


@extend_schema_view(
	get=extend_schema(operation_id='administradores_listar', summary='Listar administradores'),
	post=extend_schema(
		operation_id='administradores_crear',
		summary='Crear administrador',
		request=AdministradorWriteSerializer,
	),
)
class AdministradorListCreateView(PerfilUsuarioListCreateView):
	tipo_rol = 'administrador'
	perfil_key = 'perfil_admin'
	serializer_class = AdministradorWriteSerializer
	campos_perfil = ('fecha_contratacion', 'telefono_corporativo')


@extend_schema_view(
	get=extend_schema(operation_id='pasajeros_obtener', summary='Obtener pasajero'),
	put=extend_schema(operation_id='pasajeros_actualizar', summary='Actualizar pasajero', request=PasajeroWriteSerializer),
	patch=extend_schema(operation_id='pasajeros_actualizar_parcial', summary='Actualizar parcialmente pasajero', request=PasajeroWriteSerializer),
	delete=extend_schema(operation_id='pasajeros_eliminar', summary='Eliminar pasajero'),
)
class PasajeroDetailView(PerfilUsuarioDetailView):
	tipo_rol = 'pasajero'
	perfil_key = 'perfil_pasajero'
	serializer_class = PasajeroWriteSerializer
	campos_perfil = ('direccion_retorno_predeterminada', 'telefono')


@extend_schema_view(
	get=extend_schema(operation_id='administradores_obtener', summary='Obtener administrador'),
	put=extend_schema(operation_id='administradores_actualizar', summary='Actualizar administrador', request=AdministradorWriteSerializer),
	patch=extend_schema(operation_id='administradores_actualizar_parcial', summary='Actualizar parcialmente administrador', request=AdministradorWriteSerializer),
	delete=extend_schema(operation_id='administradores_eliminar', summary='Eliminar administrador'),
)
class AdministradorDetailView(PerfilUsuarioDetailView):
	tipo_rol = 'administrador'
	perfil_key = 'perfil_admin'
	serializer_class = AdministradorWriteSerializer
	campos_perfil = ('fecha_contratacion', 'telefono_corporativo')
