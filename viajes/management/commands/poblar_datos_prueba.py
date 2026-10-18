from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.utils import timezone

from reserva_de_asientos.models import AsientoViaje, Pago, Reserva
from usuarios.models import Administrador, Pasajero
from viajes.models import Vehiculo, Viaje


class Command(BaseCommand):
    help = 'Crea o actualiza datos de prueba de viajes desde Coquimbo.'

    def handle(self, *args, **options):
        administrador, _ = Administrador.objects.get_or_create(
            correo_electronico='camila.rojas.admin@example.test',
            defaults={
                'nombre_completo': 'Camila Rojas Muñoz',
                'contrasenia': make_password('Prueba-Django-2026'),
                'fecha_contratacion': timezone.localdate() - timedelta(days=900),
                'telefono_corporativo': '+56 9 5100 1001',
            },
        )

        pasajeros_data = [
            ('valentina.munoz@example.test', 'Valentina Muñoz Silva', '+56 9 6100 2001', 'Av. del Mar 1800, La Serena'),
            ('benjamin.araya@example.test', 'Benjamín Araya Cortés', '+56 9 6100 2002', 'Los Carrera 520, Coquimbo'),
            ('fernanda.tapia@example.test', 'Fernanda Tapia González', '+56 9 6100 2003', 'Av. La Paz 740, Ovalle'),
            ('diego.pizarro@example.test', 'Diego Pizarro Núñez', '+56 9 6100 2004', 'Guacolda 310, La Serena'),
            ('isidora.contreras@example.test', 'Isidora Contreras Vega', '+56 9 6100 2005', 'Aldunate 860, Coquimbo'),
            ('tomas.fuentes@example.test', 'Tomás Fuentes Castillo', '+56 9 6100 2006', 'Libertad 450, Ovalle'),
        ]
        pasajeros = []
        for correo, nombre, telefono, direccion in pasajeros_data:
            pasajero, _ = Pasajero.objects.get_or_create(
                correo_electronico=correo,
                defaults={
                    'nombre_completo': nombre,
                    'contrasenia': make_password('Prueba-Django-2026'),
                    'telefono': telefono,
                    'direccion_retorno_predeterminada': direccion,
                },
            )
            pasajeros.append(pasajero)

        vehiculos_data = [
            ('TEST-01', 'Mercedes-Benz Sprinter', 19),
            ('TEST-02', 'Volvo 9700', 45),
            ('TEST-03', 'Marcopolo Paradiso', 44),
            ('TEST-04', 'Mercedes-Benz O500', 42),
        ]
        vehiculos = {}
        for patente, modelo, capacidad in vehiculos_data:
            vehiculo, _ = Vehiculo.objects.update_or_create(
                patente=patente,
                defaults={'modelo': modelo, 'capacidad_maxima': capacidad},
            )
            vehiculos[patente] = vehiculo

        ahora = timezone.now()
        viajes_data = [
            ('La Serena', 'Viña del Mar', 'Estadio Sausalito', 'Los Bunkers', 'TEST-01', 14),
            ('Coquimbo', 'Viña del Mar', 'Quinta Vergara', 'Festival de Viña del Mar', 'TEST-02', 21),
            ('Ovalle', 'Santiago', 'Estadio Nacional', 'Coldplay', 'TEST-03', 28),
            ('La Serena', 'Santiago', 'Movistar Arena', 'Mon Laferte', 'TEST-04', 35),
        ]

        reservas_procesadas = 0
        asientos_procesados = 0
        pagos_procesados = 0
        for indice, (origen, destino, recinto, artista, patente, dias) in enumerate(viajes_data):
            fecha_evento = ahora + timedelta(days=dias)
            region_destino = 'Valparaíso' if destino == 'Viña del Mar' else 'Metropolitana'
            viaje, _ = Viaje.objects.update_or_create(
                titulo=f'{artista} en {recinto} - {origen}',
                defaults={
                    'id_admin': administrador,
                    'patente_vehiculo': vehiculos[patente],
                    'origen': f'{origen}, Región de Coquimbo',
                    'destino': f'{destino}, Región {region_destino}',
                    'fecha_evento': fecha_evento,
                    'fecha_salida': fecha_evento - timedelta(hours=5),
                    'fecha_retorno': fecha_evento + timedelta(hours=3),
                    'precio_ida': 18000 + (indice * 2000),
                    'precio_ida_y_vuelta': 32000 + (indice * 3000),
                    'estado': 'programado',
                    'recinto': recinto,
                    'artista': artista,
                    'descripcion': f'Traslado de prueba desde {origen}, Región de Coquimbo, hacia {recinto}, {destino}.',
                },
            )

            reservas_del_viaje = []
            for numero, pasajero in enumerate(pasajeros[indice:indice + 3], start=1):
                reserva, _ = Reserva.objects.get_or_create(
                    id_pasajero=pasajero,
                    id_viaje=viaje,
                    tipo_viaje='ida_vuelta',
                    defaults={
                        'estado': 'confirmada',
                        'direccion_retorno': pasajero.direccion_retorno_predeterminada,
                    },
                )
                reservas_del_viaje.append(reserva)
                Pago.objects.get_or_create(
                    id_reserva=reserva,
                    defaults={
                        'id_transaccion': f'TEST-TRX-{viaje.id_viaje}-{numero:02d}',
                        'monto': Decimal(32000 + (indice * 3000)),
                        'metodo_pago': 'transferencia',
                        'estado': 'completado',
                    },
                )
                pagos_procesados += 1
                reservas_procesadas += 1

            reservas_por_asiento = {numero: reservas_del_viaje[numero - 1] for numero in range(1, 4)}
            for numero in range(1, 13):
                AsientoViaje.objects.update_or_create(
                    id_viaje=viaje,
                    num_asiento=numero,
                    defaults={
                        'id_reserva': reservas_por_asiento.get(numero),
                        'estado_asiento': 'ocupado' if numero in reservas_por_asiento else 'disponible',
                    },
                )
                asientos_procesados += 1

        self.stdout.write(self.style.SUCCESS(
            f'Datos de prueba listos: 1 administrador, {len(pasajeros)} pasajeros, '
            f'{len(vehiculos)} vehículos, {len(viajes_data)} viajes, '
            f'{reservas_procesadas} reservas, {pagos_procesados} pagos y '
            f'{asientos_procesados} asientos procesados.'
        ))