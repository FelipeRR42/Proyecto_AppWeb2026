from datetime import datetime, timedelta, timezone

TIEMPO_BLOQUEO = timedelta(minutes=5)


def liberar_bloqueos_vencidos(db, ahora=None, viaje_id=None):
    ahora = ahora or datetime.now(timezone.utc)
    viajes_query = {
        'asientos': {
            '$elemMatch': {
                'estado': 'bloqueado',
                'bloqueado_hasta': {'$lte': ahora},
            },
        },
    }
    reservas_query = {
        'estado': 'pendiente',
        'bloqueado_hasta': {'$lte': ahora},
    }
    if viaje_id is not None:
        viajes_query['_id'] = viaje_id
        reservas_query['viaje_reservado.id_viaje_reservado'] = viaje_id

    db.viajes.update_many(
        viajes_query,
        {
            '$set': {
                'asientos.$[asiento].estado': 'disponible',
                'asientos.$[asiento].bloqueado_hasta': None,
            },
            '$unset': {'asientos.$[asiento].reserva_id': ''},
        },
        array_filters=[{
            'asiento.estado': 'bloqueado',
            'asiento.bloqueado_hasta': {'$lte': ahora},
        }],
    )
    db.reservas.update_many(
        reservas_query,
        {'$set': {'estado': 'vencida'}},
    )


def bloquear_asientos(viajes, viaje_id, numeros, reserva_id, vence, ahora):
    condiciones = [
        {
            'asientos': {
                '$elemMatch': {
                    'num_asiento': numero,
                    '$or': [
                        {'estado': 'disponible'},
                        {
                            'estado': 'bloqueado',
                            'bloqueado_hasta': {'$lte': ahora},
                        },
                    ],
                },
            },
        }
        for numero in numeros
    ]
    resultado = viajes.update_one(
        {'_id': viaje_id, '$and': condiciones},
        {
            '$set': {
                'asientos.$[asiento].estado': 'bloqueado',
                'asientos.$[asiento].bloqueado_hasta': vence,
                'asientos.$[asiento].reserva_id': reserva_id,
            },
        },
        array_filters=[{'asiento.num_asiento': {'$in': numeros}}],
    )
    return resultado.modified_count > 0


def liberar_asientos_reserva(viajes, viaje_id, numeros, reserva_id):
    viajes.update_one(
        {
            '_id': viaje_id,
            'asientos': {
                '$elemMatch': {
                    'num_asiento': {'$in': numeros},
                    'reserva_id': reserva_id,
                },
            },
        },
        {
            '$set': {
                'asientos.$[asiento].estado': 'disponible',
                'asientos.$[asiento].bloqueado_hasta': None,
            },
            '$unset': {'asientos.$[asiento].reserva_id': ''},
        },
        array_filters=[
            {
                'asiento.num_asiento': {'$in': numeros},
                'asiento.reserva_id': reserva_id,
                'asiento.estado': 'bloqueado',
            },
        ],
    )

