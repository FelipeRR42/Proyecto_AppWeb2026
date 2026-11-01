from datetime import datetime, time, timezone as datetime_timezone
from decimal import Decimal
from hashlib import sha256
from django.core.management.base import BaseCommand
from bson import ObjectId
from pymongo import UpdateOne, ASCENDING, TEXT

from config.mongo import get_mongo_db
from usuarios.models import Usuario, Pasajero, Administrador, Notificacion, PasajeroRecibeNotificacion
from viajes.models import Viaje, Vehiculo
from reserva_de_asientos.models import Reserva, AsientoViaje, Pago


class Command(BaseCommand):
    help = 'Migra datos desde PostgreSQL (Neon) hacia MongoDB Atlas creando documentos NoSQL optimizados e índices.'

    @staticmethod
    def object_id_for(collection, legacy_id):
        value = f'{collection}:{legacy_id}'.encode('utf-8')
        return ObjectId(sha256(value).digest()[:12])

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
        db.usuarios.delete_many({"_id": {"$in": list(usuarios.values_list('id_usuario', flat=True))}})
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
                    "fecha_contratacion": datetime.combine(
                        a.fecha_contratacion, time.min, tzinfo=datetime_timezone.utc
                    ) if a.fecha_contratacion else None,
                    "telefono_corporativo": a.telefono_corporativo
                }

            doc_usuario = {
                "_id": self.object_id_for('usuarios', u.id_usuario),
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
                "id_pasajero": self.object_id_for('usuarios', relacion.pasajero_id),
                "leido": relacion.leido
            })

        notificaciones = Notificacion.objects.select_related('id_admin').all()
        db.notificaciones.delete_many({
            "_id": {"$in": list(notificaciones.values_list('id_notificacion', flat=True))}
        })
        operaciones = []
        for notificacion in notificaciones:
            doc_notificacion = {
                "_id": self.object_id_for('notificaciones', notificacion.id_notificacion),
                "titulo": notificacion.titulo,
                "cuerpo": notificacion.cuerpo,
                "fecha_creacion": notificacion.fecha_creacion,
                "administrador": {
                    "id_admin": self.object_id_for('usuarios', notificacion.id_admin.id_usuario),
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
        db.vehiculos.delete_many({"_id": {"$in": list(vehiculos.values_list('patente', flat=True))}})
        db.vehiculos.delete_many({"_id": {"$in": ["TEST-01", "TEST-02", "TEST-03", "TEST-04"]}})
        operaciones = []

        for v in vehiculos:
            doc_vehiculo = {
                "_id": self.object_id_for('vehiculos', v.patente),
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
        db.viajes.update_many({}, {"$unset": {
            "vehiculo": "",
            "asientos.id_reserva": "",
            "asientos.rut_ocupante": "",
            "asientos.nombre_ocupante": ""
        }})
        viajes = Viaje.objects.select_related('patente_vehiculo', 'id_admin').prefetch_related('asientoviaje_set').all()
        db.viajes.delete_many({"_id": {"$in": list(viajes.values_list('id_viaje', flat=True))}})
        operaciones = []

        for v in viajes:
            asientos_embebidos = []
            for a in v.asientoviaje_set.order_by('num_asiento'):
                asientos_embebidos.append({
                    "num_asiento": a.num_asiento,
                    "estado": a.estado_asiento,
                    "bloqueado_hasta": a.bloqueado_hasta
                })

            admin_doc = None
            if v.id_admin:
                admin_doc = {
                    "id_admin": self.object_id_for('usuarios', v.id_admin.id_usuario),
                    "nombre": v.id_admin.nombre_completo
                }

            doc_viaje = {
                "_id": self.object_id_for('viajes', v.id_viaje),
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
                "patente_vehiculo": self.object_id_for('vehiculos', v.patente_vehiculo.patente) if v.patente_vehiculo else None,
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
        db.reservas.delete_many({"_id": {"$in": list(reservas.values_list('id_reserva', flat=True))}})
        operaciones = []

        for r in reservas:
            pagos_embebidos = []
            for p in r.pago_set.all():
                pagos_embebidos.append({
                    "id_pago": self.object_id_for('pagos', p.id_pago),
                    "id_transaccion": p.id_transaccion,
                    "monto": float(p.monto) if isinstance(p.monto, Decimal) else p.monto,
                    "metodo_pago": p.metodo_pago,
                    "estado": p.estado,
                    "fecha_pago": p.fecha_pago
                })

            asientos_reservados = []
            for a in r.asientoviaje_set.all():
                asientos_reservados.append({
                    "num_asiento": a.num_asiento
                })

            doc_reserva = {
                "_id": self.object_id_for('reservas', r.id_reserva),
                "fecha_reserva": r.fecha_reserva,
                "estado": r.estado,
                "tipo_viaje": r.tipo_viaje,
                "direccion_retorno": r.direccion_retorno,
                "pasajero_titular": {
                    "id_pasajero": self.object_id_for('usuarios', r.id_pasajero.id_usuario)
                } if r.id_pasajero else None,
                "viaje_reservado": {
                    "id_viaje_reservado": self.object_id_for('viajes', r.id_viaje.id_viaje)
                } if r.id_viaje else None,
                "asientos_reservados": asientos_reservados,
                "pagos": pagos_embebidos
            }
            operaciones.append(UpdateOne(
                {"_id": doc_reserva["_id"]},
                {"$set": doc_reserva, "$unset": {"pasajero": "", "viaje": ""}},
                upsert=True
            ))

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
        db.vehiculos.create_index([("patente", ASCENDING)], unique=True)

        # Índices viajes
        db.viajes.create_index([("estado", ASCENDING), ("fecha_salida", ASCENDING)])
        db.viajes.create_index([("origen", ASCENDING), ("destino", ASCENDING), ("fecha_salida", ASCENDING)])
        db.viajes.create_index([("artista", TEXT), ("recinto", TEXT), ("titulo", TEXT)])
        db.viajes.create_index([("asientos.num_asiento", ASCENDING)])
        db.viajes.create_index([("patente_vehiculo", ASCENDING)])

        # Índices reservas
        db.reservas.create_index([("pasajero_titular.id_pasajero", ASCENDING), ("fecha_reserva", ASCENDING)])
        db.reservas.create_index([("viaje_reservado.id_viaje_reservado", ASCENDING), ("estado", ASCENDING)])
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
