from datetime import date
import hashlib
import logging

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .authentication import (
	CookieJWTAuthentication,
	clear_auth_cookies,
	enforce_csrf,
	set_access_cookie,
	set_refresh_cookie,
)
from .models import Usuario
from .permissions import IsAppAdministrator
from .serializers import (
	AdministradorWriteSerializer,
	LoginWriteSerializer,
	PasajeroWriteSerializer,
	RegistroWriteSerializer,
	UsuarioReadSerializer,
	UsuarioWriteSerializer,
)


logger = logging.getLogger(__name__)

ERROR_RESPONSES = {
	400: OpenApiResponse(description='Solicitud inválida o identificador mal formado.'),
	404: OpenApiResponse(description='Usuario no encontrado.'),
	409: OpenApiResponse(description='Ya existe un usuario con ese correo electrónico.'),
	500: OpenApiResponse(description='Error interno al procesar la solicitud.'),
}


def _error_servidor():
	return Response(
		{'detail': 'Error interno al procesar la solicitud.'},
		status=status.HTTP_500_INTERNAL_SERVER_ERROR,
	)


def _datos_usuario(perfil):
	cuenta = perfil.cuenta
	perfil_pasajero = None
	perfil_admin = None
	if perfil.rol == Usuario.Rol.PASAJERO:
		perfil_pasajero = {
			'telefono': perfil.telefono,
			'direccion_retorno_predeterminada': perfil.direccion_retorno,
		}
	elif perfil.rol == Usuario.Rol.ADMINISTRADOR:
		perfil_admin = {
			'fecha_contratacion': (
				perfil.fecha_contratacion.isoformat()
				if perfil.fecha_contratacion
				else None
			),
			'telefono_corporativo': perfil.telefono_corporativo,
		}
	return {
		'_id': str(cuenta.pk),
		'nombre_completo': perfil.nombre_completo,
		'correo_electronico': cuenta.email,
		'rol': perfil.rol,
		'perfil_pasajero': perfil_pasajero,
		'perfil_admin': perfil_admin,
		'archivado': not cuenta.is_active,
	}


def _perfil_por_id(usuario_id, role=None):
	if not usuario_id.isdecimal() or int(usuario_id) < 1:
		return None, Response(
			{'detail': 'Identificador inválido.'},
			status=status.HTTP_400_BAD_REQUEST,
		)
	query = Usuario.objects.select_related('cuenta').filter(cuenta_id=int(usuario_id))
	if role is not None:
		query = query.filter(rol=role)
	perfil = query.first()
	if perfil is None:
		return None, Response(
			{'detail': 'Usuario no encontrado.'},
			status=status.HTTP_404_NOT_FOUND,
		)
	return perfil, None


def _username_for_email(email):
	return email if len(email) <= 150 else f'email_{hashlib.sha256(email.encode()).hexdigest()}'


def _cuenta_duplicada(email, username, exclude_id=None):
	user_model = get_user_model()
	query = user_model.objects.filter(email__iexact=email)
	username_query = user_model.objects.filter(username__iexact=username)
	if exclude_id is not None:
		query = query.exclude(pk=exclude_id)
		username_query = username_query.exclude(pk=exclude_id)
	return query.exists() or username_query.exists()


def _validar_contrasenia(password, email, nombre_completo):
	candidate = get_user_model()(username=_username_for_email(email), email=email)
	candidate.first_name = nombre_completo
	try:
		validate_password(password, user=candidate)
	except DjangoValidationError as error:
		return Response(
			{'contrasenia': error.messages},
			status=status.HTTP_400_BAD_REQUEST,
		)
	return None


def _guardar_cuenta(values, role, extra_profile, account=None, profile=None):
	email = values.get('correo_electronico', account.email if account else '').lower()
	username = _username_for_email(email)
	if _cuenta_duplicada(email, username, account.pk if account else None):
		return None, Response(
			{'correo_electronico': ['Ya existe un usuario con este correo.']},
			status=status.HTTP_409_CONFLICT,
		)

	password = values.get('contrasenia')
	if password:
		error = _validar_contrasenia(
			password,
			email,
			values.get('nombre_completo', profile.nombre_completo if profile else ''),
		)
		if error is not None:
			return None, error

	user_model = get_user_model()
	try:
		with transaction.atomic():
			if account is None:
				account = user_model(username=username, email=email)
				account.set_password(password)
				account.save()
				profile = Usuario(cuenta=account)
			else:
				account.email = email
				account.username = username
				if password:
					account.set_password(password)
				account.save(update_fields=['email', 'username', 'password'])

			profile.nombre_completo = values.get(
				'nombre_completo',
				profile.nombre_completo,
			)
			profile.rol = role
			profile.telefono = extra_profile.get('telefono', '')
			profile.direccion_retorno = extra_profile.get(
				'direccion_retorno_predeterminada',
				'',
			)
			profile.fecha_contratacion = extra_profile.get('fecha_contratacion')
			profile.telefono_corporativo = extra_profile.get(
				'telefono_corporativo',
				'',
			)
			profile.save()
	except IntegrityError:
		if _cuenta_duplicada(email, username, account.pk if account else None):
			return None, Response(
				{'correo_electronico': ['Ya existe un usuario con este correo.']},
				status=status.HTTP_409_CONFLICT,
			)
		logger.exception('No se pudo guardar la cuenta y perfil del usuario.')
		return None, _error_servidor()
	return profile, None


def _fecha_perfil_admin(perfil_admin):
	if not isinstance(perfil_admin, dict):
		return None, Response(
			{'perfil_admin': ['Debe ser un objeto.']},
			status=status.HTTP_400_BAD_REQUEST,
		)
	value = perfil_admin.get('fecha_contratacion')
	if value in (None, ''):
		return None, None
	if isinstance(value, date):
		return value, None
	try:
		return date.fromisoformat(value), None
	except (TypeError, ValueError):
		return None, Response(
			{'perfil_admin': {'fecha_contratacion': ['Fecha inválida.']}},
			status=status.HTTP_400_BAD_REQUEST,
		)


def _extra_profile(values, role, partial=False, profile=None):
	if role == Usuario.Rol.PASAJERO:
		current_phone = profile.telefono if profile else ''
		current_address = profile.direccion_retorno if profile else ''
		data = values.get('perfil_pasajero') or {}
		if not isinstance(data, dict):
			return None, Response(
				{'perfil_pasajero': ['Debe ser un objeto.']},
				status=status.HTTP_400_BAD_REQUEST,
			)
		return {
			'telefono': data.get('telefono', current_phone if partial else ''),
			'direccion_retorno_predeterminada': data.get(
				'direccion_retorno_predeterminada',
				current_address if partial else '',
			),
		}, None

	current_date = profile.fecha_contratacion if profile else None
	current_phone = profile.telefono_corporativo if profile else ''
	data = values.get('perfil_admin') or {}
	fecha, error = _fecha_perfil_admin(data)
	if error is not None:
		return None, error
	return {
		'fecha_contratacion': (
			fecha if 'fecha_contratacion' in data or not partial else current_date
		),
		'telefono_corporativo': data.get(
			'telefono_corporativo',
			current_phone if partial else '',
		),
	}, None


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CsrfTokenView(APIView):
	authentication_classes = []
	permission_classes = [AllowAny]

	def get(self, request):
		return Response({'csrfToken': get_token(request._request)})


class LoginView(APIView):
	authentication_classes = []
	permission_classes = [AllowAny]

	@extend_schema(
		operation_id='auth_login',
		summary='Iniciar sesión',
		request=LoginWriteSerializer,
		responses={
			200: OpenApiResponse(
				description='Inicio correcto; devuelve el rol y nombre, con JWT en cookies HttpOnly.',
			),
			400: OpenApiResponse(description='Datos de entrada inválidos.'),
			401: OpenApiResponse(description='Credenciales incorrectas.'),
			500: OpenApiResponse(description='No fue posible procesar la solicitud.'),
		},
	)
	def post(self, request):
		enforce_csrf(request)
		serializer = LoginWriteSerializer(data=request.data)
		if not serializer.is_valid():
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

		values = serializer.validated_data
		user_model = get_user_model()
		users = list(
			user_model.objects.filter(
				email__iexact=values['correo_electronico'],
			).only('pk', 'is_active', user_model.USERNAME_FIELD).order_by('pk')[:2]
		)
		if len(users) != 1:
			return Response(
				{'detail': 'El correo electrónico o la contraseña son incorrectos.'},
				status=status.HTTP_401_UNAUTHORIZED,
			)

		user = authenticate(
			request,
			username=users[0].get_username(),
			password=values['contrasenia'],
		)
		if user is None:
			return Response(
				{'detail': 'El correo electrónico o la contraseña son incorrectos.'},
				status=status.HTTP_401_UNAUTHORIZED,
			)

		try:
			profile = user.perfil
		except Usuario.DoesNotExist:
			logger.error('La cuenta autenticada con id=%s no tiene perfil Usuario.', user.pk)
			return _error_servidor()

		refresh = RefreshToken.for_user(user)
		response = Response({
			'role': profile.rol,
			'nombre_completo': profile.nombre_completo,
		})
		set_access_cookie(response, str(refresh.access_token))
		set_refresh_cookie(response, str(refresh))
		return response


class CurrentUserProfileView(APIView):
	@extend_schema(
		operation_id='auth_current_profile',
		summary='Obtener el perfil del usuario autenticado',
		responses={
			200: OpenApiResponse(description='Datos de perfil necesarios para una reserva.'),
			401: OpenApiResponse(description='Sesión no válida.'),
			404: OpenApiResponse(description='Perfil de usuario no encontrado.'),
		},
	)
	def get(self, request):
		try:
			profile = request.user.perfil
		except Usuario.DoesNotExist:
			return Response(
				{'detail': 'No se encontró el perfil de la cuenta autenticada.'},
				status=status.HTTP_404_NOT_FOUND,
			)

		return Response({
			'nombre_completo': profile.nombre_completo,
			'correo_electronico': request.user.email,
			'telefono': profile.telefono,
			'direccion_retorno_predeterminada': profile.direccion_retorno,
		})


class RefreshCookieView(APIView):
	authentication_classes = []
	permission_classes = [AllowAny]

	def post(self, request):
		enforce_csrf(request)
		raw_refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
		if not raw_refresh:
			return self._unauthorized()

		try:
			refresh = RefreshToken(raw_refresh)
			CookieJWTAuthentication().get_user(refresh)
		except (TokenError, AuthenticationFailed):
			return self._unauthorized()

		response = Response({'detail': 'Sesión renovada.'})
		set_access_cookie(response, str(refresh.access_token))
		return response

	@staticmethod
	def _unauthorized():
		response = Response(
			{'detail': 'La sesión ya no es válida. Inicia sesión nuevamente.'},
			status=status.HTTP_401_UNAUTHORIZED,
		)
		clear_auth_cookies(response)
		return response


class LogoutView(APIView):
	authentication_classes = []
	permission_classes = [AllowAny]

	def post(self, request):
		enforce_csrf(request)
		response = Response(status=status.HTTP_204_NO_CONTENT)
		clear_auth_cookies(response)
		return response


class RegistroView(APIView):
	authentication_classes = []
	permission_classes = [AllowAny]

	@extend_schema(
		operation_id='auth_register',
		summary='Crear cuenta de pasajero',
		request=RegistroWriteSerializer,
		responses={
			201: OpenApiResponse(description='Cuenta creada correctamente.'),
			400: OpenApiResponse(description='Datos de entrada inválidos.'),
			409: OpenApiResponse(description='Ya existe una cuenta con ese correo electrónico.'),
			500: OpenApiResponse(description='No fue posible procesar la solicitud.'),
		},
	)
	def post(self, request):
		enforce_csrf(request)
		serializer = RegistroWriteSerializer(data=request.data)
		if not serializer.is_valid():
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

		values = serializer.validated_data
		email = values['correo_electronico'].lower()
		user_model = get_user_model()
		if user_model.objects.filter(email__iexact=email).exists():
			return Response(
				{'correo_electronico': ['Ya existe una cuenta con este correo.']},
				status=status.HTTP_409_CONFLICT,
			)

		username = (
			email
			if len(email) <= 150
			else f'email_{hashlib.sha256(email.encode()).hexdigest()}'
		)
		if user_model.objects.filter(username__iexact=username).exists():
			return Response(
				{'correo_electronico': ['No se pudo usar este correo para crear la cuenta.']},
				status=status.HTTP_409_CONFLICT,
			)

		candidate = user_model(username=username, email=email)
		try:
			validate_password(values['contrasenia'], user=candidate)
		except DjangoValidationError as error:
			return Response(
				{'contrasenia': error.messages},
				status=status.HTTP_400_BAD_REQUEST,
			)

		try:
			with transaction.atomic():
				user = user_model.objects.create_user(
					username=username,
					email=email,
					password=values['contrasenia'],
				)
				Usuario.objects.create(
					cuenta=user,
					nombre_completo=values['nombre_completo'],
					rol=Usuario.Rol.PASAJERO,
					telefono=values.get('telefono', ''),
					direccion_retorno=values.get('direccion_retorno_predeterminada', ''),
				)
		except IntegrityError:
			if user_model.objects.filter(email__iexact=email).exists():
				return Response(
					{'correo_electronico': ['Ya existe una cuenta con este correo.']},
					status=status.HTTP_409_CONFLICT,
				)
			raise

		return Response(
			{'detail': 'Cuenta creada correctamente.'},
			status=status.HTTP_201_CREATED,
		)


class UsuarioListCreateView(APIView):
	permission_classes = [IsAppAdministrator]

	@extend_schema(
		operation_id='usuarios_listar',
		summary='Listar usuarios',
		responses={200: UsuarioReadSerializer(many=True), 500: ERROR_RESPONSES[500]},
	)
	def get(self, request):
		usuarios = Usuario.objects.select_related('cuenta').order_by('cuenta_id')
		return Response(UsuarioReadSerializer(
			[_datos_usuario(usuario) for usuario in usuarios],
			many=True,
		).data)

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
		values = dict(serializer.validated_data)
		role = values.get('rol', Usuario.Rol.PASAJERO)
		extra_profile, error = _extra_profile(values, role)
		if error is not None:
			return error
		profile, error = _guardar_cuenta(values, role, extra_profile)
		if error is not None:
			return error
		return Response(
			UsuarioReadSerializer(_datos_usuario(profile)).data,
			status=status.HTTP_201_CREATED,
		)


class UsuarioDetailView(APIView):
	permission_classes = [IsAppAdministrator]

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
		profile, error = _perfil_por_id(usuario_id)
		if error is not None:
			return error
		return Response(UsuarioReadSerializer(_datos_usuario(profile)).data)

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
		profile, error = _perfil_por_id(usuario_id)
		if error is not None:
			return error
		serializer = UsuarioWriteSerializer(data=request.data, partial=partial)
		if not serializer.is_valid():
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
		values = dict(serializer.validated_data)
		role = values.get('rol', profile.rol)
		extra_profile, error = _extra_profile(
			values,
			role,
			partial=partial,
			profile=profile,
		)
		if error is not None:
			return error
		updated, error = _guardar_cuenta(
			values,
			role,
			extra_profile,
			account=profile.cuenta,
			profile=profile,
		)
		if error is not None:
			return error
		return Response(UsuarioReadSerializer(_datos_usuario(updated)).data)

	@extend_schema(
		operation_id='usuarios_eliminar',
		summary='Desactivar usuario conservando sus referencias',
		responses={204: OpenApiResponse(description='Usuario desactivado.'), 400: ERROR_RESPONSES[400], 404: ERROR_RESPONSES[404], 500: ERROR_RESPONSES[500]},
	)
	def delete(self, request, usuario_id):
		profile, error = _perfil_por_id(usuario_id)
		if error is not None:
			return error
		profile.cuenta.is_active = False
		profile.cuenta.save(update_fields=['is_active'])
		return Response(status=status.HTTP_204_NO_CONTENT)


class PerfilUsuarioListCreateView(APIView):
	permission_classes = [IsAppAdministrator]
	tipo_rol = None
	serializer_class = None

	def get(self, request):
		usuarios = Usuario.objects.select_related('cuenta').filter(
			rol=self.tipo_rol,
		).order_by('cuenta_id')
		return Response(UsuarioReadSerializer(
			[_datos_usuario(usuario) for usuario in usuarios],
			many=True,
		).data)

	def post(self, request):
		serializer = self.serializer_class(data=request.data)
		if not serializer.is_valid():
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
		values = dict(serializer.validated_data)
		extra_profile = {
			'telefono': values.get('telefono', ''),
			'direccion_retorno_predeterminada': values.get(
				'direccion_retorno_predeterminada',
				'',
			),
			'fecha_contratacion': values.get('fecha_contratacion'),
			'telefono_corporativo': values.get('telefono_corporativo', ''),
		}
		profile, error = _guardar_cuenta(values, self.tipo_rol, extra_profile)
		if error is not None:
			return error
		return Response(
			UsuarioReadSerializer(_datos_usuario(profile)).data,
			status=status.HTTP_201_CREATED,
		)


class PerfilUsuarioDetailView(APIView):
	permission_classes = [IsAppAdministrator]
	tipo_rol = None
	serializer_class = None

	def get(self, request, usuario_id):
		profile, error = _perfil_por_id(usuario_id, self.tipo_rol)
		if error is not None:
			return error
		return Response(UsuarioReadSerializer(_datos_usuario(profile)).data)

	def put(self, request, usuario_id):
		return self._actualizar(request, usuario_id, partial=False)

	def patch(self, request, usuario_id):
		return self._actualizar(request, usuario_id, partial=True)

	def _actualizar(self, request, usuario_id, partial):
		profile, error = _perfil_por_id(usuario_id, self.tipo_rol)
		if error is not None:
			return error
		serializer = self.serializer_class(data=request.data, partial=partial)
		if not serializer.is_valid():
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
		values = dict(serializer.validated_data)
		extra_profile = {
			'telefono': values.get('telefono', profile.telefono),
			'direccion_retorno_predeterminada': values.get(
				'direccion_retorno_predeterminada',
				profile.direccion_retorno,
			),
			'fecha_contratacion': values.get(
				'fecha_contratacion',
				profile.fecha_contratacion,
			),
			'telefono_corporativo': values.get(
				'telefono_corporativo',
				profile.telefono_corporativo,
			),
		}
		updated, error = _guardar_cuenta(
			values,
			self.tipo_rol,
			extra_profile,
			account=profile.cuenta,
			profile=profile,
		)
		if error is not None:
			return error
		return Response(UsuarioReadSerializer(_datos_usuario(updated)).data)

	def delete(self, request, usuario_id):
		profile, error = _perfil_por_id(usuario_id, self.tipo_rol)
		if error is not None:
			return error
		profile.cuenta.is_active = False
		profile.cuenta.save(update_fields=['is_active'])
		return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
	get=extend_schema(operation_id='pasajeros_listar', summary='Listar pasajeros'),
	post=extend_schema(
		operation_id='pasajeros_crear',
		summary='Crear pasajero',
		request=PasajeroWriteSerializer,
	),
)
class PasajeroListCreateView(PerfilUsuarioListCreateView):
	tipo_rol = Usuario.Rol.PASAJERO
	serializer_class = PasajeroWriteSerializer


@extend_schema_view(
	get=extend_schema(operation_id='administradores_listar', summary='Listar administradores'),
	post=extend_schema(
		operation_id='administradores_crear',
		summary='Crear administrador',
		request=AdministradorWriteSerializer,
	),
)
class AdministradorListCreateView(PerfilUsuarioListCreateView):
	tipo_rol = Usuario.Rol.ADMINISTRADOR
	serializer_class = AdministradorWriteSerializer


@extend_schema_view(
	get=extend_schema(operation_id='pasajeros_obtener', summary='Obtener pasajero'),
	put=extend_schema(operation_id='pasajeros_actualizar', summary='Actualizar pasajero', request=PasajeroWriteSerializer),
	patch=extend_schema(operation_id='pasajeros_actualizar_parcial', summary='Actualizar parcialmente pasajero', request=PasajeroWriteSerializer),
	delete=extend_schema(operation_id='pasajeros_eliminar', summary='Eliminar pasajero'),
)
class PasajeroDetailView(PerfilUsuarioDetailView):
	tipo_rol = Usuario.Rol.PASAJERO
	serializer_class = PasajeroWriteSerializer


@extend_schema_view(
	get=extend_schema(operation_id='administradores_obtener', summary='Obtener administrador'),
	put=extend_schema(operation_id='administradores_actualizar', summary='Actualizar administrador', request=AdministradorWriteSerializer),
	patch=extend_schema(operation_id='administradores_actualizar_parcial', summary='Actualizar parcialmente administrador', request=AdministradorWriteSerializer),
	delete=extend_schema(operation_id='administradores_eliminar', summary='Eliminar administrador'),
)
class AdministradorDetailView(PerfilUsuarioDetailView):
	tipo_rol = Usuario.Rol.ADMINISTRADOR
	serializer_class = AdministradorWriteSerializer
