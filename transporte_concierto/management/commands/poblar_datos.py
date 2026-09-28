from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from transporte_concierto.models import (
    Pasajero, Administrador, Notificacion, PasajeroRecibeNotificacion,
    ViajeAConcierto, Reserva, AsientoReserva, Pago, Vehiculo, ViajeUsaVehiculo,
)
from django.db.models import Max


class Command(BaseCommand):
    help = "Puebla la base de datos con datos ficticios temáticos de League of Legends / Runeterra"

    def handle(self, *args, **options):
        self.stdout.write("Creando administradores...")
        admins = self._crear_administradores()

        self.stdout.write("Creando pasajeros...")
        pasajeros = self._crear_pasajeros()

        self.stdout.write("Creando notificaciones...")
        notificaciones = self._crear_notificaciones()
        self._asignar_notificaciones(pasajeros, notificaciones)

        self.stdout.write("Creando vehículos...")
        vehiculos = self._crear_vehiculos()

        self.stdout.write("Creando viajes a regiones de Runeterra...")
        viajes = self._crear_viajes(admins)
        self._asignar_vehiculos(viajes, vehiculos)

        self.stdout.write("Creando reservas, asientos y pagos...")
        self._crear_reservas(pasajeros, viajes)

        self.stdout.write(self.style.SUCCESS("¡Base de datos poblada con éxito!"))

    def _crear_administradores(self):
        datos = [
            ("Jayce", "jayce@piltover.rune", "hash_jayce"),
            ("Heimerdinger", "heimerdinger@piltover.rune", "hash_heimer"),
        ]
        admins = []
        for nombre, correo, pw in datos:
            admin, _ = Administrador.objects.get_or_create(
                correo_electronico=correo,
                defaults={"nombre_completo": nombre, "contrasenia": pw},
            )
            admins.append(admin)
        return admins

    def _crear_pasajeros(self):
        datos = [
            ("Ahri", "ahri@ionia.rune", "+56911111111"),
            ("Garen", "garen@demacia.rune", "+56922222222"),
            ("Katarina", "katarina@noxus.rune", "+56933333333"),
            ("Yasuo", "yasuo@ionia.rune", "+56944444444"),
            ("Lux", "lux@demacia.rune", "+56955555555"),
            ("Jinx", "jinx@zaun.rune", "+56966666666"),
            ("Vi", "vi@piltover.rune", "+56977777777"),
            ("Ezreal", "ezreal@piltover.rune", "+56988888888"),
            ("Ashe", "ashe@freljord.rune", "+56999999999"),
            ("Braum", "braum@freljord.rune", "+56900000001"),
            ("Lulu", "lulu@bandlecity.rune", "+56900000002"),
            ("Thresh", "thresh@shadowisles.rune", "+56900000003"),
        ]
        pasajeros = []
        for nombre, correo, tel in datos:
            pasajero, _ = Pasajero.objects.get_or_create(
                correo_electronico=correo,
                defaults={
                    "nombre_completo": nombre,
                    "telefono": tel,
                    "contrasenia": f"hash_{nombre.lower()}",
                },
            )
            pasajeros.append(pasajero)
        return pasajeros

    def _crear_notificaciones(self):
        datos = [
            ("Recuerda tu boleto", "No olvides llevar tu boleto y documento de identidad al punto de encuentro."),
            ("Cambio de horario", "El viaje ha sido reprogramado, revisa la nueva hora en tu reserva."),
            ("Bienvenido al sistema", "Gracias por registrarte en el sistema de viajes a conciertos de Runeterra."),
        ]
        notificaciones = []
        for titulo, cuerpo in datos:
            notif, _ = Notificacion.objects.get_or_create(titulo=titulo, defaults={"cuerpo": cuerpo})
            notificaciones.append(notif)
        return notificaciones

    def _asignar_notificaciones(self, pasajeros, notificaciones):
        for pasajero in pasajeros:
            PasajeroRecibeNotificacion.objects.get_or_create(pasajero=pasajero, notificacion=notificaciones[2])
        for pasajero in pasajeros[:5]:
            PasajeroRecibeNotificacion.objects.get_or_create(pasajero=pasajero, notificacion=notificaciones[0])

    def _crear_vehiculos(self):
        datos = [
            ("PPYY11", "Bus Piltover Transit", 40),
            ("ZZKK22", "Van Zaun Motors", 15),
            ("DMCC33", "Bus Demacia Royal Lines", 35),
        ]
        vehiculos = []
        for patente, modelo, capacidad in datos:
            vehiculo, _ = Vehiculo.objects.get_or_create(
                patente=patente, defaults={"modelo": modelo, "capacidad_maxima": capacidad}
            )
            vehiculos.append(vehiculo)
        return vehiculos

    def _crear_viajes(self, admins):
        ahora = timezone.now()
        datos = [
            ("Festival de las Brumas", "Salón del Hielo Eterno", "Freljord", "confirmado",
             "Avenida Central, Piltover", "Salón del Hielo Eterno, Freljord"),
            ("Noches de Noxus", "Coliseo del Inmortal", "Noxus", "confirmado",
             "Plaza Zaun", "Coliseo del Inmortal, Noxus"),
            ("Armonía de Ionia", "Templo de las Cuerdas", "Ionia", "pendiente",
             "Terminal Piltover", "Templo de las Cuerdas, Ionia"),
            ("Ecos de Shurima", "Anfiteatro del Sol", "Shurima", "confirmado",
             "Estación Zaun", "Anfiteatro del Sol, Shurima"),
            ("Marea de Bilgewater", "Muelle de la Sirena Negra", "Bilgewater", "cancelado",
             "Puerto Piltover", "Muelle de la Sirena Negra, Bilgewater"),
            ("Susurros de las Islas Sombrías", "Cripta del Réquiem", "Islas Sombrías", "confirmado",
             "Plaza Demacia", "Cripta del Réquiem, Islas Sombrías"),
        ]
        viajes = []
        for i, (titulo, recinto, region, estado, origen, destino) in enumerate(datos):
            viaje, _ = ViajeAConcierto.objects.get_or_create(
                titulo=titulo,
                defaults={
                    "administrador": admins[i % len(admins)],
                    "fecha_viaje": ahora + timedelta(days=7 * (i + 1)),
                    "descripcion": f"Viaje al concierto '{titulo}' en la región de {region}.",
                    "recinto": recinto,
                    "estado": estado,
                    "direccion_origen": origen,
                    "direccion_destino": destino,
                },
            )
            viajes.append(viaje)
        return viajes

    def _asignar_vehiculos(self, viajes, vehiculos):
        for i, viaje in enumerate(viajes):
            ViajeUsaVehiculo.objects.get_or_create(viaje=viaje, vehiculo=vehiculos[i % len(vehiculos)])

    def _crear_reservas(self, pasajeros, viajes):
        ahora = timezone.now()
        for i, pasajero in enumerate(pasajeros):
            viaje = viajes[i % len(viajes)]
            reserva, creada = Reserva.objects.get_or_create(
                pasajero=pasajero,
                viaje=viaje,
                defaults={
                    "fecha_reserva": ahora - timedelta(days=i),
                    "tipo_viaje": "ida y vuelta" if i % 2 == 0 else "solo ida",
                    "estado": "confirmada" if viaje.estado == "confirmado" else "pendiente",
                },
            )
            if not creada:
                continue

            cantidad = (i % 3) + 1  # 1, 2 o 3 asientos por reserva

            # Continuar la numeración desde el último asiento ya ocupado en ese viaje,
            # para que dos reservas del mismo viaje no compartan asiento
            ultimo = (
                AsientoReserva.objects.filter(reserva__viaje=viaje)
                .aggregate(maximo=Max("numero_asiento"))["maximo"] or 0
            )
            for n in range(1, cantidad + 1):
                AsientoReserva.objects.create(numero_asiento=ultimo + n, reserva=reserva)

            if i % 3 != 0:
                Pago.objects.create(reserva=reserva, monto=15000 * cantidad, estado="pagado")