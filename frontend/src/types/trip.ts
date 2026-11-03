export type TripSeat = {
  num_asiento: number
  estado: string
  bloqueado_hasta?: string | null
}

export type Trip = {
  id: string
  titulo: string
  artista: string
  recinto: string
  descripcion: string
  origen: string
  destino: string
  fecha_evento: string
  fecha_salida: string
  fecha_retorno: string
  precio_ida: number
  precio_ida_y_vuelta: number
  estado: 'programado' | 'lleno' | 'finalizado' | 'cancelado'
  asientos?: TripSeat[]
}

export function isTrip(value: unknown): value is Trip {
  if (typeof value !== 'object' || value === null) return false

  const trip = value as Record<string, unknown>
  return (
    typeof trip.id === 'string' &&
    typeof trip.titulo === 'string' &&
    typeof trip.artista === 'string' &&
    typeof trip.recinto === 'string' &&
    typeof trip.descripcion === 'string' &&
    typeof trip.origen === 'string' &&
    typeof trip.destino === 'string' &&
    typeof trip.fecha_evento === 'string' &&
    typeof trip.fecha_salida === 'string' &&
    typeof trip.fecha_retorno === 'string' &&
    typeof trip.precio_ida === 'number' &&
    typeof trip.precio_ida_y_vuelta === 'number' &&
    typeof trip.estado === 'string' &&
    ['programado', 'lleno', 'finalizado', 'cancelado'].includes(trip.estado) &&
    (trip.asientos === undefined ||
      (Array.isArray(trip.asientos) &&
        trip.asientos.every(
          (seat) =>
            typeof seat === 'object' &&
            seat !== null &&
            typeof seat.num_asiento === 'number' &&
            typeof seat.estado === 'string',
        )))
  )
}
