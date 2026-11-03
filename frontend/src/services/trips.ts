import { isTrip, type Trip, type TripFilters } from '../types/trip'

export const API_URL = (import.meta.env.VITE_API_URL || '/api').replace(/\/+$/, '')

async function getApiError(response: Response) {
  try {
    const data: unknown = await response.json()
    if (typeof data === 'object' && data !== null) {
      const messages = Object.values(data as Record<string, unknown>)
        .flatMap((value) => Array.isArray(value) ? value : [value])
        .filter((value): value is string => typeof value === 'string')
      if (messages.length > 0) return messages.join(' ')
    }
  } catch {
    // Use the status-based message for non-JSON error responses.
  }
  return `No se pudieron cargar los viajes (HTTP ${response.status}).`
}

export async function getUpcomingTrips(
  filters: TripFilters,
  signal?: AbortSignal,
): Promise<Trip[]> {
  const searchParams = new URLSearchParams({ proximos: 'true', orden: filters.orden })
  const activeFilters: Array<[string, string]> = [
    ['fecha_desde', filters.fecha],
    ['origen', filters.origen],
    ['artista', filters.artista],
    ['precio_minimo', filters.precioMinimo],
    ['precio_maximo', filters.precioMaximo],
    ['cupos_minimos', filters.cuposMinimos],
  ]
  for (const [key, value] of activeFilters) {
    if (value) searchParams.set(key, value)
  }

  const response = await fetch(`${API_URL}/viajes/?${searchParams.toString()}`, {
    headers: { Accept: 'application/json' },
    signal,
  })

  if (!response.ok) {
    throw new Error(await getApiError(response))
  }

  const data: unknown = await response.json()
  if (!Array.isArray(data) || !data.every(isTrip)) {
    throw new Error('La API devolvió una respuesta de viajes con un formato inesperado.')
  }

  return data
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
