import { isTrip, type Trip, type TripFilters } from '../types/trip'

export const API_URL = (import.meta.env.VITE_API_URL || '/api').replace(/\/+$/, '')

function localDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''

  const parts = new Intl.DateTimeFormat('en-CA', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    timeZone: 'America/Santiago',
  }).formatToParts(date)
  const part = (type: string) => parts.find((item) => item.type === type)?.value ?? ''
  return `${part('year')}-${part('month')}-${part('day')}`
}

function getAvailableSeats(trip: Trip) {
  return trip.asientos?.filter((seat) => seat.estado === 'disponible').length
}

export async function getUpcomingTrips(
  filters: TripFilters,
  signal?: AbortSignal,
): Promise<Trip[]> {
  const searchParams = new URLSearchParams({
    fecha_desde: filters.fecha,
    origen: filters.origen,
    artista: filters.artista,
    precio_minimo: filters.precioMinimo,
    precio_maximo: filters.precioMaximo,
    cupos_minimos: filters.cuposMinimos,
    orden: filters.orden,
  })

  const response = await fetch(`${API_URL}/viajes/?${searchParams.toString()}`, {
    headers: { Accept: 'application/json' },
    signal,
  })

  if (!response.ok) {
    throw new Error(`No se pudieron cargar los viajes (HTTP ${response.status}).`)
  }

  const data: unknown = await response.json()
  if (!Array.isArray(data) || !data.every(isTrip)) {
    throw new Error('La API devolvió una respuesta de viajes con un formato inesperado.')
  }

  const minimumPrice = filters.precioMinimo ? Number(filters.precioMinimo) : undefined
  const maximumPrice = filters.precioMaximo ? Number(filters.precioMaximo) : undefined
  const minimumSeats = filters.cuposMinimos ? Number(filters.cuposMinimos) : undefined

  return data
    .filter((trip) => {
      const availableSeats = getAvailableSeats(trip)
      return (
        (trip.estado === 'programado' || trip.estado === 'lleno') &&
        new Date(trip.fecha_salida).getTime() >= Date.now() &&
        (!filters.fecha || localDate(trip.fecha_evento) >= filters.fecha) &&
        (!filters.origen || trip.origen === filters.origen) &&
        (!filters.artista || trip.artista === filters.artista) &&
        (minimumPrice === undefined || trip.precio_ida >= minimumPrice) &&
        (maximumPrice === undefined || trip.precio_ida <= maximumPrice) &&
        (minimumSeats === undefined ||
          (availableSeats !== undefined && availableSeats >= minimumSeats))
      )
    })
    .sort(
      (first, second) => {
        if (filters.orden === 'precio_asc') {
          return first.precio_ida - second.precio_ida
        }
        if (filters.orden === 'precio_desc') {
          return second.precio_ida - first.precio_ida
        }
        return (
          new Date(first.fecha_salida).getTime() -
          new Date(second.fecha_salida).getTime()
        )
      },
    )
}

export async function getTripById(id: string, signal?: AbortSignal): Promise<Trip> {
  const response = await fetch(`${API_URL}/viajes/${encodeURIComponent(id)}/`, {
    headers: { Accept: 'application/json' },
    signal,
  })

  if (!response.ok) {
    throw new Error(`No se pudo cargar el viaje (HTTP ${response.status}).`)
  }

  const data: unknown = await response.json()
  if (!isTrip(data)) {
    throw new Error('La API devolvió un viaje con un formato inesperado.')
  }

  return data
}
