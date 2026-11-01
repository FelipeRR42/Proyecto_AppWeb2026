from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from pymongo import UpdateOne, ASCENDING, TEXT

from config.mongo import get_mongo_db
from usuarios.models import Usuario, Pasajero, Administrador, Notificacion, PasajeroRecibeNotificacion
from viajes.models import Viaje, Vehiculo
from reserva_de_asientos.models import Reserva, AsientoViaje, Pago


class Command(BaseCommand):
    help = 'Migra datos desde PostgreSQL (Neon) hacia MongoDB Atlas creando documentos NoSQL optimizados e índices.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Iniciando proceso ETL de migración a MongoDB Atlas..."))
        db = get_mongo_db()

        self.migrar_usuarios(db)
        self.migrar_notificaciones(db)
        self.migrar_vehiculos(db)
        self.migrar_viajes(db)
        self.migrar_reservas(db)
        self.crear_indices(db)
        self.validar_consistencia(db)

        self.stdout.write(self.style.SUCCESS("✓ Migración completada exitosamente a MongoDB Atlas."))

    def migrar_usuarios(self, db):
        self.stdout.write("1. Migrando Usuarios, Pasajeros y Administradores...")
        db.usuarios.update_many({}, {"$unset": {"notificaciones": ""}})
        usuarios = Usuario.objects.all()
        operaciones = []

        for u in usuarios:
            es_admin = hasattr(u, 'administrador')
            es_pasajero = hasattr(u, 'pasajero')

            rol = 'administrador' if es_admin else ('pasajero' if es_pasajero else 'usuario')

            perfil_pasajero = None
            if es_pasajero:
                p = u.pasajero
                perfil_pasajero = {
                    "telefono": p.telefono,
                    "direccion_retorno_predeterminada": p.direccion_retorno_predeterminada
                }

            perfil_admin = None
            if es_admin:
                a = u.administrador
                perfil_admin = {
                    "fecha_contratacion": str(a.fecha_contratacion) if a.fecha_contratacion else None,
                    "telefono_corporativo": a.telefono_corporativo
                }

            doc_usuario = {
                "_id": u.id_usuario,
                "nombre_completo": u.nombre_completo,
                "correo_electronico": u.correo_electronico,
                "contrasenia": u.contrasenia,
                "rol": rol,
                "perfil_pasajero": perfil_pasajero,
                "perfil_admin": perfil_admin
            }
            operaciones.append(UpdateOne({"_id": doc_usuario["_id"]}, {"$set": doc_usuario}, upsert=True))

        if operaciones:
            res = db.usuarios.bulk_write(operaciones)
            self.stdout.write(self.style.SUCCESS(
                f"   -> Usuarios procesados: {len(operaciones)} (Nuevos: {res.upserted_count}, Actualizados: {res.modified_count})"
            ))

    def migrar_notificaciones(self, db):
        self.stdout.write("2. Migrando Notificaciones a su propia colección...")
        destinatarios_por_notificacion = {}
        relaciones = PasajeroRecibeNotificacion.objects.select_related('pasajero').all()
        for relacion in relaciones:
            destinatarios_por_notificacion.setdefault(relacion.notificacion_id, []).append({
                "id_pasajero": relacion.pasajero_id,
                "leido": relacion.leido
            })

        notificaciones = Notificacion.objects.select_related('id_admin').all()
        operaciones = []
        for notificacion in notificaciones:
            doc_notificacion = {
                "_id": notificacion.id_notificacion,
                "titulo": notificacion.titulo,
                "cuerpo": notificacion.cuerpo,
                "fecha_creacion": notificacion.fecha_creacion,
                "administrador": {
                    "id_admin": notificacion.id_admin.id_usuario,
                    "nombre": notificacion.id_admin.nombre_completo
                },
                "destinatarios": destinatarios_por_notificacion.get(
                    notificacion.id_notificacion, []
                )
            }
            operaciones.append(UpdateOne(
                {"_id": doc_notificacion["_id"]},
                {"$set": doc_notificacion},
                upsert=True
            ))

        if operaciones:
            res = db.notificaciones.bulk_write(operaciones)
            self.stdout.write(self.style.SUCCESS(
                f"   -> Notificaciones procesadas: {len(operaciones)} "
                f"(Nuevas: {res.upserted_count}, Actualizadas: {res.modified_count})"
            ))

    def migrar_vehiculos(self, db):
        self.stdout.write("3. Migrando Vehículos a su propia colección...")
        vehiculos = Vehiculo.objects.all()
        operaciones = []

        for v in vehiculos:
            doc_vehiculo = {
                "_id": v.patente,
                "patente": v.patente,
                "modelo": v.modelo,
                "capacidad_maxima": v.capacidad_maxima
            }
            operaciones.append(UpdateOne({"_id": doc_vehiculo["_id"]}, {"$set": doc_vehiculo}, upsert=True))

        if operaciones:
            res = db.vehiculos.bulk_write(operaciones)
            self.stdout.write(self.style.SUCCESS(
                f"   -> Vehículos procesados: {len(operaciones)} "
                f"(Nuevos: {res.upserted_count}, Actualizados: {res.modified_count})"
            ))

    def migrar_viajes(self, db):
        self.stdout.write("4. Migrando Viajes con Asientos embebidos y Referencia a Vehículo...")
        # Eliminar el documento embebido 'vehiculo' en caso de que existiera en MongoDB
        db.viajes.update_many({}, {"$unset": {"vehiculo": ""}})
        viajes = Viaje.objects.select_related('patente_vehiculo', 'id_admin').prefetch_related('asientoviaje_set').all()
        operaciones = []

        for v in viajes:
            asientos_embebidos = []
            for a in v.asientoviaje_set.order_by('num_asiento'):
                asientos_embebidos.append({
                    "num_asiento": a.num_asiento,
                    "estado": a.estado_asiento,
                    "bloqueado_hasta": a.bloqueado_hasta,
                    "id_reserva": a.id_reserva_id,
                    "rut_ocupante": a.rut_ocupante,
                    "nombre_ocupante": a.nombre_ocupante
                })

            admin_doc = None
            if v.id_admin:
                admin_doc = {
                    "id_admin": v.id_admin.id_usuario,
                    "nombre": v.id_admin.nombre_completo
                }

            doc_viaje = {
                "_id": v.id_viaje,
                "titulo": v.titulo,
                "artista": v.artista,
                "recinto": v.recinto,
                "descripcion": v.descripcion,
                "origen": v.origen,
                "destino": v.destino,
                "fecha_evento": v.fecha_evento,
                "fecha_salida": v.fecha_salida,
                "fecha_retorno": v.fecha_retorno,
                "precio_ida": v.precio_ida,
                "precio_ida_y_vuelta": v.precio_ida_y_vuelta,
                "estado": v.estado,
                "administrador": admin_doc,
                "patente_vehiculo": v.patente_vehiculo.patente if v.patente_vehiculo else None,
                "asientos": asientos_embebidos
            }
            operaciones.append(UpdateOne({"_id": doc_viaje["_id"]}, {"$set": doc_viaje}, upsert=True))

        if operaciones:
            res = db.viajes.bulk_write(operaciones)
            self.stdout.write(self.style.SUCCESS(
                f"   -> Viajes procesados: {len(operaciones)} (Nuevos: {res.upserted_count}, Actualizados: {res.modified_count})"
            ))

    def migrar_reservas(self, db):
        self.stdout.write("5. Migrando Reservas con Pagos embebidos y Referencias Extendidas...")
        reservas = Reserva.objects.select_related('id_pasajero', 'id_viaje').prefetch_related('pago_set', 'asientoviaje_set').all()
        operaciones = []

        for r in reservas:
            pagos_embebidos = []
            for p in r.pago_set.all():
                pagos_embebidos.append({
                    "id_pago": p.id_pago,
                    "id_transaccion": p.id_transaccion,
                    "monto": float(p.monto) if isinstance(p.monto, Decimal) else p.monto,
                    "metodo_pago": p.metodo_pago,
                    "estado": p.estado,
                    "fecha_pago": p.fecha_pago
                })

            asientos_reservados = []
            for a in r.asientoviaje_set.all():
                asientos_reservados.append({
                    "num_asiento": a.num_asiento,
                    "rut_ocupante": a.rut_ocupante,
                    "nombre_ocupante": a.nombre_ocupante
                })

            pasajero_doc = None
            if r.id_pasajero:
                pasajero_doc = {
                    "id_pasajero": r.id_pasajero.id_usuario,
                    "nombre_completo": r.id_pasajero.nombre_completo,
                    "correo_electronico": r.id_pasajero.correo_electronico,
                    "telefono": r.id_pasajero.telefono
                }

            viaje_doc = None
            if r.id_viaje:
                viaje_doc = {
                    "id_viaje": r.id_viaje.id_viaje,
                    "titulo": r.id_viaje.titulo,
                    "artista": r.id_viaje.artista,
                    "recinto": r.id_viaje.recinto,
                    "origen": r.id_viaje.origen,
                    "destino": r.id_viaje.destino,
                    "fecha_salida": r.id_viaje.fecha_salida
                }

            doc_reserva = {
                "_id": r.id_reserva,
                "fecha_reserva": r.fecha_reserva,
                "estado": r.estado,
                "tipo_viaje": r.tipo_viaje,
                "direccion_retorno": r.direccion_retorno,
                "pasajero": pasajero_doc,
                "viaje": viaje_doc,
                "asientos_reservados": asientos_reservados,
                "pagos": pagos_embebidos
            }
            operaciones.append(UpdateOne({"_id": doc_reserva["_id"]}, {"$set": doc_reserva}, upsert=True))

        if operaciones:
            res = db.reservas.bulk_write(operaciones)
            self.stdout.write(self.style.SUCCESS(
                f"   -> Reservas procesadas: {len(operaciones)} (Nuevos: {res.upserted_count}, Actualizados: {res.modified_count})"
            ))

    def crear_indices(self, db):
        self.stdout.write("6. Creando índices optimizados en MongoDB Atlas...")
        # Índices usuarios
        db.usuarios.create_index([("correo_electronico", ASCENDING)], unique=True)
        db.usuarios.create_index([("rol", ASCENDING)])

        # Índice para consultar notificaciones por pasajero
        db.notificaciones.create_index([("destinatarios.id_pasajero", ASCENDING)])

        # Índices vehículos
        db.vehiculos.create_index([("modelo", ASCENDING)])

        # Índices viajes
        db.viajes.create_index([("estado", ASCENDING), ("fecha_salida", ASCENDING)])
        db.viajes.create_index([("origen", ASCENDING), ("destino", ASCENDING), ("fecha_salida", ASCENDING)])
        db.viajes.create_index([("artista", TEXT), ("recinto", TEXT), ("titulo", TEXT)])
        db.viajes.create_index([("asientos.num_asiento", ASCENDING)])
        db.viajes.create_index([("patente_vehiculo", ASCENDING)])

        # Índices reservas
        db.reservas.create_index([("pasajero.id_pasajero", ASCENDING), ("fecha_reserva", ASCENDING)])
        db.reservas.create_index([("viaje.id_viaje", ASCENDING), ("estado", ASCENDING)])
        db.reservas.create_index([("pagos.id_transaccion", ASCENDING)], unique=True, sparse=True)

        self.stdout.write(self.style.SUCCESS("   -> Índices creados satisfactoriamente."))

    def validar_consistencia(self, db):
        self.stdout.write("7. Validando consistencia entre PostgreSQL y MongoDB Atlas...")
        pg_usuarios = Usuario.objects.count()
        pg_notificaciones = Notificacion.objects.count()
        pg_vehiculos = Vehiculo.objects.count()
        pg_viajes = Viaje.objects.count()
        pg_reservas = Reserva.objects.count()
        pg_pagos = Pago.objects.count()
        pg_asientos = AsientoViaje.objects.count()

        mongo_usuarios = db.usuarios.count_documents({})
        mongo_notificaciones = db.notificaciones.count_documents({})
        mongo_vehiculos = db.vehiculos.count_documents({})
        mongo_viajes = db.viajes.count_documents({})
        mongo_reservas = db.reservas.count_documents({})

        # Sumar pagos y asientos embebidos en Mongo
        pipeline_pagos = [
            {"$unwind": "$pagos"},
            {"$count": "total_pagos"}
        ]
        res_pagos = list(db.reservas.aggregate(pipeline_pagos))
        mongo_pagos = res_pagos[0]["total_pagos"] if res_pagos else 0

        pipeline_asientos = [
            {"$unwind": "$asientos"},
            {"$count": "total_asientos"}
        ]
        res_asientos = list(db.viajes.aggregate(pipeline_asientos))
        mongo_asientos = res_asientos[0]["total_asientos"] if res_asientos else 0

        self.stdout.write(f"   Usuarios: PG={pg_usuarios} | Mongo={mongo_usuarios}")
        self.stdout.write(f"   Notificaciones: PG={pg_notificaciones} | Mongo={mongo_notificaciones}")
        self.stdout.write(f"   Vehículos: PG={pg_vehiculos} | Mongo={mongo_vehiculos}")
        self.stdout.write(f"   Viajes: PG={pg_viajes} | Mongo={mongo_viajes}")
        self.stdout.write(f"   Reservas: PG={pg_reservas} | Mongo={mongo_reservas}")
        self.stdout.write(f"   Pagos: PG={pg_pagos} | Mongo={mongo_pagos}")
        self.stdout.write(f"   Asientos: PG={pg_asientos} | Mongo={mongo_asientos}")

        if (pg_usuarios == mongo_usuarios and
            pg_notificaciones == mongo_notificaciones and
            pg_vehiculos == mongo_vehiculos and
            pg_viajes == mongo_viajes and
            pg_reservas == mongo_reservas and
            pg_pagos == mongo_pagos and
            pg_asientos == mongo_asientos):
            self.stdout.write(self.style.SUCCESS("   ★ ¡Consistencia 100% verificada! Todos los registros coinciden con exactitud."))
        else:
            self.stdout.write(self.style.WARNING("   ⚠ Advertencia: Hubo diferencias en los conteos de registros."))
