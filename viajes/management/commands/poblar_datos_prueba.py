from datetime import timedelta
from hashlib import sha256

from bson import ObjectId
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone as django_timezone

from config.mongo import get_mongo_db
from usuarios.models import Usuario


ADMINISTRADOR = (
    'camila.rojas.admin@example.test',
    'Camila Rojas Muñoz',
    '+56 9 5100 1001',
)
PASAJEROS = [
    ('valentina.munoz@example.test', 'Valentina Muñoz Silva', '+56 9 6100 2001', 'Av. del Mar 1800, La Serena'),
    ('benjamin.araya@example.test', 'Benjamín Araya Cortés', '+56 9 6100 2002', 'Los Carrera 520, Coquimbo'),
    ('fernanda.tapia@example.test', 'Fernanda Tapia González', '+56 9 6100 2003', 'Av. La Paz 740, Ovalle'),
    ('diego.pizarro@example.test', 'Diego Pizarro Núñez', '+56 9 6100 2004', 'Guacolda 310, La Serena'),
    ('isidora.contreras@example.test', 'Isidora Contreras Vega', '+56 9 6100 2005', 'Aldunate 860, Coquimbo'),
    ('tomas.fuentes@example.test', 'Tomás Fuentes Castillo', '+56 9 6100 2006', 'Libertad 450, Ovalle'),
]
VEHICULOS = [
    ('SPGV-30', 'Mercedes-Benz Sprinter', 19),
    ('GVPZ-19', 'Volvo 9700', 45),
    ('VZRZ-59', 'Marcopolo Paradiso', 44),
    ('STGP-20', 'Mercedes-Benz O500', 42),
]
VIAJES = [
    ('La Serena', 'Viña del Mar', 'Estadio Sausalito', 'Los Bunkers', 'SPGV-30', 14),
    ('Coquimbo', 'Viña del Mar', 'Quinta Vergara', 'Festival de Viña del Mar', 'GVPZ-19', 21),
    ('Ovalle', 'Santiago', 'Estadio Nacional', 'Coldplay', 'VZRZ-59', 28),
    ('La Serena', 'Santiago', 'Movistar Arena', 'Mon Laferte', 'STGP-20', 35),
]


class Command(BaseCommand):
    help = 'Crea cuentas de prueba en PostgreSQL y datos de viajes en MongoDB.'

    @staticmethod
    def object_id_for(value):
        return ObjectId(sha256(value.encode('utf-8')).digest()[:12])

    def _account(self, email, name, role, phone='', address='', hire_date=None, corporate_phone=''):
        user_model = get_user_model()
        account = user_model.objects.filter(email__iexact=email).first()
        if account is None:
            account = user_model.objects.create_user(
                username=email,
                email=email,
                password='Prueba-Django-2026',
            )
        account.is_active = True
        account.save(update_fields=['is_active'])
        profile, _ = Usuario.objects.update_or_create(
            cuenta=account,
            defaults={
                'nombre_completo': name,
                'rol': role,
                'telefono': phone,
                'direccion_retorno': address,
                'fecha_contratacion': hire_date,
                'telefono_corporativo': corporate_phone,
            },
        )
        return profile

    def handle(self, *args, **options):
        administrador = self._account(
            ADMINISTRADOR[0],
            ADMINISTRADOR[1],
            Usuario.Rol.ADMINISTRADOR,
            hire_date=django_timezone.localdate() - timedelta(days=900),
            corporate_phone=ADMINISTRADOR[2],
        )
        pasajeros = [
            self._account(
                email,
                nombre,
                Usuario.Rol.PASAJERO,
                phone=telefono,
                address=direccion,
            )
            for email, nombre, telefono, direccion in PASAJEROS
        ]

        db = get_mongo_db()
        db.command('ping')
        now = django_timezone.now()
        vehiculos = {}
        for patente, modelo, capacidad in VEHICULOS:
            existente = db.vehiculos.find_one({'patente': patente})
            vehicle_id = (
                existente['_id']
                if existente
                else self.object_id_for(f'vehiculo:{patente}')
            )
            db.vehiculos.replace_one(
                {'_id': vehicle_id},
                {
                    '_id': vehicle_id,
                    'patente': patente,
                    'modelo': modelo,
                    'capacidad_maxima': capacidad,
                },
                upsert=True,
            )
            vehiculos[patente] = (vehicle_id, capacidad)

        for indice, (origen, destino, recinto, artista, patente, dias) in enumerate(VIAJES):
            titulo = f'{artista} en {recinto} - {origen}'
            existente = db.viajes.find_one({'titulo': titulo})
            viaje_id = (
                existente['_id']
                if existente
                else self.object_id_for(f'viaje:{titulo}')
            )
            fecha_evento = now + timedelta(days=dias)
            region_destino = 'Valparaíso' if destino == 'Viña del Mar' else 'Metropolitana'
            documento = {
                '_id': viaje_id,
                'titulo': titulo,
                'artista': artista,
                'recinto': recinto,
                'descripcion': f'Traslado de prueba desde {origen}, Región de Coquimbo, hacia {recinto}, {destino}.',
                'origen': f'{origen}, Región de Coquimbo',
                'destino': f'{destino}, Región {region_destino}',
                'fecha_evento': fecha_evento,
                'fecha_salida': fecha_evento - timedelta(hours=5),
                'fecha_retorno': fecha_evento + timedelta(hours=3),
                'precio_ida': 18000 + indice * 2000,
                'precio_ida_y_vuelta': 32000 + indice * 3000,
                'estado': 'programado',
                'administrador': {
                    'id_admin': str(administrador.cuenta_id),
                    'nombre': administrador.nombre_completo,
                },
                'patente_vehiculo': vehiculos[patente][0],
                'asientos': [
                    {
                        'num_asiento': numero,
                        'estado': 'ocupado' if numero <= 3 else 'disponible',
                        'bloqueado_hasta': None,
                    }
                    for numero in range(1, vehiculos[patente][1] + 1)
                ],
            }
            db.viajes.replace_one({'_id': viaje_id}, documento, upsert=True)

            for numero, pasajero in enumerate(pasajeros[indice:indice + 3], start=1):
                pasajero_id = str(pasajero.cuenta_id)
                reserva_query = {
                    'pasajero_titular.id_pasajero': pasajero_id,
                    'viaje_reservado.id_viaje_reservado': viaje_id,
                    'tipo_viaje': 'ida_vuelta',
                }
                existente = db.reservas.find_one(reserva_query)
                reserva_id = (
                    existente['_id']
                    if existente
                    else self.object_id_for(f'reserva:{pasajero_id}:{viaje_id}')
                )
                db.reservas.replace_one(
                    {'_id': reserva_id},
                    {
                        '_id': reserva_id,
                        'fecha_reserva': now,
                        'estado': 'confirmada',
                        'tipo_viaje': 'ida_vuelta',
                        'direccion_retorno': pasajero.direccion_retorno,
                        'pasajero_titular': {
                            'id_pasajero': pasajero_id,
                            'nombre_completo': pasajero.nombre_completo,
                        },
                        'viaje_reservado': {'id_viaje_reservado': viaje_id},
                        'asientos_reservados': [{'num_asiento': numero}],
                        'pagos': [{
                            'id_transaccion': f'TEST-TRX-{viaje_id}-{numero:02d}',
                            'monto': 32000 + indice * 3000,
                            'metodo_pago': 'transferencia',
                            'estado': 'completado',
                            'fecha_pago': now,
                        }],
                    },
                    upsert=True,
                )

        notificaciones = [
            (
                'Confirmación de itinerario - Los Bunkers en Sausalito',
                'El viaje saldrá puntualmente desde La Serena. Preséntate 15 minutos antes con tu cédula de identidad.',
                [0, 1, 2],
                [True, False, False],
            ),
            (
                'Recomendaciones de seguridad y equipaje',
                'Lleva tu entrada descargada o impresa, cargador portátil y abrigo ligero para el retorno nocturno.',
                list(range(len(pasajeros))),
                [True, True, False, False, True, False],
            ),
            (
                'Punto de retorno en Coquimbo actualizado',
                'La parada oficial será en Plaza de Armas por obras viales.',
                [1, 4],
                [True, False],
            ),
            (
                '¡Nuevas fechas abiertas para Coldplay!',
                'Hay nuevos traslados hacia el Estadio Nacional. ¡Reserva con anticipación!',
                [2, 3, 5],
                [False, False, False],
            ),
        ]
        for titulo, cuerpo, indices, leidos in notificaciones:
            existente = db.notificaciones.find_one({'titulo': titulo})
            notification_id = (
                existente['_id']
                if existente
                else self.object_id_for(f'notificacion:{titulo}')
            )
            db.notificaciones.replace_one(
                {'_id': notification_id},
                {
                    '_id': notification_id,
                    'titulo': titulo,
                    'cuerpo': cuerpo,
                    'fecha_creacion': now,
                    'administrador': {
                        'id_admin': str(administrador.cuenta_id),
                        'nombre': administrador.nombre_completo,
                    },
                    'destinatarios': [
                        {
                            'id_pasajero': str(pasajeros[index].cuenta_id),
                            'leido': leido,
                        }
                        for index, leido in zip(indices, leidos)
                    ],
                },
                upsert=True,
            )

        self.stdout.write(self.style.SUCCESS(
            f'Datos listos: 1 administrador y {len(pasajeros)} pasajeros en PostgreSQL; '
            f'{len(VEHICULOS)} vehículos, {len(VIAJES)} viajes, '
            f'{sum(len(pasajeros[i:i + 3]) for i in range(len(VIAJES)))} reservas '
            f'y {len(notificaciones)} notificaciones en MongoDB.'
        ))
