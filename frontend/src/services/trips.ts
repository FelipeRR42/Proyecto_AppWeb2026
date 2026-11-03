import { isTrip, type Trip } from '../types/trip'

export const API_URL = (import.meta.env.VITE_API_URL || '/api').replace(/\/+$/, '')

export async function getUpcomingTrips(signal?: AbortSignal): Promise<Trip[]> {
  const response = await fetch(`${API_URL}/viajes/`, {
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

  return data
    .filter(
      (trip) =>
        (trip.estado === 'programado' || trip.estado === 'lleno') &&
        new Date(trip.fecha_salida).getTime() >= Date.now(),
    )
    .sort(
      (first, second) =>
        new Date(first.fecha_salida).getTime() -
        new Date(second.fecha_salida).getTime(),
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
